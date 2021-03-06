# Generated by Django 2.2.23 on 2022-01-11 11:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0056_auto_20211008_1250'),
        ('reporting', '0005_taskreport_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskreport',
            name='document_part',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='core.DocumentPart'),
        ),
        migrations.AlterField(
            model_name='taskreport',
            name='workflow_state',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Queued'), (1, 'Running'), (2, 'Crashed'), (3, 'Finished'), (4, 'Canceled')], default=0),
        ),
    ]
