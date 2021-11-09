from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from reporting.views import ReportList, ReportDetail, QuotasLeaderboard


urlpatterns = [
    path('quotas/', ReportList.as_view(), name='report-list'),
    path('quotas/<int:pk>/', ReportDetail.as_view(), name='report-detail'),
    path('quotas/instance/', staff_member_required(QuotasLeaderboard.as_view()), name='quotas-leaderboard'),
]
