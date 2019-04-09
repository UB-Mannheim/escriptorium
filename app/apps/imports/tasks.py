from django.apps import apps

from celery import shared_task

from imports.parsers import AltoParser
from users.consumers import send_event


@shared_task
def xml_import(import_pk, resume=True):
    Import = apps.get_model('imports', 'Import')
    imp = Import.objects.get(pk=import_pk)  # let it fail
    send_event('document', imp.document.pk, "import:start", {
        "id": imp.document.pk
    })
    
    try:
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
        raise
    
    send_event('document', imp.document.pk, "import:done", {
        "id": imp.document.pk
    })


@shared_task
def iiif_import(import_pk):
    pass
