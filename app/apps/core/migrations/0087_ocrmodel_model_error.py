# Generated for the OcrModel.model_error field added alongside the
# qualify_model load verification.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0086_seed_default_ontology'),
    ]

    operations = [
        migrations.AddField(
            model_name='ocrmodel',
            name='model_error',
            field=models.TextField(blank=True, null=True),
        ),
    ]
