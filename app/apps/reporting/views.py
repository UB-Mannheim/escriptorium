from collections import Counter, OrderedDict
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.aggregates.general import StringAgg
from django.core.paginator import Page, Paginator
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.utils.functional import cached_property
from django.views.generic import DetailView, ListView
from django.views.generic.base import TemplateView

from core.models import Document, LineTranscription, Project
from reporting.models import TaskReport
from users.models import User


class ReportList(LoginRequiredMixin, ListView):
    model = TaskReport
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        cpu_usage = self.request.user.calc_cpu_usage()
        context['cpu_cost_last_week'] = cpu_usage
        gpu_usage = self.request.user.calc_gpu_usage()
        context['gpu_cost_last_week'] = gpu_usage

        disk_storage_limit = self.request.user.disk_storage_limit()
        context['enforce_disk_storage'] = not settings.DISABLE_QUOTAS and disk_storage_limit is not None
        if context['enforce_disk_storage']:
            context['disk_storage_used_percentage'] = min(round((self.request.user.calc_disk_usage() * 100) / disk_storage_limit, 2) if disk_storage_limit else 100, 100)

        cpu_minutes_limit = self.request.user.cpu_minutes_limit()
        context['enforce_cpu'] = not settings.DISABLE_QUOTAS and cpu_minutes_limit is not None
        if context['enforce_cpu']:
            context['cpu_minutes_used_percentage'] = min(round((cpu_usage * 100) / cpu_minutes_limit, 2) if cpu_minutes_limit else 100, 100)

        gpu_minutes_limit = self.request.user.gpu_minutes_limit()
        context['enforce_gpu'] = not settings.DISABLE_QUOTAS and gpu_minutes_limit is not None
        if context['enforce_gpu']:
            context['gpu_minutes_used_percentage'] = min(round((gpu_usage * 100) / gpu_minutes_limit, 2) if gpu_minutes_limit else 100, 100)

        return context

    def get_queryset(self):
        qs = super().get_queryset()

        blacklist = [
            'core.tasks.lossless_compression',
            'core.tasks.convert',
            'core.tasks.generate_part_thumbnails',
            'users.tasks.async_email',
            'core.tasks.recalculate_masks'
        ]

        return (qs.filter(user=self.request.user)
                  .exclude(method__in=blacklist)
                  .annotate(duration=ExpressionWrapper(F('done_at') - F('started_at'),
                                                       output_field=DurationField()))
                  .order_by('-queued_at'))


class ReportDetail(LoginRequiredMixin, DetailView):
    model = TaskReport
    context_object_name = 'report'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class CustomPaginator(Paginator):

    def __init__(self, *args, **kwargs):
        self._count = kwargs.pop('total')
        super(CustomPaginator, self).__init__(*args, **kwargs)

    @cached_property
    def count(self):
        return self._count

    def page(self, number):
        number = self.validate_number(number)
        return Page(self.object_list, number, self)


class QuotasLeaderboard(LoginRequiredMixin, TemplateView):
    template_name = "reporting/quotas_leaderboard.html"
    paginate_by = 20

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['enforce_quotas'] = not settings.DISABLE_QUOTAS

        try:
            page = int(self.request.GET.get('page', '1'))
        except ValueError:
            page = 1
        offset = (page - 1) * self.paginate_by

        today = date.today()
        filter_last_week = Q(taskreport__started_at__gte=today - timedelta(days=7))
        filter_last_day = Q(taskreport__started_at__gte=today - timedelta(days=1))
        runtime = ExpressionWrapper(
            F('taskreport__done_at') - F('taskreport__started_at'),
            output_field=DurationField()
        )

        qs = User.objects.all()
        results = list(
            qs.annotate(
                total_cpu_usage=Sum('taskreport__cpu_cost'),
                total_gpu_usage=Sum('taskreport__gpu_cost'),
                last_week_cpu_usage=Sum('taskreport__cpu_cost', filter=filter_last_week),
                last_week_gpu_usage=Sum('taskreport__gpu_cost', filter=filter_last_week),
                total_tasks=Count('taskreport'),
                total_runtime=Sum(runtime),
                last_week_tasks=Count('taskreport', filter=filter_last_week),
                last_week_runtime=Sum(runtime, filter=filter_last_week),
                last_day_tasks=Count('taskreport', filter=filter_last_day),
                last_day_runtime=Sum(runtime, filter=filter_last_day)
            ).order_by(F('total_runtime').desc(nulls_last=True))[offset:offset + self.paginate_by]
        )
        disk_usages_left = dict(qs.values('id').annotate(disk_usage=Sum('ocrmodel__file_size')).values_list('id', 'disk_usage'))
        disk_usages_right = dict(qs.values('id').annotate(disk_usage=Sum('document__parts__image_file_size')).values_list('id', 'disk_usage'))

        for user in results:
            user.disk_usage = (disk_usages_left[user.id] or 0) + (disk_usages_right[user.id] or 0)

        # Pagination
        paginator = CustomPaginator(results, self.paginate_by, total=qs.count())

        if page > paginator.num_pages:
            page = paginator.num_pages

        context['page_obj'] = paginator.page(page)
        context['is_paginated'] = paginator.num_pages > 1

        return context


