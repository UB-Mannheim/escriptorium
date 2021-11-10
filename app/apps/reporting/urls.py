from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from reporting.views import QuotasLeaderboard, ReportDetail, ReportList, ProjectReport

urlpatterns = [
    path('quotas/', ReportList.as_view(), name='report-list'),
    path('quotas/<int:pk>/', ReportDetail.as_view(), name='report-detail'),
    path('quotas/instance/', staff_member_required(QuotasLeaderboard.as_view()), name='quotas-leaderboard'),
    path('project/<str:slug>/reports/', ProjectReport.as_view(), name='project-report'),
]
