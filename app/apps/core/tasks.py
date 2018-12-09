import logging

from celery import shared_task
from imagekit.cachefiles import LazyImageCacheFile

from core.models import DocumentPart
from core.imagegenerators import CardThumbnail

logger = logging.getLogger(__name__)


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
