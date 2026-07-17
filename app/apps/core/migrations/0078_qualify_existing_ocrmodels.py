import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def qualify_existing_models(apps, schema_editor):
    from core.tasks import qualify_model

    OcrModel = apps.get_model('core', 'OcrModel')
    pks = OcrModel.objects.exclude(file='').exclude(file__isnull=True).values_list('pk', flat=True)
    for pk in pks:
        # don't fail the migration if the broker is unreachable
        try:
            qualify_model.delay(pk)
        except Exception as e:
            logger.warning("could not enqueue model qualification, skipping (%s)", e)
            break


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0077_ocrmodel_architecture'),
    ]

    operations = [
        migrations.RunPython(qualify_existing_models, migrations.RunPython.noop),
    ]
