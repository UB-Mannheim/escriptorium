from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from reporting.views import ReportList, ReportDetail, QuotasLeaderboard


urlpatterns = [
    path('reports/', ReportList.as_view(), name='report-list'),
    path('reports/<int:pk>/', ReportDetail.as_view(), name='report-detail'),
    path('quotas/instance/', staff_member_required(QuotasLeaderboard.as_view()), name='quotas-leaderboard'),
]
