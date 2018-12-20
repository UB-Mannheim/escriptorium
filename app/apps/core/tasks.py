import logging
import json
import os.path
import subprocess

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files import File
from django.utils.translation import gettext as _

from celery import shared_task
from imagekit.cachefiles import LazyImageCacheFile

from users.consumers import send_event


logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def generate_part_thumbnails(instance_pk):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        instance = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to generate thumbnail for innexistant DocumentPart : %d', instance_pk)
        return False

    try:
        file = LazyImageCacheFile('core:card.thumbnail', source=instance.image_source)
        file.generate()
        file = LazyImageCacheFile('core:list.thumbnail', source=instance.image_source)
        file.generate()
    except:
        logger.exception('Error while trying to generate thumbnails.')
    # we can fail silently, the thumbnail will be generated on the fly and we have logs
    return True


def update_client_state(part):
    send_event('document', part.document.pk, "part:workflow", {
        "id": part.pk,
        "value": part.workflow_state
    })


@shared_task
def binarize(instance_pk, user_pk=None):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to binarize innexistant DocumentPart : %d', instance_pk)
        return False
    
    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        part.workflow_state = part.WORKFLOW_STATE_BINARIZING
        part.save()
        update_client_state(part)
        
        fname = os.path.basename(part.image_source.file.name)
        bw_file_name = 'bw_' + fname
        bw_file = os.path.join(os.path.dirname(part.image_source.file.name), bw_file_name)
        error = subprocess.check_call(["kraken", "-i", part.image_source.path,
                                       bw_file,
                                       'binarize'])
        if error:
            raise RuntimeError("Something went wrong during binarization!")
        
    except:
        if user:
            user.notify(_("Something went wrong during the binarization!"),
                        id="binarization-error", level='danger')
        update_client_state(part)
        part.workflow_state = part.WORKFLOW_STATE_CREATED
        part.save()
        raise
    else:
        if user:
            user.notify(_("Binarization done!"),
                        id="binarization-success", level='success')
        
        from core.models import document_images_path  # meh
        part.bw_image = document_images_path(part, bw_file_name)
        part.workflow_state = part.WORKFLOW_STATE_BINARIZED
        part.save()
        update_client_state(part)
        
        file = LazyImageCacheFile('core:large', source=part.bw_image)
        file.generate()


@shared_task
def segment(instance_pk, user_pk=None):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to segment innexistant DocumentPart : %d', instance_pk)
        return False

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        Block = apps.get_model('core', 'Block')
        Line = apps.get_model('core', 'Line')
        # cleanup pre-existing
        part.lines.all().delete()
        Block.objects.filter(document_part=part).delete()
        
        part.workflow_state = part.WORKFLOW_STATE_SEGMENTING
        part.save()
        update_client_state(part)
        
        fname = os.path.basename(part.image_source.file.name)
        
        # kraken -i bw.png lines.json segment
        json_file = '/tmp/' + fname + '.lines.json'
        error = subprocess.check_call(["kraken", "-i", part.bw_image.file.name, json_file,
                                       #'--text-direction', text_direction,
                                       # Error: no such option: --text-direction
                                       'segment'])   # -script-detection
        if error:
            raise RuntimeError("Something went wrong during segmentation!")
        
        with open(json_file, 'r') as fh:
            data = json.loads(fh.read())
            for line in data['boxes']:
                # block = Block.objects.create(document_part=part)
                # for line in block_:
                Line.objects.create(
                    document_part=part,
                #     # block=block,
                #     # script=script,
                    box=line)
    except:
        if user:
            user.notify(_("Something went wrong during the segmentation!"),
                        id="segmentation-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_BINARIZED
        part.save()
        update_client_state(part)
        raise
    else:
        if user:
            user.notify(_("Segmentation done!"),
                        id="segmentation-success", level='success')
        part.workflow_state = part.WORKFLOW_STATE_SEGMENTED
        part.save()
        update_client_state(part)


@shared_task
def transcribe(part_pk, user_pk=None):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=part_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to transcribe innexistant DocumentPart : %d', instance_pk)
        return False

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None

    Transcription.objects.get_or_create(name='default', document=part.document)
    part.workflow_state = part.WORKFLOW_STATE_TRANSCRIBING
    part.save()
    update_client_state(part)
    
    # model = part.select_model()
    #if model:
    #    TODO: kraken ocr
