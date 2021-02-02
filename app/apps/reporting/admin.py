from django.contrib import admin

from reporting.models import TaskReport


class TaskReportAdmin(admin.ModelAdmin):
    list_display = ['label', 'workflow_state', 'user']


admin.site.register(TaskReport, TaskReportAdmin)
