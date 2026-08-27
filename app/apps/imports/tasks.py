import logging
import os.path
from datetime import timedelta

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from escriptorium.utils import send_email
from imports.export import ENABLED_EXPORTERS
from reporting.models import Download

# DO NOT REMOVE THIS IMPORT, it will break celery tasks located in this file
from reporting.tasks import create_task_reporting  # noqa F401
from users.consumers import send_event

logger = logging.getLogger(__name__)


def _register_download(user, report, filepath, label):
    """Create a reporting.Download row for a freshly produced export file.

    Isolated in a helper so the render-else branch stays legible and future
    exporters (not just JSON/ZIP archives) can share the same registration.
    Failures are logged and swallowed -- the export itself already succeeded,
    a missing Download row is a UX regression, not a data-loss bug.
    """
    try:
        stat = os.stat(filepath)
    except OSError:
        logger.warning("Cannot stat export file %s; skipping Download row.", filepath)
        return None

    if filepath.endswith(".tar.gz"):
        mime = "application/gzip"
    elif filepath.endswith(".zip"):
        mime = "application/zip"
    elif filepath.endswith(".json"):
        mime = "application/json"
    else:
        mime = "application/octet-stream"

    retention_days = getattr(user, "download_retention_days", 30) or 0
    expires_at = None
    if retention_days > 0:
        expires_at = django_timezone.now() + timedelta(days=retention_days)

    try:
        return Download.objects.create(
            user=user,
            task_report=report,
            label=label or os.path.basename(filepath),
            file_path=filepath,
            file_size=stat.st_size,
            mime_type=mime,
            expires_at=expires_at,
        )
    except Exception:
        logger.exception("Failed to register Download for %s", filepath)
        return None


@shared_task(bind=True)
def document_import(task, document_pk=None, import_pk=None,
                    resume=True, task_id=None, user_pk=None,
                    task_group_pk=None, report_label=None, **kwargs):
    DocumentImport = apps.get_model('imports', 'DocumentImport')
    TaskReport = apps.get_model('reporting', 'TaskReport')
    User = apps.get_model('users', 'User')

    user = User.objects.get(pk=user_pk)
    # If quotas are enforced, assert that the user still has free CPU minutes and disk storage
    if not settings.DISABLE_QUOTAS:
        if user.cpu_minutes_limit() is not None:
            assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"
        if user.disk_storage_limit() is not None:
            assert user.has_free_disk_storage(), f"User {user.id} doesn't have any disk storage left"

    imp = DocumentImport.objects.get(
        Q(workflow_state=DocumentImport.WORKFLOW_STATE_CREATED)
        | Q(workflow_state=DocumentImport.WORKFLOW_STATE_ERROR),
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
                    transcription_pk, region_types, document_pk=None,
                    include_images=False, include_characters=False,
                    user_pk=None, report_label=None, task_group_pk=None, **kwargs):
    User = apps.get_model('users', 'User')
    Document = apps.get_model('core', 'Document')
    Transcription = apps.get_model('core', 'Transcription')
    TaskReport = apps.get_model('reporting', 'TaskReport')

    user = User.objects.get(pk=user_pk)

    # If quotas are enforced, assert that the user still has free CPU minutes
    if not settings.DISABLE_QUOTAS and user.cpu_minutes_limit() is not None:
        assert user.has_free_cpu_minutes(), f"User {user.id} doesn't have any CPU minutes left"

    document = Document.objects.get(pk=document_pk)
    try:
        report = TaskReport.objects.get(task_id=task.request.id)
    except TaskReport.MultipleObjectsReturned:
        report = TaskReport.objects.filter(task_id=task.request.id).order_by('-started_at').first()
    except TaskReport.DoesNotExist:
        report = None

    try:
        send_event('document', document.pk, "export:start", {
            "id": document.pk
        })

        if file_format not in ENABLED_EXPORTERS:
            raise NotImplementedError(f"File format {file_format} isn't a supported format during a data export")

        transcription = Transcription.objects.get(document=document, pk=transcription_pk)
        exporter = ENABLED_EXPORTERS[file_format]["class"](
            part_pks=part_pks,
            region_types=region_types,
            include_images=include_images,
            include_characters=include_characters,
            include_metadata=kwargs.get("include_metadata", False),
            include_models=kwargs.get("include_models", False),
            include_graph=kwargs.get("include_graph", False),
            include_annotations=kwargs.get("include_annotations", False),
            include_comments=kwargs.get("include_comments", False),
            all_transcriptions=kwargs.get("all_transcriptions", False),
            anonymize=kwargs.get("anonymize", False),
            archive_format=kwargs.get("archive_format", "zip"),
            user=user,
            document=document,
            report=report,
            transcription=transcription,
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

        # Register the produced file as a Download so it shows up in
        # /downloads/ and expires per the user's retention preference.
        _register_download(user=user,
                           report=report,
                           filepath=exporter.filepath,
                           label=report.label if report else exporter.filepath)

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
