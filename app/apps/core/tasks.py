import logging
import json
import os.path
import subprocess

from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model

from celery import shared_task
from imagekit.cachefiles import LazyImageCacheFile

from core.models import DocumentPart, Line, Block
from core.imagegenerators import CardThumbnail

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def generate_part_thumbnail(instance_pk):
    try:
        instance = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to generate thumbnail for innexistant DocumentPart : %d', instance_pk)
        return False

    try:
        file = LazyImageCacheFile('core:card.thumbnail', source=instance.image)
        file.generate()
    except:
        logger.exception('Error while trying to generate thumbnail.')
    # we can fail silently, the thumbnail will be generated on the fly and we have logs
    return True


@shared_task
def segment(instance_pk, user_pk=None):
    try:
        part = DocumentPart.objects.get(pk=instance_pk)
    except DocumentPart.DoesNotExist:
        logger.error('Trying to generate thumbnail for innexistant DocumentPart : %d', instance_pk)
        return False

    if user_pk:
        try:
            user = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            user = None
    else:
        user = None
    
    try:
        # cleanup pre-existing
        part.lines.all().delete()
        Block.objects.filter(document_part=part).delete()
        
        # kraken -i image.tif bw.png binarize
        fname = os.path.basename(part.image.file.name)
        bw_file = '/tmp/bw_' + fname
        error = subprocess.check_call(["kraken", "-i", part.image.path,
                                        bw_file,
                                        'binarize'])
        if error:
            raise RuntimeError("Something went wrong during binarization!")
        # kraken -i bw.png lines.json segment
        json_file = '/tmp/' + fname + '.lines.json'
        error = subprocess.check_call(["kraken", "-i", bw_file, json_file,
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
            user.notify(_("Something went wrong during the segmentation!"), level='danger')
        raise
    else:
        if user:
            user.notify(_("Segmentation done!"), level='success')
        part.segmented = True
        part.save()
