from django.contrib import admin

from reporting.models import TaskReport


class TaskReportAdmin(admin.ModelAdmin):
    list_display = ['label', 'method', 'workflow_state', 'user', 'cpu_cost', 'gpu_cost']


admin.site.register(TaskReport, TaskReportAdmin)
