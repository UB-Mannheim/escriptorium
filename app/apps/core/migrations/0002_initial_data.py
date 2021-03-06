# Generated by Django 2.1.4 on 2018-12-17 10:58
import subprocess

from django.db import migrations


def initial_data(apps, schema_editor):
    TARGET_DOCUMENT = 1  # Note: not dry because get_model only get fields not consts
    TARGET_PART = 2
    Typology = apps.get_model('core', 'Typology')
    Typology.objects.create(name='Manuscript', target=TARGET_DOCUMENT)
    Typology.objects.create(name='Page', target=TARGET_PART)
    Typology.objects.create(name='Cover', target=TARGET_PART)

    # fetching kraken default models
    OcrModel = apps.get_model('core', 'OcrModel')
    try:
        subprocess.check_call(["kraken", "get", "default"])
    except Exception:
        pass
    else:
        # TODO: ask for ben@kraken to give a higher level function that returns the name of the model
        OcrModel.objects.create(name='default', file='en-default.pronn')


def backward(apps, schema_editor):
    Typology = apps.get_model('core', 'Typology')
    OcrModel = apps.get_model('core', 'OcrModel')
    Typology.objects.all().delete()
    OcrModel.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(initial_data, backward),
    ]
