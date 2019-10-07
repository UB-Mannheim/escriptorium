import itertools

from django.db.models import Prefetch, Count

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination

from api.serializers import *
from core.models import *
from imports.forms import ImportForm, ExportForm
from imports.parsers import ParseError
from users.consumers import send_event


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
        current_import = document.import_set.order_by('started_on').last()
        if current_import.is_cancelable():
            current_import.cancel()
            return Response({'status': 'canceled'})
        else:
            return Response({'status': 'already canceled'}, status=400)
    
    @action(detail=True, methods=['post'])
    def cancel_training(self, request, pk=None):
        document = self.get_object()
        model = document.ocr_models.filter(training=True).last()
        model.cancel_training()
        return Response({'status': 'canceled'})
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        document = self.get_object()
        form = ExportForm(document, request.POST)
        if form.is_valid():
            return form.stream()
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
    
    @action(detail=True, methods=['post'])
    def reset_mask(self, request, document_pk=None, part_pk=None, pk=None):
        line = Line.objects.get(document_part=part_pk, pk=pk)
        line.make_mask()
        return Response({'status': 'done', 'mask': line.mask})


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
    
    def get_serializer_class(self):
        lines = Line.objects.filter(document_part=self.kwargs['part_pk'])
        class RuntimeSerializer(self.serializer_class):
            line = serializers.PrimaryKeyRelatedField(queryset=lines)
        return RuntimeSerializer
    
    @action(detail=True, methods=['post'])
    def new_version(self, request, document_pk=None, part_pk=None, pk=None):
        lt = self.get_object()
        lt.new_version()
        lt.save()
        return Response(lt.versions[0], status=status.HTTP_201_CREATED)
