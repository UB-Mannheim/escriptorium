from datetime import datetime, timezone

from celery.task.control import revoke
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from core.models import Document, DocumentPart
from django.db.models import Count, Sum, F, CharField, Value as V
from django.db.models.functions import Concat
import re
from collections import Counter

from core.models import Document, DocumentPart

User = get_user_model()


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
        Document, blank=True, null=True, on_delete=models.SET_NULL, related_name='reports'
    )
    document_part = models.ForeignKey(
        DocumentPart, blank=True, null=True, on_delete=models.SET_NULL, related_name='reports'
    )

    def append(self, text):
        self.messages += text + '\n'

    @property
    def uri(self):
        return reverse('report-detail', kwargs={'pk': self.pk})

    def start(self):
        self.workflow_state = self.WORKFLOW_STATE_STARTED
        self.started_at = datetime.now(timezone.utc)
        self.save()

    def cancel(self, user_email):
        self.workflow_state = self.WORKFLOW_STATE_CANCELED
        self.done_at = datetime.now(timezone.utc)
        self.append(f"Canceled by user {user_email}")
        revoke(self.task_id, terminate=True)
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

    def calc_cpu_cost(self, nb_cores):
        # No need to calculate the CPU usage if the task was canceled/crashed before even starting
        if not self.started_at:
            return

        task_duration = (self.done_at - self.started_at).total_seconds()
        self.cpu_cost = (task_duration * nb_cores * settings.CPU_COST_FACTOR) / 60
        self.save()

    def calc_gpu_cost(self):
        # No need to calculate the GPU usage if the task was canceled/crashed before even starting
        if not self.started_at:
            return

        task_duration = (self.done_at - self.started_at).total_seconds()
        self.gpu_cost = (task_duration * settings.GPU_COST) / 60
        self.save()


class ProjectReport:
    def __init__(self, project, tags=None):
        project_document = self.get_queryset(project, tags)
        raw_transcription_content = ' '.join(list(filter(None, project_document.values_list('_part_lines_transcriptions', flat=True))))
        self.project_documentpart_total = self.aggregate_value(project_document, '_part_count')
        self.project_documentpart_rows_total = self.aggregate_value(project_document, '_part_lines_count')
        self.project_documentpart_region_total = self.aggregate_value(project_document, '_part_lines_block')
        self.project_create_at = project.created_at
        self.project_update_at = project.updated_at
        self.project_shared_group_total = project.shared_with_groups.all().count()
        self.project_shared_users_total = project.shared_with_users.all().count()
        self.project_document_group_shared_total = project_document.filter(shared_with_groups__isnull=False).count()
        self.project_document_user_shared_total = project_document.filter(shared_with_users__isnull=False).count()
        self.project_documentpart_rows_words_total = re.sub(r'[^\w\s]','', raw_transcription_content)
        self.project_documentpart_vocabulary = dict(sorted(Counter(raw_transcription_content).items()))
        self.project_documenttag_list = set(project_document.values_list('_document_per_tag', flat=True))
        self.project_lines_type = dict(Counter(project_document.values_list('_part_lines_count_typology', flat=True)))
        self.project_regions_type = dict(Counter(project_document.values_list('_part_lines_block_typology', flat=True)))

    def aggregate_value(self, model, field):
        return model.aggregate(Sum(field)).get(field + '__sum')
    
    def get_queryset(self, project, tags=None):
        qs = (Document
            .objects
            .filter(project=project)
            .annotate(_part_count=Count('parts'))
            .annotate(_part_lines_count=Count('parts__lines'))
            .annotate(_part_lines_transcriptions=F('parts__lines__transcriptions__content'))
            .annotate(_part_lines_block=Count('parts__lines__block', distinct=True))
            .annotate(_part_lines_count_typology=F('parts__lines__typology__name'))
            .annotate(_part_lines_block_typology=F('parts__lines__block__typology__name'))
            .annotate(_document_per_tag=Concat('project__document_tags__name', V('∂'), Count('project__document_tags__tags_document', distinct=True), output_field=CharField()))
            .only('shared_with_groups', 'shared_with_users', '_part_count', '_part_lines_count', '_part_lines_transcriptions', '_part_lines_block', '_document_per_tag','_part_lines_count_typology', '_part_lines_block_typology'))
        
        for tag in tags:
            qs = qs.filter(tags__name=tag)
        return qs
