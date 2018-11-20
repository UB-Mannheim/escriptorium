from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def async_email(subject, message, recipients, html=None):
    """
    Task used by celery to send an email,
    if in doubt use the higher level function in escriptorium.utils
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=False,
        html=html
    )
