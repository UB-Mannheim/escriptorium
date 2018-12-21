import json
import logging
import os.path
import subprocess

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.utils.translation import gettext as _

from celery import shared_task
from easy_thumbnails.files import generate_all_aliases

from users.consumers import send_event


logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def generate_part_thumbnails(model, pk, field):
    instance = model._default_manager.get(pk=pk)
    fieldfile = getattr(instance, field)
    generate_all_aliases(fieldfile, include_global=True)


@shared_task(bind=True)
def lossless_compression(self, instance_pk):
    try:
        DocumentPart = apps.get_model('core', 'DocumentPart')
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to compress innexistant DocumentPart : %d', instance_pk)
        return False
    
    convert = False
    old_name = part.image.file.name
    filename, extension = os.path.splitext(old_name)
    if extension != ".png":
        convert = True
        new_name = filename + ".png"
        error = subprocess.check_call(["convert", old_name, new_name])
        if error:
            raise RuntimeError("Error trying to convert file(%s) to png.")
    else:
        new_name = old_name
    
    opti_name = filename + '_opti.png'
    # Note: leave it fail if need be
    subprocess.check_call(["pngcrush", "-q", new_name, opti_name])
    os.rename(opti_name, new_name)
    if convert:
        part.image = new_name.split(settings.MEDIA_ROOT)[1][1:]
        os.remove(old_name)
    if part.workflow_state < part.WORKFLOW_STATE_COMPRESSED:
        part.workflow_state = part.WORKFLOW_STATE_COMPRESSED
        part.save()


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
        
        fname = os.path.basename(part.image.file.name)
        bw_file_name = 'bw_' + fname
        bw_file = os.path.join(os.path.dirname(part.image.file.name), bw_file_name)
        error = subprocess.check_call(["kraken", "-i", part.image.path,
                                       bw_file,
                                       'binarize'])
        if error:
            raise RuntimeError("Something went wrong during binarization!")
        
    except:
        if user:
            user.notify(_("Something went wrong during the binarization!"),
                        id="binarization-error", level='danger')
        part.workflow_state = part.WORKFLOW_STATE_CREATED
        part.save()
        update_client_state(part)
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
        
        fname = os.path.basename(part.image.file.name)
        
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

    Transcription = apps.get_model('core', 'Transcription')
    Transcription.objects.get_or_create(name='default', document=part.document)
    part.workflow_state = part.WORKFLOW_STATE_TRANSCRIBING
    part.save()
    update_client_state(part)
    
    # model = part.select_model()
    #if model:
    #    TODO: kraken ocr
