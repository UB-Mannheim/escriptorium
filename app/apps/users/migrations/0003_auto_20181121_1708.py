# Generated by Django 2.1.3 on 2018-11-21 17:08

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_invitation'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invitation',
            options={'ordering': ('-created_at',)},
        ),
        migrations.AlterField(
            model_name='invitation',
            name='recipient',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invitations_received', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='sender',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='invitations_sent', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='workflow_state',
            field=models.SmallIntegerField(choices=[(0, 'Error'), (1, 'Created'), (2, 'Sent'), (4, 'Received'), (8, 'Accepted')], default=1, editable=False),
        ),
    ]
