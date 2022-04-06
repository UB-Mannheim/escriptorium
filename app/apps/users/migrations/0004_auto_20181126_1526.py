import os

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_auto_20181121_1708'),
    ]

    def generate_superuser(apps, schema_editor):
        User = apps.get_model('users', 'User')
        DJANGO_SU_NAME = os.environ.get('DJANGO_SU_NAME', 'admin')
        DJANGO_SU_EMAIL = os.environ.get('DJANGO_SU_EMAIL', 'admin@admin.com')
        DJANGO_SU_PASSWORD = os.environ.get('DJANGO_SU_PASSWORD', 'admin')
        superuser = User.objects.create(
            username=DJANGO_SU_NAME,
            email=DJANGO_SU_EMAIL,
            is_staff=True,
            is_superuser=True)
        from django.contrib.auth.hashers import make_password
        superuser.password = make_password(DJANGO_SU_PASSWORD)
        superuser.save()

    def delete_admin(apps, schema_editor):
        User = apps.get_model('users', 'User')
        User.objects.get(username='admin').delete()

    operations = [
        migrations.RunPython(generate_superuser, delete_admin),
    ]
