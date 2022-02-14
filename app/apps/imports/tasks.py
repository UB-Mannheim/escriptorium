import logging
import os.path

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext as _

from celery import shared_task

from users.consumers import send_event
from escriptorium.utils import send_email
from imports.export import EXPORTER_CLASS
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
    User = apps.get_model('users', 'User')
    Document = apps.get_model('core', 'Document')
    Transcription = apps.get_model('core', 'Transcription')
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

        if file_format not in EXPORTER_CLASS:
            raise NotImplementedError(f"File format {file_format} isn't a supported format during a data export")

        transcription = Transcription.objects.get(document=document, pk=transcription_pk)
        exporter = EXPORTER_CLASS[file_format](
            part_pks, region_types, include_images, user, document, report, transcription
        )
        exporter.render()
    except Exception as e:
        report.error(str(e))

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
    else:
        report.end()

        rel_path = os.path.relpath(exporter.filepath, settings.MEDIA_ROOT)
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
