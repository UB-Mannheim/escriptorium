from django.template.loader import get_template

from users.tasks import async_email


def send_email(subject_template, txt_template, html_template,
               recipients,
               context=None,
               result_interface=None):
    """
    Higher level interface to send a multipart/alternative email with text/plain + text/html

    Send an email to the given recipient using given templates and context
    Queue with celery if settings.USE_CELERY == True

    result_interface is used by the task to update an instance if the mail was sent or got an error
    it's a tuple (app_name, model_name, instance_id) which needs to present .email_sent() and .email_error(msg) methods
    """
    subject_tmplt = get_template(subject_template)
    txt_tmplt = get_template(txt_template)
    html_tmplt = get_template(html_template)

    subject = subject_tmplt.render(context=context).strip('\n')
    msg = txt_tmplt.render(context=context)
    html = html_tmplt.render(context=context)

    async_email.delay(subject, msg, recipients, html=html, result_interface=result_interface)
