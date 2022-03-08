# Generated by Django 2.1.4 on 2019-01-28 09:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20190128_0940'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='documentprocesssettings',
            name='ocrmodel',
        ),
        migrations.AddField(
            model_name='documentprocesssettings',
            name='ocr_model',
            field=models.ForeignKey(blank=True, limit_choices_to={'trained': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settings_ocr', to='core.OcrModel', verbose_name='Model'),
        ),
        migrations.AddField(
            model_name='documentprocesssettings',
            name='train_model',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settings_train', to='core.OcrModel', verbose_name='Model'),
        ),
    ]
