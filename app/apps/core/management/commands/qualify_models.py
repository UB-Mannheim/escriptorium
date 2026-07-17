from django.core.management.base import BaseCommand

from core.models import OcrModel
from core.tasks import qualify_model


class Command(BaseCommand):
    help = "Enqueues architecture qualification tasks for OcrModels, use it to (re)qualify models if the data migration could not reach the broker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Also requalify models that already have an architecture set, instead of only unqualified ones.",
            default=False
        )

    def handle(self, *args, **kwargs):
        models = OcrModel.objects.exclude(file='').exclude(file__isnull=True)
        if not kwargs.get("all"):
            models = models.filter(architecture__isnull=True)
        pks = models.values_list('pk', flat=True)
        for pk in pks:
            qualify_model.delay(pk)
        self.stdout.write("enqueued qualification for %d model(s)" % len(pks))
