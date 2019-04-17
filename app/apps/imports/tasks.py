from django.apps import apps

from celery import shared_task

from imports.parsers import AltoParser
from users.consumers import send_event


@shared_task(bind=True)
def document_import(task, import_pk, resume=True, task_id=None):
    Import = apps.get_model('imports', 'Import')
    imp = Import.objects.get(pk=import_pk)  # let it fail    
    imp.task_id = task.request.id
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
        imp.workflow_state = imp.WORKFLOW_STATE_ERROR
        imp.save()
        send_event('document', imp.document.pk, "import:fail", {
            "id": imp.document.pk,
            "reason": str(e)
        })
        raise
    else:
        send_event('document', imp.document.pk, "import:done", {
            "id": imp.document.pk
        })
