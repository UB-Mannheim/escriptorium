from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import FileExtensionValidator

from core.models import Document, DocumentPart, Transcription
from users.models import User
from imports.parsers import make_parser


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
    parts = ArrayField(models.IntegerField())
    import_file = models.FileField(
        upload_to='import_src/',
        validators=[FileExtensionValidator(
            allowed_extensions=['xml', 'alto'])])
    processed = models.PositiveIntegerField(default=0)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    
    def process(self):
        try:
            with open(self.import_file.path, 'r') as fh:
                parser = make_parser(fh)
            self.workflow_state = self.WORKFLOW_STATE_STARTED
            self.save()
            parts = DocumentPart.objects.filter(pk__in=self.parts)
            for obj in parser.parse(self.document, parts):
                self.processed += 1
                self.save()
            self.workflow_state = self.WORKFLOW_STATE_DONE
            self.save()
        except Exception as e:
            self.worflow_state = self.WORKFLOW_STATE_ERROR
            self.error_message = str(e)
            self.save()
            raise
