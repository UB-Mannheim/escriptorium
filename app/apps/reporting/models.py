from datetime import datetime, timezone

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class TaskReport(models.Model):
    WORKFLOW_STATE_QUEUED = 0
    WORKFLOW_STATE_STARTED = 1
    WORKFLOW_STATE_ERROR = 2
    WORKFLOW_STATE_DONE = 3
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_QUEUED, _("Queued")),
        (WORKFLOW_STATE_STARTED, _("Running")),
        (WORKFLOW_STATE_ERROR, _("Crashed")),
        (WORKFLOW_STATE_DONE, _("Finished"))
    )

    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_QUEUED,
        choices=WORKFLOW_STATE_CHOICES
    )
    label = models.CharField(max_length=256)
    messages = models.TextField(blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    done_at = models.DateTimeField(null=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # celery task id
    task_id = models.CharField(max_length=64, blank=True, null=True)

    def append(self, text):
        self.messages += text + '\n'

    def start(self, task_id):
        self.task_id = task_id
        self.workflow_state = self.WORKFLOW_STATE_STARTED
        self.started_at = datetime.now(timezone.utc)
        self.save()

    def error(self, message):
        # unrecoverable error
        self.workflow_state = self.WORKFLOW_STATE_ERROR
        self.append(message)
        self.save()

    def end(self):
        self.workflow_state = self.WORKFLOW_STATE_DONE
        self.done_at = datetime.now(timezone.utc)
        self.append('Done.')
        self.save()
