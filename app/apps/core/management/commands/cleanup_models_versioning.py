import datetime
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import OcrModel

logger = logging.getLogger("core")
logger.setLevel(logging.ERROR)


class Command(BaseCommand):
    help = "Removes all content from models versioning older than settings.MODELS_VERSION_RETENTION (in days)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Avoid doing any actual changes to the file system or database, only print the number of models that would be affected.",
            default=False
        )

    def handle(self, *args, **kwargs):
        logger.setLevel(logging.INFO)

        if settings.MODELS_VERSION_RETENTION == 0:
            logger.info("MODELS_VERSION_RETENTION set to 0. Nothing will be cleaned up.")
            return

        today = timezone.now()
        older_than = today - datetime.timedelta(days=settings.MODELS_VERSION_RETENTION)
        to_be_cleaned = OcrModel.objects.filter(version_updated_at__lt=older_than).exclude(versions__exact=[])
        dry_run = kwargs.get("dry_run", False)
        for model in to_be_cleaned:
            logger.info("Deleting %s epoch models from %s #%d.", len(model.versions), model.name, model.id)
            if not dry_run:
                model.flush_history()
                # specify update_fields to avoid updating the auto_now fields
                model.save(update_fields=['versions'])
