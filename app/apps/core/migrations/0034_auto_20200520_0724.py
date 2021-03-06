# Generated by Django 2.1.4 on 2020-05-20 07:24

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models

import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_ocrmodel_job'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='box',
            field=django.contrib.postgres.fields.jsonb.JSONField(validators=[core.models.validate_polygon]),
        ),
        migrations.AlterField(
            model_name='block',
            name='typology',
            field=models.ForeignKey(blank=True, limit_choices_to={'target': 3}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.Typology'),
        ),
        migrations.AlterField(
            model_name='documentpart',
            name='workflow_state',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Created'), (1, 'Converting'), (2, 'Converted'), (5, 'Segmenting'), (6, 'Segmented'), (7, 'Transcribing')], default=0),
        ),
        migrations.AlterField(
            model_name='line',
            name='baseline',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, validators=[core.models.validate_polygon]),
        ),
        migrations.AlterField(
            model_name='line',
            name='block',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.Block'),
        ),
        migrations.AlterField(
            model_name='line',
            name='mask',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, validators=[core.models.validate_polygon]),
        ),
        migrations.AlterField(
            model_name='linetranscription',
            name='content',
            field=models.CharField(blank=True, default='', max_length=2048),
        ),
        migrations.AlterField(
            model_name='linetranscription',
            name='version_source',
            field=models.CharField(default='eScriptorium', editable=False, max_length=128),
        ),
        migrations.AlterField(
            model_name='ocrmodel',
            name='version_source',
            field=models.CharField(default='eScriptorium', editable=False, max_length=128),
        ),
    ]
