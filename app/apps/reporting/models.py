from datetime import datetime, timezone

import psutil
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from escriptorium.celery import app

User = get_user_model()

# Dictionary to store CPU times for tasks.
task_cpu_times = {}


class TaskGroup(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    document = models.ForeignKey("core.Document", on_delete=models.CASCADE)
    task = models.CharField(max_length=256)

    class Meta:
        ordering = ["-created_at"]


class TaskReport(models.Model):
    WORKFLOW_STATE_QUEUED = 0
    WORKFLOW_STATE_STARTED = 1
    WORKFLOW_STATE_ERROR = 2
    WORKFLOW_STATE_DONE = 3
    WORKFLOW_STATE_CANCELED = 4
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_QUEUED, _("Queued")),
        (WORKFLOW_STATE_STARTED, _("Running")),
        (WORKFLOW_STATE_ERROR, _("Crashed")),
        (WORKFLOW_STATE_DONE, _("Finished")),
        (WORKFLOW_STATE_CANCELED, _("Canceled")),
    )
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_QUEUED,
        choices=WORKFLOW_STATE_CHOICES
    )
    group = models.ForeignKey(TaskGroup, null=True, on_delete=models.SET_NULL)

    label = models.CharField(max_length=256)
    messages = models.TextField(blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    done_at = models.DateTimeField(null=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # celery task id
    task_id = models.CharField(max_length=64, blank=True, null=True)

    # shared_task method name
    method = models.CharField(max_length=512, blank=True, null=True)

    cpu_cost = models.FloatField(blank=True, null=True)
    gpu_cost = models.FloatField(blank=True, null=True)

    document = models.ForeignKey(
        "core.Document", blank=True, null=True, on_delete=models.SET_NULL, related_name='reports'
    )
    document_part = models.ForeignKey(
        "core.DocumentPart", blank=True, null=True, on_delete=models.SET_NULL, related_name='reports'
    )
    ocr_model = models.ForeignKey(
        "core.OcrModel", blank=True, null=True, on_delete=models.SET_NULL, related_name='reports'
    )

    def append(self, text, logger_fct=None):
        if logger_fct:
            logger_fct(text)

        self.messages += text + '\n'
        self.save()

    @property
    def uri(self):
        return reverse('report-detail', kwargs={'pk': self.pk})

    def start(self):
        self.workflow_state = self.WORKFLOW_STATE_STARTED
        self.started_at = datetime.now(timezone.utc)
        # Start tracking CPU time when the task starts.
        task_id = self.task_id
        task_cpu_times[task_id] = psutil.Process().cpu_times()
        self.save()

    def cancel(self, username):
        self.workflow_state = self.WORKFLOW_STATE_CANCELED
        self.done_at = datetime.now(timezone.utc)

        canceled_by = "anonymous"
        if username:
            canceled_by = f"user {username}"
        self.append(f"Canceled by {canceled_by}")

        app.control.revoke(self.task_id, terminate=True)
        self.save()

    def error(self, message):
        # unrecoverable error
        self.workflow_state = self.WORKFLOW_STATE_ERROR
        self.done_at = datetime.now(timezone.utc)
        self.append(message)
        self.save()

    def end(self, extra_links=None):
        self.workflow_state = self.WORKFLOW_STATE_DONE
        self.done_at = datetime.now(timezone.utc)
        self.save()

    def calc_cpu_cost(self):
        # No need to calculate the CPU usage if the task was canceled/crashed before even starting
        if not self.started_at:
            return

        task_id = self.task_id
        if task_id in task_cpu_times:
            start_cpu_times = task_cpu_times.pop(task_id)
            end_cpu_times = psutil.Process().cpu_times()
            user_cpu_time = end_cpu_times.user - start_cpu_times.user
            system_cpu_time = end_cpu_times.system - start_cpu_times.system
            self.cpu_cost = (user_cpu_time + system_cpu_time) / 60
        else:
            self.cpu_cost = 0
        self.save()

    def calc_gpu_cost(self):
        # No need to calculate the GPU usage if the task was canceled/crashed before even starting
        if not self.started_at:
            return

        task_duration = (self.done_at - self.started_at).total_seconds()
        self.gpu_cost = (task_duration * settings.GPU_COST) / 60
        self.save()


TASK_FINAL_STATES = [TaskReport.WORKFLOW_STATE_ERROR, TaskReport.WORKFLOW_STATE_DONE, TaskReport.WORKFLOW_STATE_CANCELED]
