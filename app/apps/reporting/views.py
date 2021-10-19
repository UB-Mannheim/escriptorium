from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.views.generic import ListView, DetailView

from reporting.models import TaskReport
from users.models import User


class ReportList(LoginRequiredMixin, ListView):
    model = TaskReport
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        today = date.today()
        qs = self.request.user.taskreport_set.filter(
            started_at__gte=today - timedelta(days=30)
        ).aggregate(Sum('cpu_cost'), Sum('gpu_cost'))
        context['cpu_cost_last_month'] = qs['cpu_cost__sum'] or 0
        context['gpu_cost_last_month'] = qs['gpu_cost__sum'] or 0
        disk_storage_limit = self.request.user.disk_storage_limit()
        context['enforce_disk_storage'] = not settings.DISABLE_QUOTAS and disk_storage_limit != None
        if context['enforce_disk_storage']:
            context['disk_storage_used_percentage'] = min(round((self.request.user.calc_disk_usage()*100)/disk_storage_limit, 2) if disk_storage_limit else 100, 100)
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


class QuotasLeaderboard(LoginRequiredMixin, ListView):
    model = User
    template_name = "reporting/quotas_leaderboard.html"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        today = date.today()
        filter_last_month = Q(taskreport__started_at__gte=today - timedelta(days=30))
        filter_last_week = Q(taskreport__started_at__gte=today - timedelta(days=7))
        filter_last_day = Q(taskreport__started_at__gte=today - timedelta(days=1))
        runtime = ExpressionWrapper(
            F('taskreport__done_at') - F('taskreport__started_at'),
            output_field=DurationField()
        )

        results = list(
            qs.annotate(
                total_cpu_usage=Sum('taskreport__cpu_cost'),
                total_gpu_usage=Sum('taskreport__gpu_cost'),
                last_month_cpu_usage=Sum('taskreport__cpu_cost', filter=filter_last_month),
                last_month_gpu_usage=Sum('taskreport__gpu_cost', filter=filter_last_month),
                total_tasks=Count('taskreport'),
                total_runtime=Sum(runtime),
                last_week_tasks=Count('taskreport', filter=filter_last_week),
                last_week_runtime=Sum(runtime, filter=filter_last_week),
                last_day_tasks=Count('taskreport', filter=filter_last_day),
                last_day_runtime=Sum(runtime, filter=filter_last_day)
            ).order_by(F('total_runtime').desc(nulls_last=True))
        )
        disk_usages_left = dict(qs.values('id').annotate(disk_usage=Sum('ocrmodel__file_size')).values_list('id', 'disk_usage'))
        disk_usages_right = dict(qs.values('id').annotate(disk_usage=Sum('document__parts__image_file_size')).values_list('id', 'disk_usage'))

        for user in results:
            user.disk_usage = (disk_usages_left[user.id] or 0) + (disk_usages_right[user.id] or 0)

        return results
