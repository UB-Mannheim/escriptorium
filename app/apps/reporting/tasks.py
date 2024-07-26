import logging

from celery import states
from celery.signals import before_task_publish, task_postrun, task_prerun
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model

from users.consumers import send_event

logger = logging.getLogger(__name__)


def update_client_state(task_kwargs, task_name, status, task_id=None, data=None):
    part_pks = []
    if task_kwargs.get("instance_pk"):
        part_pks = [task_kwargs["instance_pk"]]
    elif task_kwargs.get("part_pks"):
        part_pks = task_kwargs["part_pks"]

    DocumentPart = apps.get_model('core', 'DocumentPart')

    for part_pk in part_pks:
        part = DocumentPart.objects.get(pk=part_pk)
        send_event('document', part.document.pk, "part:workflow", {
            "id": part.pk,
            "process": task_name.split('.')[-1],
            "status": status,
            "task_id": task_id,
            "data": data or {}
        })


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
    OcrModel = apps.get_model('core', 'OcrModel')
    TaskReport = apps.get_model('reporting', 'TaskReport')
    TaskGroup = apps.get_model('reporting', 'TaskGroup')

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
    model = None
    if task_kwargs.get("model_pk"):
        try:
            model = OcrModel.objects.get(pk=task_kwargs["model_pk"])
        except OcrModel.DoesNotExist:
            pass

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

    task_group = None
    if task_kwargs.get("task_group_pk"):
        task_group = TaskGroup.objects.get(pk=task_kwargs.get("task_group_pk"))

    # Update the frontend display consequently
    update_client_state(task_kwargs, sender, "pending")

    # TODO: Define an explicit "report_label" kwarg on all tasks
    default_report_label = f"Report for celery task {task_id} of type {sender}"
    TaskReport.objects.create(
        user=user,
        group=task_group,
        label=task_kwargs.get("report_label", default_report_label),
        document=document,
        document_part=part,
        ocr_model=model,
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

    # Update the frontend display consequently
    update_client_state(kwargs.get("kwargs", {}), task.name, "ongoing", task_id=task_id)


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
    from reporting.models import TASK_FINAL_STATES

    if report.workflow_state not in TASK_FINAL_STATES:
        if kwargs.get("state") == states.SUCCESS:
            report.end()
        else:
            report.error(str(kwargs.get("retval")))

    # Update the frontend display consequently
    client_status_mapping = {
        TaskReport.WORKFLOW_STATE_ERROR: 'error',
        TaskReport.WORKFLOW_STATE_DONE: 'done'
    }

    if report.workflow_state in client_status_mapping:
        update_client_state(kwargs.get("kwargs", {}), task.name, client_status_mapping[report.workflow_state], task_id=task_id, data=kwargs.get('result'))

    report.calc_cpu_cost()
    # Listing tasks parametrized to run on 'gpu' Celery queue
    if task.name in [route for route, queue in settings.CELERY_TASK_ROUTES.items() if queue == {'queue': 'gpu'}]:
        report.calc_gpu_cost()
