import logging

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext as _

from celery import shared_task

from users.consumers import send_event
from imports.parsers import ParseError

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def document_import(task, import_pk, resume=True, task_id=None):
    DocumentImport = apps.get_model('imports', 'DocumentImport')

    imp = DocumentImport.objects.get(
        Q(workflow_state=DocumentImport.WORKFLOW_STATE_CREATED) |
        Q(workflow_state=DocumentImport.WORKFLOW_STATE_ERROR),
        pk=import_pk)
    
    try:
        imp.task_id = task.request.id
        
        send_event('document', imp.document.pk, "import:start", {
            "id": imp.document.pk
        })
        
        for obj in imp.process(resume=resume):
            send_event('document', imp.document.pk, "import:progress", {
                "id": imp.document.pk,
                "progress": imp.processed,
                "total": imp.total
            })
    except Exception as e:
        send_event('document', imp.document.pk, "import:fail", {
            "id": imp.document.pk,
            "reason": str(e)
        })
        logger.exception(e)
    else:
        send_event('document', imp.document.pk, "import:done", {
            "id": imp.document.pk
        })


@shared_task(bind=True)
def document_export(task, file_format, user_pk, document_pk, part_pks, transcription_pk):
    user = User.objects.get(pk=user_pk)
    document = Document.objects.get(pk=document_pk)
    #  parts = DocumentPart.objects.filter(document=self.document, pk__in=pks)
    transcripton = Transcription.objects.get(document=self.document, pk=transcription_pk)
    
    if file_format == self.TEXT_FORMAT:
        filename = "export_%s_%s_%s.txt" % (slugify(self.document.name).replace('-', '_'),
                                            file_format,
                                            datetime.now().strftime('%Y%m%d%H%M'))
        # content_type = 'text/plain'
        lines = (LineTranscription.objects
                 .filter(transcription=transcription, line__document_part__in=parts)
                 .exclude(content="")
                 .order_by('line__document_part', 'line__document_part__order', 'line__order'))
        # return StreamingHttpResponse(['%s\n' % line.content for line in lines],
        #                              content_type=content_type)
        with open(filepath, 'w') as fh:
            fh.writelines(['%s\n' % line.content for line in lines])

    
    elif file_format == self.ALTO_FORMAT or file_format == self.PAGEXML_FORMAT:
        filename = "export_%s_%s_%s.zip" % (slugify(self.document.name).replace('-', '_'),
                                            file_format,
                                            datetime.now().strftime('%Y%m%d%H%M'))
        #buff = io.BytesIO()
        if file_format == self.ALTO_FORMAT:
            tplt = loader.get_template('export/alto.xml')
        elif file_format == self.PAGEXML_FORMAT:
            tplt = loader.get_template('export/pagexml.xml')

        
        with ZipFile(filepath, 'w') as zip_:
            for part in parts:
                page = tplt.render({
                    'part': part,
                    'lines': part.lines.order_by('block__order', 'order')
                                       .prefetch_related(
                                           Prefetch('transcriptions',
                                                    to_attr='transcription',
                                                    queryset=LineTranscription.objects.filter(
                                                        transcription=transcription)))})
                zip_.writestr('%s.xml' % os.path.splitext(part.filename)[0], page)
        # response = HttpResponse(buff.getvalue(),content_type='application/x-zip-compressed')
        # response['Content-Disposition'] = 'attachment; filename=%s' % filename
        # TODO: add METS file
        # return response
    
    # TODO
    # send email
    # send websocket msg
