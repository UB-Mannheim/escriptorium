import logging
import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from core.models import OcrModel

logger = logging.getLogger("core")
logger.setLevel(logging.ERROR)


class Command(BaseCommand):
    help = (
        "Removes OcrModel rows without a file and model directories under "
        "MEDIA_ROOT/models that no OcrModel references anymore."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be cleaned up, without changing the file system or the database.",
            default=False
        )

    def handle(self, *args, **kwargs):
        logger.setLevel(logging.INFO)
        dry_run = kwargs.get("dry_run", False)

        fileless = OcrModel.objects.filter(Q(file__isnull=True) | Q(file=""))
        for model in fileless:
            if model.training:
                logger.warning(
                    "Keeping model %r #%d: the training flag is set, but no file exists "
                    "(possibly a stuck training).", model.name, model.pk
                )
                continue
            logger.info("Deleting model %r #%d because it has no file.", model.name, model.pk)
            if not dry_run:
                model.delete()

        models_dir = os.path.join(settings.MEDIA_ROOT, "models")
        if os.path.isdir(models_dir):
            referenced = set(
                name.split("/")[1]
                for name in OcrModel.objects.exclude(file__isnull=True).exclude(file="")
                .values_list("file", flat=True)
            )
            for directory in os.listdir(models_dir):
                path = os.path.join(models_dir, directory)
                if directory in referenced or not os.path.isdir(path):
                    continue
                logger.info("Deleting orphaned model directory %s.", path)
                if not dry_run:
                    shutil.rmtree(path)

        for model in OcrModel.objects.exclude(file__isnull=True).exclude(file=""):
            if not os.path.exists(os.path.join(settings.MEDIA_ROOT, model.file.name)):
                logger.warning(
                    "Model %r #%d references a file that does not exist: %s",
                    model.name, model.pk, model.file.name
                )