class ProjectReport(LoginRequiredMixin, DetailView):
    template_name = 'reporting/project_reports.html'
    model = Project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object
        context['filters'] = self.request.GET.getlist('tags')
        context['vocabulary'] = self.request.GET.get('vocabulary')
        context['document_tags'] = list(self.object.document_tags.annotate(document_count=Count('tags_document', distinct=True)).values())
        context['part_count'] = self.get_aggregate_sum('part_count')
        context['part_lines_count'] = self.get_aggregate_sum('part_lines_count')
        context['documents_shared_with_users'] = self.get_aggregate_sum('documents_shared_with_users')
        context['documents_shared_with_groups'] = self.get_aggregate_sum('documents_shared_with_groups')
        context['part_lines_transcriptions'] = self.get_aggregate('part_lines_transcriptions')
        context['part_lines_typology'] = self.get_typology_count('part_lines_typology')
        context['part_block_typology'] = self.get_typology_count('part_block_typology')
        context['part_block_count'] = self.get_aggregate_sum('part_block_count')

        return context

    def get_object(self):
        project = Project.objects.get(slug=self.kwargs.get('slug'))
        self.documents = project.documents.exclude(workflow_state=Document.WORKFLOW_STATE_ARCHIVED)

        for tag in self.request.GET.getlist('tags'):
            self.documents = self.documents.filter(tags__name=tag)

        return project

    def get_aggregate_sum(self, field):
        document_list = self.documents

        if field == 'part_count':
            document_list = document_list.annotate(part_count=Count('parts', distinct=True))
        elif field == 'part_lines_count':
            document_list = document_list.annotate(part_lines_count=Count('parts__lines', distinct=True))
        elif field == 'documents_shared_with_users':
            document_list = document_list.annotate(documents_shared_with_users=Count('shared_with_users', distinct=True))
        elif field == 'documents_shared_with_groups':
            document_list = document_list.annotate(documents_shared_with_groups=Count('shared_with_groups', distinct=True))
        elif field == 'part_lines_typology':
            document_list = document_list.annotate(part_lines_typology=StringAgg('parts__lines__typology__name', delimiter='|'))
        elif field == 'part_block_typology':
            document_list = document_list.annotate(part_block_typology=StringAgg('parts__blocks__typology__name', delimiter='|'))
        elif field == 'part_block_count':
            document_list = document_list.annotate(part_block_count=Count('parts__blocks', distinct=True))

        sum = document_list.aggregate(data=Sum(field)).get('data')
        if sum is None:
            sum = 0
        return sum

    def get_aggregate(self, field, delimiter=' '):
        document_list = self.documents

        if field == 'part_lines_transcriptions':
            document_list = document_list.annotate(part_lines_transcriptions=StringAgg('parts__lines__transcriptions__content', delimiter=' '))
        elif field == 'part_lines_typology':
            document_list = document_list.annotate(part_lines_typology=StringAgg('parts__lines__typology__name', delimiter='|'))
        elif field == 'part_block_typology':
            document_list = document_list.annotate(part_block_typology=StringAgg('parts__blocks__typology__name', delimiter='|'))

        return document_list.aggregate(data=StringAgg(field, delimiter=delimiter)).get('data')

    def get_typology_count(self, field):
        value = self.get_aggregate(field, '|')
        return OrderedDict(Counter(value.split('|'))).items() if value else ''


class DocumentReport(LoginRequiredMixin, DetailView):
    template_name = 'reporting/document_report.html'
    model = Document

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # get form data
        transcription_pk = self.request.GET.get('transcription')
        all_transcriptions = self.object.transcriptions.all()

        # set self.transcriptions to those matching PK, or all transcriptions
        if transcription_pk and transcription_pk != "all":
            self.transcriptions = self.object.transcriptions.filter(pk=int(transcription_pk))
            context['selected_transcription'] = self.transcriptions.first()
        else:
            self.transcriptions = all_transcriptions

        context['document'] = self.object
        context['all_transcriptions'] = all_transcriptions
        context['part_count'] = self.object.parts.count()
        context['transcribed_part_count'] = self.get_transcribed_part_count()
        context['avg_ocr_confidence'] = self.get_ocr_confidence()
        context['part_lines_transcriptions'] = self.get_part_lines_transcriptions()
        context['vocabulary'] = self.request.GET.get('vocabulary')
        return context

    def get_part_lines_transcriptions(self):
        document_list = Document.objects.filter(pk=self.object.pk)
        document_list = document_list.annotate(
            part_lines_transcriptions=StringAgg('parts__lines__transcriptions__content', delimiter=' ', filter=Q(parts__lines__transcriptions__transcription__in=self.transcriptions)),
        )
        return document_list.aggregate(data=StringAgg("part_lines_transcriptions", delimiter=' ')).get('data')

    def get_transcribed_part_count(self):
        """Count the number of document parts in selected transcription(s)"""
        # since DocumentPart is not directly related to Transcription, we have to go through
        # related objects Line and LineTranscription

        # get part PKs from this document
        part_pks = self.object.parts.values_list('pk', flat=True)
        # get transcription PKs from applied filter
        transcription_pks = self.transcriptions.values_list('pk', flat=True)
        return LineTranscription.objects.filter(     # find all LineTranscriptions that contain
            line__document_part__pk__in=part_pks,    # lines related to DocumentParts on this doc,
            transcription__pk__in=transcription_pks  # and whose transcription matches the filter
        ).values(
            "line__document_part"  # count the distinct related DocumentParts
        ).distinct().count()

    def get_ocr_confidence(self):
        """Compute the average confidence for selected transcription(s)"""
        return self.transcriptions.aggregate(avg=Avg("avg_confidence")).get("avg")
