import json
import logging
import os.path
import subprocess
import redis

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.utils.translation import gettext as _

from celery import shared_task
from celery.signals import *
from easy_thumbnails.files import get_thumbnailer
from kraken import binarization, pageseg, rpred
from kraken.lib import models as kraken_models

from users.consumers import send_event


logger = logging.getLogger(__name__)
User = get_user_model()
redis_ = redis.Redis(host=settings.REDIS_HOST,
                     port=settings.REDIS_PORT,
                     db=getattr(settings, 'REDIS_DB', 0))


def update_client_state(part_id, task, status, task_id=None, data=None):
    DocumentPart = apps.get_model('core', 'DocumentPart')
    part = DocumentPart.objects.get(pk=part_id)
    task_name = task.split('.')[-1]
    send_event('document', part.document.pk, "part:workflow", {
        "id": part.pk,
        "process": task_name,
        "status": status,
        "task_id": task_id,
        "data": data or {}
    })

    
@shared_task
def generate_part_thumbnails(instance_pk):
    if not settings.THUMBNAIL_ENABLE:
        return 
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        raise
    
    aliases = {}
    thbn = get_thumbnailer(part.image)
    print('###', part.image)
    for alias, config in settings.THUMBNAIL_ALIASES[''].items():
        aliases[alias] = thbn.get_thumbnail(config).url
    return aliases


@shared_task
def convert(instance_pk, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to convert innexistant DocumentPart : %d', instance_pk)
        raise
    part.convert()

    
@shared_task
def lossless_compression(instance_pk, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        raise
    part.compress()


@shared_task
def binarize(instance_pk, user_pk=None, binarizer=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to binarize innexistant DocumentPart : %d', instance_pk)
        raise
    
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        part.binarize()
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the binarization!"),
                        id="binarization-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CREATED
        part.save()
        raise e
    else:
        if user:
            user.notify(_("Binarization done!"),
                        id="binarization-success", level='success')


@shared_task
def segment(instance_pk, user_pk=None, steps=None, text_direction=None, **kwargs):
    """
    steps can be either 'regions', 'lines' or 'both'
    """
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist as e:
        logger.error('Trying to segment innexistant DocumentPart : %d', instance_pk)
        raise e

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        part.segment(steps=steps, text_direction=text_direction)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the segmentation!"),
                        id="segmentation-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_BINARIZED
        part.save()
        raise e
    else:
        if user:
            user.notify(_("Segmentation done!"),
                        id="segmentation-success", level='success')


@shared_task
def train(model, pks, user_pk=None, **kwargs):
    pass

 
@shared_task
def transcribe(instance_pk, model_pk=None, user_pk=None, text_direction=None, **kwargs):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to transcribe innexistant DocumentPart : %d', instance_pk)
        raise
    
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    if model_pk:
        try:
            OcrModel = apps.get_model('core', 'OcrModel')
            model = OcrModel.objects.get(pk=model_pk)
        except OcrModel.DoesNotExist:
            # Not sure how we should deal with this case
            model = None
    else:
        model = None
    
    try:
        part.transcribe(model=model)
    except Exception as e:
        if user:
            user.notify(_("Something went wrong during the transcription!"),
                        id="transcription-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_SEGMENTED
        part.save()
        raise
    else:
        if user and model:
            user.notify(_("Transcription done!"),
                        id="transcription-success",
                        level='success')


def check_signal_order(old_signal, new_signal):
    SIGNAL_ORDER = ['before_task_publish', 'task_prerun', 'task_failure', 'task_success']
    return SIGNAL_ORDER.index(old_signal) < SIGNAL_ORDER.index(new_signal)


@before_task_publish.connect
def before_publish_state(sender=None, body=None, **kwargs):
    if not sender.startswith('core.tasks'):
        return
    instance_id = body[0][0]
    
    data = json.loads(redis_.get('process-%d' % instance_id) or '{}')
    
    try:
        # protects against signal race condition
        if (data[sender]['task_id'] == sender.request.id and
            not check_signal_order(data[sender]['status'], signal_name)):
            return
    except KeyError:
        pass
    
    data[sender] = {
        "task_id": kwargs['headers']['id'],
        "status": 'before_task_publish'
    }
    redis_.set('process-%d' % instance_id, json.dumps(data))
    update_client_state(instance_id, sender, 'pending')


@task_prerun.connect
@task_success.connect
@task_failure.connect
def done_state(sender=None, body=None, **kwargs):
    if not sender.name.startswith('core.tasks'):
        return
    instance_id = sender.request.args[0]
    
    data = json.loads(redis_.get('process-%d' % instance_id) or '{}')

    signal_name = kwargs['signal'].name
    
    try:
        # protects against signal race condition
        if (data[sender.name]['task_id'] == sender.request.id and
            not check_signal_order(data[sender.name]['status'], signal_name)):
            return
    except KeyError:
        pass

    data[sender.name] = {
        "task_id": sender.request.id,
        "status": signal_name
    }
    status = {
        'task_success': 'done',
        'task_failure': 'error',
        'task_prerun': 'ongoing'
    }[signal_name]
    if status == 'error':
        # remove any pending task down the chain
        data = {k:v for k,v in data.items() if v['status'] != 'pending'}

    redis_.set('process-%d' % instance_id, json.dumps(data))

    if status == 'done':
        result = kwargs.get('result', None)
    else:
        result = None
    update_client_state(instance_id, sender.name, status, task_id=sender.request.id, data=result)
