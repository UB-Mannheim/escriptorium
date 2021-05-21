# Generated by Django 2.2.20 on 2021-05-10 13:06
import time

from django.db import migrations
from django.template.defaultfilters import slugify


def make_slug(proj, Project):
    # models in migrations don't have access to models methods ;(
    slug = slugify(proj.name)
    # check unicity
    exists = Project.objects.filter(slug=slug).count()
    if not exists:
        proj.slug = slug
    else:
        proj.slug = slug[:40] + hex(int(time.time()))[2:]

    proj.save()


def forwards(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Project = apps.get_model('core', 'Project')
    Document = apps.get_model('core', 'Document')
    # create user projects
    for user in User.objects.all():
        proj, created = Project.objects.get_or_create(name=user.username+"'s Project",
                                                      owner=user)
        if not proj.slug:
            make_slug(proj, Project)
        # move documents into projects
        user.document_set.update(project=proj)
        # move share from docs to created projects
        for doc in user.document_set.all():
            for share in doc.shared_with_users.all():
                proj.shared_with_users.add(share)
            for share in doc.shared_with_groups.all():
                proj.shared_with_groups.add(share)

        # shared to draft
        user.document_set.filter(workflow_state=1).update(workflow_state=0)

    # deal with documents without owner (shouldn't be any but let's be safe)
    # move them to admin's
    user = User.objects.filter(is_superuser=True).first()
    proj, dummy = Project.objects.get_or_create(name=user.username+"'s Project",
                                                owner=user)
    if not proj.slug:
        make_slug(proj, Project)
    for doc in Document.objects.filter(owner=None):
        doc.project = proj
        doc.save()
        # move share from docs to created projects
        for doc in user.document_set.all():
            for share in doc.shared_with_users.all():
                proj.shared_with_users.add(share)
            for share in doc.shared_with_groups.all():
                proj.shared_with_groups.add(share)


def backwards(apps, schema_editor):
    Document = apps.get_model('core', 'Document')
    for doc in Document.objects.all():
        if doc.project:
            for share in doc.project.shared_with_users.all():
                doc.shared_with_users.add(share)
            for share in doc.project.shared_with_groups.all():
                doc.shared_with_groups.add(share)

    Document.objects.update(project=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0046_auto_20210521_1444'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
