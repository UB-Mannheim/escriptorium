# Generated by Django 2.2.23 on 2021-07-08 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskreport',
            name='method',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]
