from django.db import models
from django.utils.functional import cached_property
from django.contrib.postgres.fields import ArrayField
from django.core.validators import FileExtensionValidator

#from celery.task.control import revoke
from escriptorium.celery import app

from core.models import Document, DocumentPart, Transcription
from users.models import User
from users.consumers import send_event
from imports.parsers import make_parser, XML_EXTENSIONS


# TODO: now that i think about it, it's probably a terrible idea to name something Import.
class Import(models.Model):
    WORKFLOW_STATE_CREATED = 0
    WORKFLOW_STATE_STARTED = 1
    WORKFLOW_STATE_DONE = 2
    WORKFLOW_STATE_ERROR = 5
    WORKFLOW_STATE_CHOICES = (
        (WORKFLOW_STATE_CREATED, 'Created'),
        (WORKFLOW_STATE_STARTED, 'Started'),
        (WORKFLOW_STATE_DONE, 'Done'),
        (WORKFLOW_STATE_ERROR, 'Error'),
    )
    
    started_on = models.DateTimeField(auto_now_add=True)
    started_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL)
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_CREATED,
        choices=WORKFLOW_STATE_CHOICES)
    error_message = models.CharField(
        null=True, blank=True, max_length=512)

    name = models.CharField(max_length=256, blank=True)
    override = models.BooleanField(default=True)
    parts = ArrayField(models.IntegerField(), blank=True)
    import_file = models.FileField(
        upload_to='import_src/',
        validators=[FileExtensionValidator(
            allowed_extensions=XML_EXTENSIONS + ['json',])])
    
    task_id = models.CharField(max_length=64, blank=True)
    processed = models.PositiveIntegerField(default=0)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ('-started_on',)
    
    @property
    def failed(self):
        return self.workflow_state == self.WORKFLOW_STATE_ERROR
    
    @property
    def ongoing(self):
        return self.workflow_state == self.WORKFLOW_STATE_STARTED
    
    @property
    def total(self):
        return self.parser.total
    
    @cached_property
    def parser(self):
        return make_parser(self.import_file, name=self.name, override=self.override)

    def is_cancelable(self):
        return self.workflow_state < self.WORKFLOW_STATE_DONE
    
    def cancel(self):
        self.workflow_state = self.WORKFLOW_STATE_ERROR
        self.error_message = 'canceled'
        if self.task_id:
            #revoke(self.task_id, terminate=True)
            app.control.revoke(self.task_id, terminate=True)
        self.save()
    
    def process(self, resume=True):
        try:
            self.workflow_state = self.WORKFLOW_STATE_STARTED
            self.save()
            parts = DocumentPart.objects.filter(pk__in=self.parts)
            start_at = resume and self.processed or 0
            for obj in self.parser.parse(self.document, parts, start_at=start_at):
                self.processed += 1
                self.save()
                yield obj
            self.workflow_state = self.WORKFLOW_STATE_DONE
            self.save()
        except Exception as e:
            self.worflow_state = self.WORKFLOW_STATE_ERROR
            self.error_message = str(e)
            self.save()
            raise e

