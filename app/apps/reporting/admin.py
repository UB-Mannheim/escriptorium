from django.contrib import admin

from reporting.models import TaskReport


class TaskReportAdmin(admin.ModelAdmin):
    list_display = ['label', 'method', 'workflow_state', 'user', 'document', 'cpu_cost', 'gpu_cost']
    list_filter = ('method', 'workflow_state')
    raw_id_fields = ('document', 'document_part')


admin.site.register(TaskReport, TaskReportAdmin)
