# Generated by Django 2.1.4 on 2020-10-09 10:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0001_initial'),
        ('imports', '0010_auto_20191015_0917'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='documentimport',
            name='task_id',
        ),
        migrations.AddField(
            model_name='documentimport',
            name='report',
            field=models.ForeignKey(blank=True, max_length=64, null=True, on_delete=django.db.models.deletion.CASCADE, to='reporting.TaskReport'),
        ),
    ]
