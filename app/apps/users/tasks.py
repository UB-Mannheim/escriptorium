from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail

# DO NOT REMOVE THIS IMPORT, it will break celery tasks located in this file
from reporting.tasks import create_task_reporting  # noqa F401

logger = logging.getLogger(__name__)


def email_result(result_interface, success=True):
    app_name, model_name, instance_id = result_interface
    model = apps.get_model(app_label=app_name, model_name=model_name)
    try:
        instance = model.objects.get(id=instance_id)
    except model.DoesNotExist:
        logger.error("Tried to update %s.%s but instance with id %d doesn't exist.",
                     app_name, model_name, instance_id)
    else:
        if success:
            instance.email_sent()
            logger.debug('Updated %s.%s:%d to SENT', app_name, model_name, instance_id)
        else:
            instance.email_error()
            logger.debug('Updated %s.%s:%d to ERROR', app_name, model_name, instance_id)


@shared_task
def async_email(subject, message, recipients, html=None, result_interface=None):
    """
    Task used by celery to send an email,
    if in doubt use the higher level function in escriptorium.utils
    """
    try:
        success = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
            html_message=html)
    except Exception:  # Good old catch all, fine in this case
        logger.exception('Error sending email %s to %s.', subject, recipients)
        if result_interface:
            email_result(result_interface, success=False)
    else:
        if result_interface:
            email_result(result_interface, success=success)
