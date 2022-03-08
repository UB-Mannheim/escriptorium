import os

from django.db import migrations


def change_mydomain_name(apps, schema_editor):
    DOMAIN_NAME = os.getenv('DOMAIN', 'localhost')
    SITE_NAME = os.getenv('SITE_NAME', 'escriptorium')
    Site = apps.get_model('sites', 'Site')
    site = Site.objects.first()
    if site:
        site.name = SITE_NAME
        site.domain = DOMAIN_NAME
        site.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20210324_1007'),
    ]

    operations = [
        migrations.RunPython(change_mydomain_name, migrations.RunPython.noop),
    ]
