from datetime import datetime
import logging
import os.path
from zipfile import ZipFile

from django.apps import apps
from django.conf import settings
from django.db.models import Q, Prefetch
from django.template import loader
from django.utils.text import slugify

from celery import shared_task

from core.models import Line
from users.consumers import send_event
from escriptorium.utils import send_email


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
    ALTO_FORMAT = "alto"
    PAGEXML_FORMAT = "pagexml"
    TEXT_FORMAT = "text"

    User = apps.get_model('users', 'User')
    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')

    user = User.objects.get(pk=user_pk)
    document = Document.objects.get(pk=document_pk)

    send_event('document', document.pk, "export:start", {
        "id": document.pk
    })

    transcription = Transcription.objects.get(document=document, pk=transcription_pk)

    if file_format == TEXT_FORMAT:
        filename = "export_%s_%s_%s.txt" % (slugify(document.name).replace('-', '_'),
                                            file_format,
                                            datetime.now().strftime('%Y%m%d%H%M'))
        filepath = os.path.join(user.get_document_store_path(), filename)
        # content_type = 'text/plain'
        lines = (LineTranscription.objects
                 .filter(transcription=transcription, line__document_part__pk__in=part_pks)
                 .exclude(content="")
                 .order_by('line__document_part', 'line__document_part__order', 'line__order'))
        # return StreamingHttpResponse(['%s\n' % line.content for line in lines],
        #                              content_type=content_type)
        with open(filepath, 'w') as fh:
            fh.writelines(['%s\n' % line.content for line in lines])
        fh.close()

    elif file_format == ALTO_FORMAT or file_format == PAGEXML_FORMAT:
        filename = "export_%s_%s_%s.zip" % (slugify(document.name).replace('-', '_'),
                                            file_format,
                                            datetime.now().strftime('%Y%m%d%H%M'))
        filepath = os.path.join(user.get_document_store_path(), filename)
        # buff = io.BytesIO()
        if file_format == ALTO_FORMAT:
            tplt = loader.get_template('export/alto.xml')
        elif file_format == PAGEXML_FORMAT:
            tplt = loader.get_template('export/pagexml.xml')
        parts = DocumentPart.objects.filter(document=document, pk__in=part_pks)
        with ZipFile(filepath, 'w') as zip_:
            for part in parts:
                page = tplt.render({
                    'valid_block_types': document.valid_block_types.all(),
                    'valid_line_types': document.valid_line_types.all(),
                    'part': part,
                    'blocks': (part.blocks.order_by('order')
                                          .prefetch_related(
                                             Prefetch(
                                                 'lines',
                                                 queryset=Line.objects.prefetch_transcription(transcription)))),

                    'orphan_lines': (part.lines.prefetch_transcription(transcription)
                                               .filter(block=None))
                })
                zip_.writestr('%s.xml' % os.path.splitext(part.filename)[0], page)
        zip_.close()

    # send websocket msg
    rel_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
    user.notify('Export ready!', level='success', link={'text': 'Download', 'src': rel_path})

    send_event('document', document.pk, "export:done", {
        "id": document.pk
    })

    # send email
    from django.contrib.sites.models import Site
    send_email('export/email/ready_subject.txt',
               'export/email/ready_message.txt',
               'export/email/ready_html.html',
               user.email,
               context={'domain': Site.objects.get_current().domain,
                        'export_uri': rel_path})
