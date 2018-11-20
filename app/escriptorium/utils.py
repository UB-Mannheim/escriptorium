from django.conf import settings

from users.tasks import async_email


def send_email(subject, message, recipient, html=None):
    """
    Send an email to the given recipient using celery if settings.USE_CELERY == True
    if html is set, the email will be a multipart/alternative email with text/plain + text/html
    """
    if settings.USE_CELERY:
        send_email.delay(subject, message, [recipient,], html=html)
    else:
        send_email(subject, message, [recipient,], html=html)
