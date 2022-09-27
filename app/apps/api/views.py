import json
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.serializers import PrimaryKeyRelatedField
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.serializers import (
    AnnotationComponentSerializer,
    AnnotationTaxonomySerializer,
    AnnotationTypeSerializer,
    BlockSerializer,
    BlockTypeSerializer,
    DetailedLineSerializer,
    DocumentMetadataSerializer,
    DocumentPartMetadataSerializer,
    DocumentPartTypeSerializer,
    DocumentSerializer,
    DocumentTasksSerializer,
    ImageAnnotationSerializer,
    LineOrderSerializer,
    LineSerializer,
    LineTranscriptionSerializer,
    LineTypeSerializer,
    OcrModelSerializer,
    PartDetailSerializer,
    PartMoveSerializer,
    PartSerializer,
    ProjectSerializer,
    ScriptSerializer,
    SegmentSerializer,
    SegTrainSerializer,
    TagDocumentSerializer,
    TextAnnotationSerializer,
    TrainSerializer,
    TranscribeSerializer,
    TranscriptionSerializer,
    UserSerializer,
)
from core.merger import MAX_MERGE_SIZE, merge_lines
from core.models import (
    AlreadyProcessingException,
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    Block,
    BlockType,
    Document,
    DocumentMetadata,
    DocumentPart,
    DocumentPartMetadata,
    DocumentPartType,
    DocumentTag,
    ImageAnnotation,
    Line,
    LineTranscription,
    LineType,
    OcrModel,
    Project,
    ProtectedObjectException,
    Script,
    TextAnnotation,
    Transcription,
)
from core.tasks import recalculate_masks
from imports.forms import ExportForm, ImportForm
from imports.parsers import ParseError
from reporting.models import TaskReport
from users.consumers import send_event
from users.models import User
from versioning.models import NoChangeException

logger = logging.getLogger(__name__)

redis_ = get_redis_connection()
CLIENT_TASK_NAME_MAP = {
    'segtrain': 'training',
    'train': 'training',
    'document_export': 'export',
    'document_import': 'import'
}


class IsAdminOrSelfOnly(BasePermission):
    """
    Permission class letting a non-admin user only update his own record,
    and admin users can update everyone and create/delete users.
    Really only makes sense for the UserViewset.
    """

    def has_permission(self, request, view):
        return bool(request.method in ("GET", "PUT", "PATCH")
                    or (request.method in ("POST", "DELETE") and request.user.is_staff))

    def has_object_permission(self, request, view, obj):
        return bool(obj == request.user
                    or request.user.is_staff)


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminOrSelfOnly,)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            return qs.filter(id=self.request.user.id)
        return qs


class ScriptViewSet(ReadOnlyModelViewSet):
    queryset = Script.objects.all()
    serializer_class = ScriptSerializer


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.for_user_read(self.request.user)


class TagViewSet(ModelViewSet):
    queryset = DocumentTag.objects.all()
    serializer_class = TagDocumentSerializer

    def perform_create(self, serializer):
        project = Project.objects.get(pk=self.kwargs.get('project_pk'))
        return serializer.save(project=project)

    def get_queryset(self):
        return DocumentTag.objects.filter(project__pk=self.kwargs.get('project_pk'))


class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

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
            mapped_labels = {label.lower(): state for state, label in TaskReport.WORKFLOW_STATE_CHOICES}
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
                if report.document_part:
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
            self.document = (Document.objects
                             .for_user(self.request.user)
                             .get(pk=self.kwargs.get('document_pk')))
        except Document.DoesNotExist:
            raise PermissionDenied
        return super().get_queryset()


class DocumentMetadataViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = DocumentMetadata.objects.all().select_related('document')
    serializer_class = DocumentMetadataSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(document=self.kwargs.get('document_pk'))
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['document'] = Document.objects.get(pk=self.kwargs.get('document_pk'))
        return context


class PartMetadataViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = DocumentPartMetadata.objects.all().select_related('part')
    serializer_class = DocumentPartMetadataSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(part=self.kwargs.get('part_pk'))
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['part'] = DocumentPart.objects.get(pk=self.kwargs.get('part_pk'))
        return context


class PartViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = DocumentPart.objects.all().select_related('document')

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(document=self.kwargs.get('document_pk'))
        if self.action == 'retrieve':
            return qs.prefetch_related('lines', 'blocks', 'metadata')
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
        except TypeError:
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
        try:
            del part.tasks  # reset cache, if present
        except AttributeError:
            pass
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
            document_part.rotate(angle, user=self.request.user)
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

    def destroy(self, request, *args, **kwargs):
        try:
            self.get_object().archive()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedObjectException:
            return Response("This object can not be deleted.", status=400)


class BlockTypeViewSet(ModelViewSet):
    queryset = BlockType.objects.filter(public=True)
    serializer_class = BlockTypeSerializer


class LineTypeViewSet(ModelViewSet):
    queryset = LineType.objects.filter(public=True)
    serializer_class = LineTypeSerializer


class AnnotationTypeViewSet(ModelViewSet):
    queryset = AnnotationType.objects.filter(public=True)
    serializer_class = AnnotationTypeSerializer


class DocumentPartTypeViewSet(ModelViewSet):
    queryset = DocumentPartType.objects.filter(public=True)
    serializer_class = DocumentPartTypeSerializer


class AnnotationComponentViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = AnnotationComponent.objects.all()
    serializer_class = AnnotationComponentSerializer

    def get_queryset(self):
        return super().get_queryset().filter(document=self.document)


class AnnotationTaxonomyViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = AnnotationTaxonomy.objects.all()
    serializer_class = AnnotationTaxonomySerializer

    def get_queryset(self):
        qs = (super().get_queryset()
              .filter(document=self.document)
              .prefetch_related('typology', 'components'))
        target = self.request.query_params.get('target')
        if target == 'image':
            return qs.filter(
                marker_type__in=[c[0] for c in AnnotationTaxonomy.IMG_MARKER_TYPE_CHOICES])
        elif target == 'text':
            return qs.filter(
                marker_type__in=[c[0] for c in AnnotationTaxonomy.TEXT_MARKER_TYPE_CHOICES])
        else:
            return qs


class ImageAnnotationViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = ImageAnnotation.objects.all()
    serializer_class = ImageAnnotationSerializer
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        return (super().get_queryset()
                .filter(part=self.kwargs['part_pk'])
                .filter(part__document=self.kwargs['document_pk']))


class TextAnnotationViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = TextAnnotation.objects.all()
    serializer_class = TextAnnotationSerializer
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        qs = (super().get_queryset()
              .filter(part=self.kwargs['part_pk'])
              .filter(part__document=self.kwargs['document_pk']))
        try:
            transcription = int(self.request.GET.get('transcription'))
        except (ValueError, TypeError):
            pass
        else:
            qs = qs.filter(transcription=transcription)
        return qs


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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = DetailedLineSerializer(instance)
        json = serializer.data
        super().destroy(request, *args, **kwargs)
        return Response(status=200, data=json)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def bulk_create(self, request, document_pk=None, part_pk=None):
        lines = request.data.get("lines")

        response_json = self._bulk_create_helper(lines)
        return Response({'status': 'ok', 'lines': response_json})

    def _bulk_create_helper(self, lines):
        # Performs the actual creation, called from two endpoints

        # We create the lines in two parts - first the lines, then their transcriptions.
        # We can't used the DetailedLineSerializer, since the Transcription serializer requires a line property,
        # which is unknown at this time - the line has not been created yet.
        # We may want to move this code into the DetailedLineSerializer's create method at some point.
        serializer = LineSerializer(data=lines, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Now we go over the lines retrieved from the request, take their transcriptions, and add the right line PK to each one.
        # serializer.data is ordered, in the same order as lines
        if len(lines) != len(serializer.data):
            raise ValueError(f"LineSerializer created {len(serializer.data)} lines, while {len(lines)} were expected")

        transcriptions = []
        line_pks = []
        for i in range(len(lines)):
            pk = serializer.data[i]['pk']
            line_transcriptions = lines[i].get('transcriptions', [])
            for lt in line_transcriptions:
                lt['line'] = pk
            transcriptions += line_transcriptions
            line_pks.append(pk)

        serializer = LineTranscriptionSerializer(data=transcriptions, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Finally, for a response, we want to create all the newly created lines along with their transcriptions.
        # Simplest way to do this - just use the PKs to load the lines again
        qs = Line.objects.filter(pk__in=line_pks)
        serializer = DetailedLineSerializer(qs, many=True)
        return serializer.data

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
        serializer = DetailedLineSerializer(qs, many=True)
        json = serializer.data
        qs.delete()
        return Response({'status': 'ok', 'lines': json}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def merge(self, request, document_pk=None, part_pk=None):
        original_lines = request.data.get("lines")
        if len(original_lines) > MAX_MERGE_SIZE:
            return Response(dict(status='error', error=f"Can't merge more than {MAX_MERGE_SIZE} lines"), status=status.HTTP_400_BAD_REQUEST)

        lines = list(Line.objects.filter(pk__in=original_lines))
        for line in lines:
            if not line.baseline:
                return Response(dict(status='error', error="Lines without a baseline cannot be merged"), status=status.HTTP_400_BAD_REQUEST)

        original_serializer = DetailedLineSerializer(lines, many=True)
        deleted_json = original_serializer.data

        merged_line_json = merge_lines(lines)
        created_json = self._bulk_create_helper([merged_line_json])
        for line in lines:
            line.delete()

        response_json = dict(created=created_json[0], deleted=deleted_json)
        return Response(dict(status='ok', lines=response_json), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def move(self, request, document_pk=None, part_pk=None, pk=None):
        data = request.data.get('lines')
        qs = Line.objects.filter(pk__in=[line['pk'] for line in data])
        serializer = LineOrderSerializer(qs, data=data, many=True)
        if serializer.is_valid():
            resp = serializer.save()
            return Response(resp, status=200)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LineTranscriptionViewSet(DocumentPermissionMixin, ModelViewSet):
    queryset = LineTranscription.objects.all()
    serializer_class = LineTranscriptionSerializer
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        qs = (super().get_queryset()
              .filter(line__document_part=self.kwargs['part_pk'])
              .filter(line__document_part__document=self.kwargs['document_pk'])
              .select_related('line', 'transcription')
              .order_by('line__order', 'id'))
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
                .filter(Q(owner=self.request.user)
                        | Q(ocr_model_rights__user=self.request.user)
                        | Q(ocr_model_rights__group__user=self.request.user)))

    @action(detail=True, methods=['post'])
    def cancel_training(self, request, pk=None):
        model = self.get_object()
        try:
            model.cancel_training()
        except Exception as e:
            logger.exception(e)
            return Response({'status': 'failed'}, status=400)
        return Response({'status': 'canceled'})


class RegenerableAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        if not created and request.data.get('regenerate'):
            token.delete()
            token, created = Token.objects.get_or_create(user=user)

        return Response({'token': token.key})
