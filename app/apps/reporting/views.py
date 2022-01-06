from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Page, Paginator
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.utils.functional import cached_property
from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView

from reporting.models import TaskReport
from users.models import User


class ReportList(LoginRequiredMixin, ListView):
    model = TaskReport
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        cpu_usage = self.request.user.calc_cpu_usage()
        context['cpu_cost_last_week'] = cpu_usage
        gpu_usage = self.request.user.calc_gpu_usage()
        context['gpu_cost_last_week'] = gpu_usage
        
        disk_storage_limit = self.request.user.disk_storage_limit()
        context['enforce_disk_storage'] = not settings.DISABLE_QUOTAS and disk_storage_limit != None
        if context['enforce_disk_storage']:
            context['disk_storage_used_percentage'] = min(round((self.request.user.calc_disk_usage()*100)/disk_storage_limit, 2) if disk_storage_limit else 100, 100)
        
        cpu_minutes_limit = self.request.user.cpu_minutes_limit()
        context['enforce_cpu'] = not settings.DISABLE_QUOTAS and cpu_minutes_limit != None
        if context['enforce_cpu']:
            context['cpu_minutes_used_percentage'] = min(round((cpu_usage*100)/cpu_minutes_limit, 2) if cpu_minutes_limit else 100, 100)
        
        gpu_minutes_limit = self.request.user.gpu_minutes_limit()
        context['enforce_gpu'] = not settings.DISABLE_QUOTAS and gpu_minutes_limit != None
        if context['enforce_gpu']:
            context['gpu_minutes_used_percentage'] = min(round((gpu_usage*100)/gpu_minutes_limit, 2) if gpu_minutes_limit else 100, 100)

        return context

    def get_queryset(self):
        qs = super().get_queryset()

        blacklist = [
            'core.tasks.lossless_compression',
            'core.tasks.convert',
            'core.tasks.generate_part_thumbnails',
            'users.tasks.async_email',
            'core.tasks.recalculate_masks'
        ]

        return (qs.filter(user=self.request.user)
                  .exclude(method__in=blacklist)
                  .annotate(duration=ExpressionWrapper(F('done_at') - F('started_at'),
                                                       output_field=DurationField()))
                  .order_by('-queued_at'))


class ReportDetail(LoginRequiredMixin, DetailView):
    model = TaskReport
    context_object_name = 'report'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class CustomPaginator(Paginator):

    def __init__(self, *args, **kwargs):
        self._count = kwargs.pop('total')
        super(CustomPaginator, self).__init__(*args, **kwargs)

    @cached_property
    def count(self):
        return self._count

    def page(self, number):
        number = self.validate_number(number)
        return Page(self.object_list, number, self)


class QuotasLeaderboard(LoginRequiredMixin, TemplateView):
    template_name = "reporting/quotas_leaderboard.html"
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['enforce_quotas'] = not settings.DISABLE_QUOTAS

        try:
            page = int(self.request.GET.get('page', '1'))
        except ValueError:
            page = 1
        offset = (page-1) * self.paginate_by

        today = date.today()
        filter_last_week = Q(taskreport__started_at__gte=today - timedelta(days=7))
        filter_last_day = Q(taskreport__started_at__gte=today - timedelta(days=1))
        runtime = ExpressionWrapper(
            F('taskreport__done_at') - F('taskreport__started_at'),
            output_field=DurationField()
        )

        qs = User.objects.all()
        results = list(
            qs.annotate(
                total_cpu_usage=Sum('taskreport__cpu_cost'),
                total_gpu_usage=Sum('taskreport__gpu_cost'),
                last_week_cpu_usage=Sum('taskreport__cpu_cost', filter=filter_last_week),
                last_week_gpu_usage=Sum('taskreport__gpu_cost', filter=filter_last_week),
                total_tasks=Count('taskreport'),
                total_runtime=Sum(runtime),
                last_week_tasks=Count('taskreport', filter=filter_last_week),
                last_week_runtime=Sum(runtime, filter=filter_last_week),
                last_day_tasks=Count('taskreport', filter=filter_last_day),
                last_day_runtime=Sum(runtime, filter=filter_last_day)
            ).order_by(F('total_runtime').desc(nulls_last=True))[offset:offset+self.paginate_by]
        )
        disk_usages_left = dict(qs.values('id').annotate(disk_usage=Sum('ocrmodel__file_size')).values_list('id', 'disk_usage'))
        disk_usages_right = dict(qs.values('id').annotate(disk_usage=Sum('document__parts__image_file_size')).values_list('id', 'disk_usage'))

        for user in results:
            user.disk_usage = (disk_usages_left[user.id] or 0) + (disk_usages_right[user.id] or 0)

        # Pagination
        paginator = CustomPaginator(results, self.paginate_by, total=qs.count())

        if page > paginator.num_pages:
            page = paginator.num_pages

        context['page_obj'] = paginator.page(page)
        context['is_paginated'] = paginator.num_pages > 1

        return context
