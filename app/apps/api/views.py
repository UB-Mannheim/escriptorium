import json
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django_redis import get_redis_connection

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination
from rest_framework.serializers import PrimaryKeyRelatedField

from api.serializers import (UserOnboardingSerializer,
                             ProjectSerializer,
                             DocumentSerializer,
                             DocumentTasksSerializer,
                             PartDetailSerializer,
                             PartSerializer,
                             PartMoveSerializer,
                             BlockSerializer,
                             LineSerializer,
                             BlockTypeSerializer,
                             LineTypeSerializer,
                             DetailedLineSerializer,
                             LineOrderSerializer,
                             TranscriptionSerializer,
                             LineTranscriptionSerializer,
                             SegmentSerializer,
                             TrainSerializer,
                             SegTrainSerializer,
                             ScriptSerializer,
                             TranscribeSerializer,
                             OcrModelSerializer,
                             TagDocumentSerializer)

from core.models import (Project,
                         Document,
                         DocumentPart,
                         Block,
                         Line,
                         BlockType,
                         LineType,
                         Transcription,
                         LineTranscription,
                         OcrModel,
                         Script,
                         AlreadyProcessingException,
                         DocumentTag)

from core.tasks import recalculate_masks
from users.models import User
from users.consumers import send_event
from imports.forms import ImportForm, ExportForm
from imports.parsers import ParseError
from reporting.models import TaskReport
from versioning.models import NoChangeException
from reporting.models import TaskReport

logger = logging.getLogger(__name__)

