import os.path

from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import Document
from imports.parsers import XML_EXTENSIONS, make_parser
from reporting.models import TaskReport
from users.models import User


def document_import_path(instance, filename):
    return "import_src/{0}/{1}".format(instance.document.pk, filename)


class DocumentImport(models.Model):
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

    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    started_on = models.DateTimeField(auto_now_add=True)
    started_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL)
    workflow_state = models.PositiveSmallIntegerField(
        default=WORKFLOW_STATE_CREATED,
        choices=WORKFLOW_STATE_CHOICES)
    error_message = models.CharField(
        null=True, blank=True, max_length=512)

    name = models.CharField(max_length=256, blank=True)
    override = models.BooleanField(default=False)
    import_file = models.FileField(
        upload_to=document_import_path,
        validators=[FileExtensionValidator(
            allowed_extensions=XML_EXTENSIONS + ['json'])])
    with_mets = models.BooleanField(default=False)
    mets_base_uri = models.CharField(null=True, blank=True, max_length=512)

    report = models.ForeignKey(TaskReport, max_length=64,
                               null=True, blank=True,
                               on_delete=models.CASCADE)
    processed = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=None, null=True, blank=True)

    class Meta:
        ordering = ['-started_on']

    @property
    def filename(self):
        return os.path.basename(self.import_file.name)

    @property
    def failed(self):
        return self.workflow_state == self.WORKFLOW_STATE_ERROR

    @property
    def ongoing(self):
        return self.workflow_state == self.WORKFLOW_STATE_STARTED

    def is_cancelable(self):
        return self.workflow_state < self.WORKFLOW_STATE_DONE

    def cancel(self, revoke_task=True, username=None):
        self.workflow_state = self.WORKFLOW_STATE_ERROR
        self.error_message = 'canceled'
        self.save()
        if revoke_task and self.report and self.report.task_id:
            self.report.cancel(username)

    def process(self, resume=True):
        try:
            self.workflow_state = self.WORKFLOW_STATE_STARTED
            self.save()

            start_at = resume and self.processed or 0
            parser = make_parser(self.document, self.import_file,
                                 name=self.name, report=self.report,
                                 mets_describer=self.with_mets,
                                 mets_base_uri=self.mets_base_uri)
            for obj in parser.parse(start_at=start_at,
                                    override=self.override,
                                    user=self.started_by):
                self.processed += 1
                self.save()
                yield obj
            self.workflow_state = self.WORKFLOW_STATE_DONE
            self.save()

        except Exception as e:
            self.workflow_state = self.WORKFLOW_STATE_ERROR
            self.error_message = str(e)[:512]
            self.report.error(str(e))
            self.save()
            raise e

        else:
            parser.clean()
