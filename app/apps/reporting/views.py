from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from reporting.models import TaskReport


class ReportList(LoginRequiredMixin, ListView):
    model = TaskReport
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class ReportDetail(LoginRequiredMixin, DetailView):
    model = TaskReport
    context_object_name = 'report'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)
