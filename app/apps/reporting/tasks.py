import logging
import os

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model

from celery import states
from celery.signals import before_task_publish, task_prerun, task_postrun

logger = logging.getLogger(__name__)


@before_task_publish.connect
def create_task_reporting(sender, body, **kwargs):
    task_id = kwargs['headers']['id']
    task_kwargs = body[1]

    # If the reporting is disabled for this task we don't need to execute following code
    if sender in settings.REPORTING_TASKS_BLACKLIST:
        return

    User = get_user_model()
    DocumentImport = apps.get_model('imports', 'DocumentImport')
    Document = apps.get_model('core', 'Document')
    DocumentPart = apps.get_model('core', 'DocumentPart')
    TaskReport = apps.get_model('reporting', 'TaskReport')

    if task_kwargs.get("user_pk"):
        try:
            user = User.objects.get(pk=task_kwargs["user_pk"])
        except User.DoesNotExist:
            user = None
    else:
        user = None

    if not user:
        logger.error(f"Couldn't create a TaskReport object associated with celery task {task_id}, user attribute is mandatory")
        return

    document = None
    part = None
    if task_kwargs.get("document_pk"):
        try:
            document = Document.objects.get(pk=task_kwargs["document_pk"])
        except Document.DoesNotExist:
            pass
    elif task_kwargs.get("instance_pk"):
        try:
            part = DocumentPart.objects.get(pk=task_kwargs["instance_pk"])
            document = part.document
        except DocumentPart.DoesNotExist:
            pass
    elif task_kwargs.get("import_pk"):
        try:
            document_import = DocumentImport.objects.get(pk=task_kwargs["import_pk"])
            document = document_import.document
        except DocumentImport.DoesNotExist:
            pass
    elif task_kwargs.get("part_pks"):
        # They should all belong to the same document
        first_part = (DocumentPart.objects
                      .prefetch_related('document')
                      .get(pk=task_kwargs["part_pks"][0]))
        document = first_part.document

    # TODO: Define an explicit "report_label" kwarg on all tasks
    default_report_label = f"Report for celery task {task_id} of type {sender}"
    TaskReport.objects.create(
        user=user,
        label=task_kwargs.get("report_label", default_report_label),
        document=document,
        document_part=part,
        task_id=task_id,
        method=sender
    )


@task_prerun.connect
def start_task_reporting(task_id, task, *args, **kwargs):
    # If the reporting is disabled for this task we don't need to execute following code
    if task.name in settings.REPORTING_TASKS_BLACKLIST:
        return

    TaskReport = apps.get_model('reporting', 'TaskReport')

    try:
        report = TaskReport.objects.get(task_id=task_id)
    except TaskReport.DoesNotExist:
        logger.error(f"Couldn't retrieve any TaskReport object associated with celery task {task_id}")
        return

    report.start()


@task_postrun.connect
def end_task_reporting(task_id, task, *args, **kwargs):
    # If the reporting is disabled for this task we don't need to execute following code
    if task.name in settings.REPORTING_TASKS_BLACKLIST:
        return

    TaskReport = apps.get_model('reporting', 'TaskReport')

    try:
        report = TaskReport.objects.get(task_id=task_id)
    except TaskReport.DoesNotExist:
        logger.warning(f"Couldn't retrieve any TaskReport object associated with celery task {task_id}")
        return

    # Checking if the report wasn't already ended by tasks like "document_export" or "document_import"
    # or canceled by the Document.cancel_tasks API endpoint
    if (
        report.workflow_state != report.WORKFLOW_STATE_ERROR and
        report.workflow_state != report.WORKFLOW_STATE_DONE and
        report.workflow_state != report.WORKFLOW_STATE_CANCELED
    ):
        if kwargs.get("state") == states.SUCCESS:
            report.end()
        else:
            report.error(str(kwargs.get("retval")))

    report.calc_cpu_cost(os.cpu_count())
    # Listing tasks parametrized to run on 'gpu' Celery queue
    if task.name in [route for route, queue in settings.CELERY_TASK_ROUTES.items() if queue == {'queue': 'gpu'}]:
        report.calc_gpu_cost()
