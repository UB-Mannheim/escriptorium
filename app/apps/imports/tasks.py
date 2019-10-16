import logging

from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext as _

from celery import shared_task

from users.consumers import send_event
from imports.parsers import ParseError

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def document_import(task, import_pk, resume=True, task_id=None):
    DocumentImport = apps.get_model('imports', 'DocumentImport')
    
    try:
        imp = DocumentImport.objects.get(pk=import_pk)
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