redis_ = get_redis_connection()
CLIENT_TASK_NAME_MAP = {
    'segtrain': 'training',
    'train': 'training',
    'document_export': 'export',
    'document_import': 'import'
}


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserOnboardingSerializer

    @action(detail=False, methods=['put'])
    def onboarding(self, request):
        serializer = UserOnboardingSerializer(self.request.user, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(status=status.HTTP_200_OK)


class ScriptViewSet(ReadOnlyModelViewSet):
    queryset = Script.objects.all()
    paginate_by = 20
    serializer_class = ScriptSerializer


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    paginate_by = 10


class TagViewSet(ModelViewSet):
    queryset = DocumentTag.objects.all()
    serializer_class = TagDocumentSerializer
    paginate_by = 10

    def perform_create(self, serializer):
        project = Project.objects.get(pk=self.kwargs.get('project_pk'))
        return serializer.save(project=project)

    def get_queryset(self):
        return DocumentTag.objects.filter(project__pk=self.kwargs.get('project_pk'))


class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.for_user(self.request.user).prefetch_related(
            Prefetch('valid_block_types', queryset=BlockType.objects.order_by('name')),
            Prefetch('valid_line_types', queryset=LineType.objects.order_by('name')),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context

    def form_error(self, msg):
        return Response({'status': 'error', 'error': msg}, status=400)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def tasks(self, request):
        extra = {}

        if not request.user.is_staff:
            extra["owner"] = request.user
        else:
            # Filter results by owner
            user_id_filter = request.GET.get('user_id')

            if user_id_filter:
                try:
                    user_id_filter = int(user_id_filter)
                except ValueError:
                    return Response(
                        {'error': 'Invalid user_id, it should be an int.'},
                        status=400
                    )

                extra["owner"] = user_id_filter

        # Filter results by querying their name
        document_name_filter = request.GET.get('name')
        if document_name_filter:
            extra["name__icontains"] = document_name_filter

        # Filter results by TaskReport.workflow_state
        state_filter = request.GET.get('task_state', '').lower()
        if state_filter:
            mapped_labels = {label.lower():state for state, label in TaskReport.WORKFLOW_STATE_CHOICES}
            if state_filter not in mapped_labels:
                return Response(
                    {'error': 'Invalid task_state, it should match a valid workflow_state.'},
                    status=400
                )

            extra["reports__workflow_state__in"] = [mapped_labels[state_filter]]

        documents = Document.objects.filter(reports__isnull=False, **extra).select_related('owner').distinct()

        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = DocumentTasksSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DocumentTasksSerializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel_tasks(self, request, pk=None):
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND,
                data={'status': 'Not Found', 'error': f"Document with pk {pk} doesn't exist"}
            )

        if not request.user.is_staff and document.owner != request.user:
            raise PermissionDenied

        # Revoking all pending/running tasks for the specified document

        reports = (document.reports
                   .prefetch_related('document_part')
                   .filter(workflow_state__in=[TaskReport.WORKFLOW_STATE_QUEUED,
                                               TaskReport.WORKFLOW_STATE_STARTED]))
        count = len(reports)  # evaluate query
        for report in reports:
            report.cancel(request.user.email)

            method_name = report.method.split('.')[-1]
            task_name = CLIENT_TASK_NAME_MAP.get(method_name, method_name)

            if report.document_part:
                # Some glue code from DocumentPart.cancel_tasks function is moved here to prevent performance issues
                # update redis workflow state
                redis_.set('process-%d' % report.document_part.pk, json.dumps({report.method: {"status": "canceled"}}))
            else:
                try:
                    send_event('document', document.pk, f'{task_name}:error',
                               {'reason': _('Canceled.')})
                except Exception as e:
                    # don't crash on websocket error
                    logger.exception(e)

        if count:
            try:
                # send a single websocket message for all parts
                send_event('document', document.pk, 'parts:workflow', {
                    'parts': [{
                        'id': report.document_part.pk,
                        'process': task_name,
                        'status': 'error',
                        'reason': _('Canceled.')
                    } for report in reports]
                })
            except Exception as e:
                # don't crash on websocket error
                logger.exception(e)

        # Executing all the glue code outside the real revoking of tasks to maintain db objects
        # up-to-date with the real state of the app (e.g.: we stopped a training, we need to set
        # the model.training attribute to False)
        for model in document.ocr_models.filter(training=True):
            model.cancel_training(revoke_task=False)  # We already revoked the Celery task

        for doc_import in document.documentimport_set.all():
            doc_import.cancel(revoke_task=False)  # We already revoked the Celery task

        return Response({
            'status': 'canceled',
            'details': f'Canceled {count} pending/running tasks linked to document {document.name}.'
        })

    @action(detail=True, methods=['post'])
    def imports(self, request, pk=None):
        document = self.get_object()
        form = ImportForm(document, request.user,
                          request.POST, request.FILES)
        if form.is_valid():
            form.save()  # create the import
            try:
                form.process()
            except ParseError:
                return self.form_error("Incorrectly formatted file, couldn't parse it.")
            return Response({'status': 'ok'})
        else:
            return self.form_error(json.dumps(form.errors))

    @action(detail=True, methods=['post'])
    def cancel_import(self, request, pk=None):
        document = self.get_object()
        current_import = document.documentimport_set.order_by('started_on').last()
        if current_import.is_cancelable():
            current_import.cancel()
            return Response({'status': 'canceled'})
        else:
            return Response({'status': 'already stopped'}, status=400)

    @action(detail=True, methods=['post'])
    def cancel_training(self, request, pk=None):
        document = self.get_object()
        model = document.ocr_models.filter(training=True).last()
        try:
            model.cancel_training()
        except Exception as e:
            logger.exception(e)
            return Response({'status': 'failed'}, status=400)
        return Response({'status': 'canceled'})

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        document = self.get_object()
        form = ExportForm(document, request.user, request.POST)
        if form.is_valid():
            # return form.stream()
            form.process()
            return Response({'status': 'ok'})
        else:
            return self.form_error(json.dumps(form.errors))

    def get_process_response(self, request, serializer_class):
        document = self.get_object()
        serializer = serializer_class(document=document,
                                      user=request.user,
                                      data=request.data)
        if serializer.is_valid():
            try:
                serializer.process()
            except AlreadyProcessingException:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={'status': 'error',
                                      'error': 'Already processing.'})

            return Response(status=status.HTTP_200_OK,
                            data={'status': 'ok'})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={'status': 'error',
                                  'error': serializer.errors})

    @action(detail=True, methods=['post'])
    def segment(self, request, pk=None):
        return self.get_process_response(request, SegmentSerializer)

    @action(detail=True, methods=['post'])
    def train(self, request, pk=None):
        return self.get_process_response(request, TrainSerializer)

    @action(detail=True, methods=['post'])
    def segtrain(self, request, pk=None):
        return self.get_process_response(request, SegTrainSerializer)

    @action(detail=True, methods=['post'])
    def transcribe(self, request, pk=None):
        return self.get_process_response(request, TranscribeSerializer)


class DocumentPermissionMixin():
    def get_queryset(self):
        try:
            Document.objects.for_user(self.request.user).get(pk=self.kwargs.get('document_pk'))
        except Document.DoesNotExist:
            raise PermissionDenied
        return super().get_queryset()


class PartViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = DocumentPart.objects.all().select_related('document')

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(document=self.kwargs.get('document_pk'))
        if self.action == 'retrieve':
            return qs.prefetch_related('lines', 'blocks')
        else:
            return qs

    def get_serializer_class(self):
        # different serializer because we don't want to query all the lines in the list view
        if self.action == 'retrieve':
            return PartDetailSerializer
        else:  # list & create
            return PartSerializer

    @action(detail=False, methods=['get'])
    def byorder(self, request, document_pk=None):
        try:
            order = int(request.GET.get('order'))
        except ValueError:
            return Response({'error': 'invalid order.'})
        if not order:
            return Response({'error': 'pass order as an url parameter.'})
        try:
            part = self.get_queryset().get(order=order)
        except DocumentPart.DoesNotExist:
            return Response({'error': 'Out of bounds.'})
        return HttpResponseRedirect(reverse('api:part-detail',
                                            kwargs={'document_pk': self.kwargs.get('document_pk'),
                                                    'pk': part.pk}))

    @action(detail=True, methods=['post'])
    def move(self, request, document_pk=None, pk=None):
        part = DocumentPart.objects.get(document=document_pk, pk=pk)
        serializer = PartMoveSerializer(part=part, data=request.data)
        if serializer.is_valid():
            serializer.move()
            return Response({'status': 'moved'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, document_pk=None, pk=None):
        part = DocumentPart.objects.get(document=document_pk, pk=pk)
        part.cancel_tasks()
        part.refresh_from_db()
        del part.tasks  # reset cache
        return Response({'status': 'canceled', 'workflow': part.workflow})

    @action(detail=True, methods=['post'])
    def reset_masks(self, request, document_pk=None, pk=None):
        # If quotas are enforced, assert that the user still has free CPU minutes
        if not settings.DISABLE_QUOTAS and not request.user.has_free_cpu_minutes():
            return Response({'error': "You don't have any CPU minutes left."}, status=status.HTTP_400_BAD_REQUEST)
        part = DocumentPart.objects.get(document=document_pk, pk=pk)
        onlyParam = request.query_params.get("only")
        only = onlyParam and list(map(int, onlyParam.split(',')))
        recalculate_masks.delay(instance_pk=part.pk, user_pk=request.user.pk, only=only)
        return Response({'status': 'ok'})

    @action(detail=True, methods=['post'])
    def recalculate_ordering(self, request, document_pk=None, pk=None):
        document_part = DocumentPart.objects.get(pk=pk)
        document_part.recalculate_ordering()
        serializer = LineOrderSerializer(document_part.lines.all(), many=True)
        return Response({'status': 'done', 'lines': serializer.data}, status=200)

    @action(detail=True, methods=['post'])
    def rotate(self, request, document_pk=None, pk=None):
        document_part = DocumentPart.objects.get(pk=pk)
        angle = self.request.data.get('angle')
        if angle:
            document_part.rotate(angle)
            return Response({'status': 'done'}, status=200)
        else:
            return Response({'error': "Post an angle."},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def crop(self, request, document_pk=None, pk=None):
        document_part = DocumentPart.objects.get(pk=pk)
        x1 = self.request.data.get('x1')
        y1 = self.request.data.get('y1')
        x2 = self.request.data.get('x2')
        y2 = self.request.data.get('y2')
        if (x1 is not None
            and y1 is not None
            and x2 is not None
            and y2 is not None):
            document_part.crop(x1, y1, x2, y2)
            return Response({'status': 'done'}, status=200)
        else:
            return Response({'error': "Post corners as x1, y1 (top left) and x2, y2 (bottom right)."},
                            status=status.HTTP_400_BAD_REQUEST)


class DocumentTranscriptionViewSet(ModelViewSet):
    # Note: there is no dedicated Transcription viewset, it's always in the context of a Document
    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer
    pagination_class = None

    def get_queryset(self):
        return Transcription.objects.filter(
            archived=False,
            document=self.kwargs['document_pk'])

    def perform_delete(self, serializer):
        serializer.instance.archive()


class BlockTypeViewSet(ModelViewSet):
    queryset = BlockType.objects.filter(public=True)
    serializer_class = BlockTypeSerializer


class LineTypeViewSet(ModelViewSet):
    queryset = LineType.objects.filter(public=True)
    serializer_class = LineTypeSerializer


class BlockViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = Block.objects.select_related('typology')
    serializer_class = BlockSerializer

    def get_queryset(self):
        return (super().get_queryset()
                .filter(document_part=self.kwargs['part_pk'])
                .filter(document_part__document=self.kwargs['document_pk']))


class LineViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = (Line.objects.select_related('block')
                            .select_related('typology'))

    def get_queryset(self):
        return (super().get_queryset()
                .filter(document_part=self.kwargs['part_pk'])
                .filter(document_part__document=self.kwargs['document_pk']))

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DetailedLineSerializer
        else:  # create, list
            return LineSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request, document_pk=None, part_pk=None):
        lines = request.data.get("lines")
        serializer = LineSerializer(data=lines, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'ok', 'lines': serializer.data})

    @action(detail=False, methods=['put'])
    def bulk_update(self, request, document_pk=None, part_pk=None):
        lines = request.data.get("lines")
        qs = self.get_queryset().filter(pk__in=[line['pk'] for line in lines])
        serializer = LineSerializer(qs, data=lines, partial=True, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'ok', 'lines': serializer.data}, status=200)

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request, document_pk=None, part_pk=None):
        deleted_lines = request.data.get("lines")
        qs = Line.objects.filter(pk__in=deleted_lines)
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def move(self, request, document_pk=None, part_pk=None, pk=None):
        data = request.data.get('lines')
        qs = Line.objects.filter(pk__in=[l['pk'] for l in data])
        serializer = LineOrderSerializer(qs, data=data, many=True)
        if serializer.is_valid():
            resp = serializer.save()
            return Response(resp, status=200)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100


class LineTranscriptionViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = LineTranscription.objects.all()
    serializer_class = LineTranscriptionSerializer
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        qs = (super().get_queryset()
              .filter(line__document_part=self.kwargs['part_pk'])
              .filter(line__document_part__document=self.kwargs['document_pk'])
              .select_related('line', 'transcription')
              .order_by('line__order'))
        transcription = self.request.GET.get('transcription')
        if transcription:
            qs = qs.filter(transcription=transcription)
        return qs

    def create(self, request, document_pk=None, part_pk=None):
        response = super().create(request, document_pk=document_pk, part_pk=part_pk)
        document_part = DocumentPart.objects.get(pk=part_pk)
        document_part.calculate_progress()
        document_part.save()
        return response

    def perform_create(self, serializer):
        serializer.save(version_author=self.request.user.username)

    def update(self, request, document_pk=None, part_pk=None, pk=None, partial=False):
        instance = self.get_object()
        try:
            instance.new_version(author=request.user.username,
                                 source=settings.VERSIONING_DEFAULT_SOURCE)
        except NoChangeException:
            # Note we can safely pass here
            pass

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def get_serializer_class(self):
        lines = Line.objects.filter(document_part=self.kwargs['part_pk'])

        class RuntimeSerializer(self.serializer_class):
            line = PrimaryKeyRelatedField(queryset=lines)
        return RuntimeSerializer

    @action(detail=False, methods=['POST'])
    def bulk_create(self, request, document_pk=None, part_pk=None, pk=None):
        lines = request.data.get("lines")
        serializer = LineTranscriptionSerializer(data=lines, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'status': 'ok', 'lines': serializer.data}, status=200)

    @action(detail=False, methods=['PUT'])
    def bulk_update(self, request, document_pk=None, part_pk=None, pk=None):
        lines = request.data.get('lines')
        response = []
        errors = []
        for line in lines:
            lt = get_object_or_404(LineTranscription, pk=line["pk"])
            serializer = LineTranscriptionSerializer(lt, data=line, partial=True)

            if serializer.is_valid():
                try:
                    lt.new_version(author=request.user.username,
                                   source=settings.VERSIONING_DEFAULT_SOURCE)
                except NoChangeException:
                    pass

                serializer.save()
                response.append(serializer.data)

            else:
                errors.append(errors)

        if errors:
            return Response(errors,
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(status=200, data=response)

    @action(detail=False, methods=['POST'])
    def bulk_delete(self, request, document_pk=None, part_pk=None, pk=None):
        lines = request.data.get("lines")
        qs = LineTranscription.objects.filter(pk__in=lines)
        qs.update(content='')
        return Response(status=status.HTTP_204_NO_CONTENT, )


class OcrModelViewSet(ModelViewSet):
    queryset = OcrModel.objects.all()
    serializer_class = OcrModelSerializer

    def get_queryset(self):
        return (super().get_queryset()
                .filter(owner=self.request.user))

    @action(detail=True, methods=['post'])
    def cancel_training(self, request, pk=None):
        model = self.get_object()
        try:
            model.cancel_training()
        except Exception as e:
            logger.exception(e)
            return Response({'status': 'failed'}, status=400)
        return Response({'status': 'canceled'})
