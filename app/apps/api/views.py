import itertools

from django.db.models import Prefetch, Count
from django.http import StreamingHttpResponse
from django.template import loader
from django.utils.text import slugify

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination

from api.serializers import *
from core.models import *
from imports.forms import ImportForm
from imports.parsers import ParseError
from users.consumers import send_event


class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    paginate_by = 10
    
    def get_queryset(self):
        return Document.objects.for_user(self.request.user)
    
    @action(detail=True, methods=['post'])
    def imports(self, request, pk=None):
        def error(msg):
            return Response({'status': 'error', 'error': msg}, status=400)
        
        document = self.get_object()
        form = ImportForm(document, request.user,
                          request.POST, request.FILES)
        if form.is_valid():
            form.save()  # create the import
            try:
                form.process()
            except ParseError as e:
                return error("Incorrectly formated file, couldn't parse it.")
            return Response({'status': 'ok'})
        else:
            return error(json.dumps(form.errors))

    @action(detail=True, methods=['post'])
    def cancel_import(self, request, pk=None):
        document = self.get_object()
        current_import = document.import_set.order_by('started_on').last()
        if current_import.is_cancelable():
            current_import.cancel()
            return Response({'status': 'canceled'})
        else:
            return Response({'status': 'already canceled'}, status=400)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):            
        format_ = request.GET.get('as', 'text')
        try:
            transcription = Transcription.objects.get(
                document=pk, pk=request.GET.get('transcription'))
        except Transcription.DoesNotExist:
            return Response({'error': "Object 'transcription' is required."}, status=status.HTTP_400_BAD_REQUEST)
        self.object = self.get_object()
        
        if format_ == 'text':
            template = 'core/export/simple.txt'
            content_type = 'text/plain'
            extension = 'txt'
            lines = (LineTranscription.objects.filter(transcription=transcription)
                     .order_by('line__document_part', 'line__document_part__order', 'line__order'))
            response = StreamingHttpResponse(['%s\n' % line.content for line in lines],
                                             content_type=content_type)
        elif format_ == 'alto':
            template = 'core/export/alto.xml'
            content_type = 'text/xml'
            extension = 'xml'
            document = self.get_object()
            part_pks = document.parts.values_list('pk', flat=True)
            start = loader.get_template('core/export/alto_start.xml').render()
            end = loader.get_template('core/export/alto_end.xml').render()
            part_tmpl = loader.get_template('core/export/alto_part.xml')
            response = StreamingHttpResponse(itertools.chain([start],
                                                             [part_tmpl.render({
                                                                 'part': self.get_part_data(pk, transcription),
                                                                 'counter': i})
                                                              for i, pk in enumerate(part_pks)],
                                                             [end]),
                                             content_type=content_type)
        else:
            return Response({'error': 'Invalid format.'}, status=status.HTTP_400_BAD_REQUEST)
        
        response['Content-Disposition'] = 'attachment; filename="export_%s_%s.%s"' % (
            slugify(self.object.name), datetime.now().isoformat()[:16].replace('-', '_'), extension)
        return response
    
    def get_part_data(self, part_pk, transcription):
        return (DocumentPart.objects
                .prefetch_related(
                    Prefetch('blocks',
                             to_attr='orphan_blocks',
                             queryset=(Block.objects.annotate(num_lines=Count("line"))
                                       .filter(num_lines=0))),
                    Prefetch('lines',
                             queryset=(Line.objects.all()
                                       .select_related('block')
                                       .prefetch_related(
                                           Prefetch('transcriptions',
                                          to_attr='transcription',
                                          queryset=LineTranscription.objects.filter(transcription=transcription))))))
                .get(pk=part_pk))


class PartViewSet(ModelViewSet):
    queryset = DocumentPart.objects.all().select_related('document')
    paginate_by = 50
    
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
