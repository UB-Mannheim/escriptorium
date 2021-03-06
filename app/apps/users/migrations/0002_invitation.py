# Generated by Django 2.1.3 on 2018-11-21 10:20

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invitation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_first_name', models.CharField(blank=True, max_length=256, null=True)),
                ('recipient_last_name', models.CharField(blank=True, max_length=256, null=True)),
                ('recipient_email', models.EmailField(max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(editable=False, null=True)),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('workflow_state', models.SmallIntegerField(choices=[(0, 'Error'), (2, 'Sent'), (4, 'Received'), (8, 'Accepted')], default=1)),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.Group')),
                ('recipient', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invitations_received', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invitations_sent', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
