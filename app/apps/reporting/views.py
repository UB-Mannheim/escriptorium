from datetime import date, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.views.generic import ListView, DetailView

from reporting.models import TaskReport
from users.models import User


class ReportList(LoginRequiredMixin, ListView):
    model = TaskReport
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return (qs.filter(user=self.request.user)
                .exclude(messages='')
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
        filter_last_week = Q(taskreport__started_at__gte=today - timedelta(days=7))
        filter_last_day = Q(taskreport__started_at__gte=today - timedelta(days=1))
        runtime = ExpressionWrapper(
            F('taskreport__done_at') - F('taskreport__started_at'),
            output_field=DurationField()
        )

        return qs.annotate(
            total_tasks=Count('taskreport'),
            total_runtime=Sum(runtime),
            last_week_tasks=Count('taskreport', filter=filter_last_week),
            last_week_runtime=Sum(runtime, filter=filter_last_week),
            last_day_tasks=Count('taskreport', filter=filter_last_day),
            last_day_runtime=Sum(runtime, filter=filter_last_day)
        ).order_by(F('total_runtime').desc(nulls_last=True))
