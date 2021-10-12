from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_ocrmodel_file_size'),
    ]

    operations = [
        TrigramExtension()
    ]
