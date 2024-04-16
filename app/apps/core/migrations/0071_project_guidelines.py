# Generated by Django 4.0.10 on 2023-06-08 15:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0070_alter_annotationcomponent_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='guidelines',
            field=models.URLField(blank=True, help_text='An optional URL pointing to an external document that explains content editing and authorship guidelines for this project, in order to guide a team or group towards consistent practices for manual segmentation/transcription.', null=True),
        ),
    ]