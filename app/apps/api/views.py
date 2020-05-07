import itertools
import logging

from django.db.models import Prefetch, Count

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination

from api.serializers import *
from core.models import *
from users.models import User
from imports.forms import ImportForm, ExportForm
from imports.parsers import ParseError
from versioning.models import NoChangeException
from users.consumers import send_event
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserOnboardingSerializer

    @action(detail=False, methods=['put'])
    def onboarding(self, request):
        serializer = UserOnboardingSerializer(data=request.data, user=self.request.user)
        if serializer.is_valid(raise_exception=True):
            serializer.complete()
            return Response(status=status.HTTP_200_OK)


class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.for_user(self.request.user)

    def form_error(self, msg):
        return Response({'status': 'error', 'error': msg}, status=400)

    @action(detail=True, methods=['post'])
    def imports(self, request, pk=None):
        document = self.get_object()
        form = ImportForm(document, request.user,
                          request.POST, request.FILES)
        if form.is_valid():
            form.save()  # create the import
            try:
                form.process()
            except ParseError as e:
                return self.form_error("Incorrectly formated file, couldn't parse it.")
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


class PartViewSet(ModelViewSet):
    queryset = DocumentPart.objects.all().select_related('document')

    def get_queryset(self):
        qs = self.queryset.filter(document=self.kwargs.get('document_pk'))
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
        part = DocumentPart.objects.get(document=document_pk, pk=pk)
        onlyParam = request.query_params.get("only")
        only = onlyParam and list(map(int, onlyParam.split(',')))

        try:
            part.make_masks(only=only)
        except Exception as e:
            logger.exception(e)
            return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)

        if only is None:
            qs = part.lines.all()
        else:
            qs = part.lines.filter(pk__in=only)
        serializer = LineSerializer(qs, many=True)
        return Response({'status': 'done', 'lines': serializer.data}, status=200)

    @action(detail=True, methods=['post'])
    def recalculate_ordering(self, request, document_pk=None, pk=None):
        document_part = DocumentPart.objects.get(pk=pk)
        document_part.recalculate_ordering()
        serializer = LineOrderSerializer(document_part.lines.all(), many=True)
        return Response({'status': 'done', 'lines': serializer.data}, status=200)


class BlockViewSet(ModelViewSet):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer

    def get_queryset(self):
        return Block.objects.filter(document_part=self.kwargs['part_pk'])


class LineViewSet(ModelViewSet):
    queryset = Line.objects.all().select_related('block').prefetch_related('transcriptions__transcription')
    serializer_class = DetailedLineSerializer

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return DetailedLineSerializer
        else:  # create
            return LineSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request, document_pk=None, part_pk=None):
        lines = request.data.get("lines")
        result = []
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
        return Response({'response': 'ok', 'lines': serializer.data}, status=200)

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request, document_pk=None, part_pk=None):
        deleted_lines = request.data.get("lines")
        qs = Line.objects.filter(pk__in=deleted_lines)
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100


class LineTranscriptionViewSet(ModelViewSet):
    queryset = LineTranscription.objects.all()
    serializer_class = LineTranscriptionSerializer
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        qs = (self.queryset.filter(line__document_part=self.kwargs['part_pk'])
                .select_related('line', 'transcription').order_by('line__order'))
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

    def update(self, request, document_pk=None, part_pk=None, pk=None):
        instance = self.get_object()
        try:
            instance.new_version(author=request.user.username,
                                 source=settings.VERSIONING_DEFAULT_SOURCE)
        except NoChangeException:
            # Note we can safely pass here
            pass
        else:
            instance.save()
        return super().update(request, document_pk=document_pk, part_pk=part_pk, pk=pk)

    def get_serializer_class(self):
        lines = Line.objects.filter(document_part=self.kwargs['part_pk'])
        class RuntimeSerializer(self.serializer_class):
            line = serializers.PrimaryKeyRelatedField(queryset=lines)
        return RuntimeSerializer
