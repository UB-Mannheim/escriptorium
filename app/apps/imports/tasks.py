from datetime import datetime
import logging
import os.path
from zipfile import ZipFile

from django.apps import apps
from django.conf import settings
from django.db.models import Q, Prefetch, Avg
from django.template import loader
from django.utils.text import slugify
from django.utils.translation import gettext as _

from celery import shared_task

from core.models import Line
from users.consumers import send_event
from escriptorium.utils import send_email
from reporting.tasks import create_task_reporting


logger = logging.getLogger(__name__)


@shared_task(bind=True)
def document_import(task, import_pk=None, resume=True, task_id=None, user_pk=None, report_label=None):
    DocumentImport = apps.get_model('imports', 'DocumentImport')
    TaskReport = apps.get_model('reporting', 'TaskReport')
    User = apps.get_model('users', 'User')

    user = User.objects.get(pk=user_pk)
    # If quotas are enforced, assert that the user still has free CPU minutes and disk storage
    if not settings.DISABLE_QUOTAS:
        if user.cpu_minutes_limit() != None:
            assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        if user.disk_storage_limit() != None:
            assert user.has_free_disk_storage(), f"User {user.id} doesn't have any disk storage left"

    imp = DocumentImport.objects.get(
        Q(workflow_state=DocumentImport.WORKFLOW_STATE_CREATED) |
        Q(workflow_state=DocumentImport.WORKFLOW_STATE_ERROR),
        pk=import_pk)

    imp.report = TaskReport.objects.get(task_id=task.request.id)
    imp.save()

    try:
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
        if user:
            user.notify(_("Something went wrong during the import!"),
                        links=[{'text': 'Report', 'src': imp.report.uri}],
                        id="import-error", level='danger')

        send_event('document', imp.document.pk, "import:error", {
            "id": imp.document.pk,
            "reason": str(e)
        })
        logger.exception(e)
        imp.report.error(str(e))
    else:
        if user:
            if imp.report.messages:
                user.notify(_("Import finished with warnings!"),
                            links=[{'text': _('Details'), 'src': imp.report.uri}],
                            level='warning')
            else:
                user.notify(_("Import done!"), level='success')
        send_event('document', imp.document.pk, "import:done", {"id": imp.document.pk})
        imp.report.end()


@shared_task(bind=True)
def document_export(task, file_format, part_pks,
                    transcription_pk, region_types, document_pk=None, include_images=False,
                    user_pk=None, report_label=None):
    ALTO_FORMAT = "alto"
    PAGEXML_FORMAT = "pagexml"
    TEXT_FORMAT = "text"

    User = apps.get_model('users', 'User')
    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    Transcription = apps.get_model('core', 'Transcription')
    LineTranscription = apps.get_model('core', 'LineTranscription')
    TaskReport = apps.get_model('reporting', 'TaskReport')

    user = User.objects.get(pk=user_pk)

    # If quotas are enforced, assert that the user still has free CPU minutes
    if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() != None:
        assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"

    document = Document.objects.get(pk=document_pk)
    report = TaskReport.objects.get(task_id=task.request.id)

    try:
        send_event('document', document.pk, "export:start", {
            "id": document.pk
        })

        # Check if we have to include orphan lines
        include_orphans = False
        if 'Orphan' in region_types:
            include_orphans = True
            region_types.remove('Orphan')

        # Check if we have to include lines with an undefined region type
        include_undefined = False
        if 'Undefined' in region_types:
            include_undefined = True
            region_types.remove('Undefined')

        transcription = Transcription.objects.get(document=document, pk=transcription_pk)

        base_filename = "export_doc%d_%s_%s_%s" % (
            document.pk,
            slugify(document.name).replace('-', '_')[:32],
            file_format,
            datetime.now().strftime('%Y%m%d%H%M'))

        if file_format == TEXT_FORMAT:
            filename = "%s.txt" % base_filename
            filepath = os.path.join(user.get_document_store_path(), filename)
            # content_type = 'text/plain'

            region_filters = Q(line__block__typology_id__in=region_types)
            if include_orphans:
                region_filters |= Q(line__block__isnull=True)
            if include_undefined:
                region_filters |= Q(line__block__isnull=False, line__block__typology_id__isnull=True)

            lines = (LineTranscription.objects
                     .filter(transcription=transcription, line__document_part__pk__in=part_pks)
                     .filter(region_filters)
                     .exclude(content="")
                     .order_by('line__document_part', 'line__document_part__order', 'line__order'))
            # return StreamingHttpResponse(['%s\n' % line.content for line in lines],
            #                              content_type=content_type)
            with open(filepath, 'w') as fh:
                fh.writelines(['%s\n' % line.content for line in lines])
                fh.close()

        elif file_format == ALTO_FORMAT or file_format == PAGEXML_FORMAT:
            filename = "%s.zip" % base_filename
            filepath = os.path.join(user.get_document_store_path(), filename)
            # buff = io.BytesIO()
            if file_format == ALTO_FORMAT:
                tplt = loader.get_template('export/alto.xml')
            elif file_format == PAGEXML_FORMAT:
                tplt = loader.get_template('export/pagexml.xml')
            parts = DocumentPart.objects.filter(document=document, pk__in=part_pks)

            region_filters = Q(typology_id__in=region_types)
            if include_undefined:
                region_filters |= Q(typology_id__isnull=True)

            with ZipFile(filepath, 'w') as zip_:
                for part in parts:
                    render_orphans = {} if not include_orphans else {
                        'orphan_lines': part.lines.prefetch_transcription(transcription).filter(block=None)
                    }

                    if include_images:
                        # Note adds image before the xml file
                        zip_.write(part.image.path, part.filename)
                    try:
                        page = tplt.render({
                            'valid_block_types': document.valid_block_types.all(),
                            'valid_line_types': document.valid_line_types.all(),
                            'part': part,
                            'blocks': (part.blocks.filter(region_filters)
                                       .annotate(avglo=Avg('lines__order'))
                                       .order_by('avglo')
                                       .prefetch_related(
                                           Prefetch(
                                               'lines',
                                               queryset=Line.objects.prefetch_transcription(
                                                   transcription)))),
                            **render_orphans
                        })
                    except Exception as e:
                        report.append("Skipped {element}({image}) because '{reason}'.".format(
                            element=part.name, image=part.filename, reason=str(e)
                        ))
                    else:
                        zip_.writestr('%s.xml' % os.path.splitext(part.filename)[0], page)

                zip_.close()

    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the export!"),
                        links=[{'text': 'Report', 'src': report.uri}],
                        id="export-error",
                        level='danger')

        send_event('document', document.pk, "import:error", {
            "id": document.pk,
            "reason": str(e)
        })
        logger.exception(e)
        report.error(str(e))

    else:
        rel_path = os.path.relpath(filepath, settings.MEDIA_ROOT)
        report.end()

        user.notify(_('Export done!'),
                    level='success',
                    links=[{'text': _('Download'),
                            'src': settings.MEDIA_URL + rel_path}])

        # send websocket msg
        send_event('document', document.pk, "export:done", {
            "id": document.pk
        })

        # send email
        from django.contrib.sites.models import Site
        send_email('export/email/ready_subject.txt',
                   'export/email/ready_message.txt',
                   'export/email/ready_html.html',
                   (user.email,),
                   context={'domain': Site.objects.get_current().domain,
                            'export_uri': rel_path})
