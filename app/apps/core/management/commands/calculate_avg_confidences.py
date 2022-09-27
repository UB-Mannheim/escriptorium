import logging
from statistics import mean

from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from django.db.models import Avg, FloatField
from django.db.models.functions import Coalesce

from core.models import DocumentPart, LineTranscription, Transcription

logger = logging.getLogger("avg_confidence")


class Command(BaseCommand):
    help = "Compute average character confidence for all existing OCR/HTR lines with confidence values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            nargs="?",
            type=int,
            help="Specify a batch size for processing sets of data.",
            default=1000,
            const=1000,
        )

    def handle(self, *args, **options):
        batch_size = options.get("batch_size", 1000)
        logger.info(f"Calculating confidences with batch_size {batch_size}...")
        self.calculate_avg_confidences(batch_size=batch_size)
        logger.info("Done!")

    def calculate_avg_confidences(self, batch_size=1000):
        # Computes average character confidence for all existing OCR/HTR lines with confidence
        # values. This will be done automatically for each new transcription performed--this
        # management command is just to populate existing records.

        # First, compute average confidence per line. Save this in a DB field to allow fast
        # retrieval by page-level view.
        line_transcriptions = LineTranscription.objects.filter(
            graphs__0__confidence__isnull=False
        )

        # use Paginator to fetch and process these in batches
        # adapted from https://nextlinklabs.com/insights/django-big-data-iteration
        paginator = Paginator(line_transcriptions, batch_size)

        for page_number in paginator.page_range:
            page = paginator.page(page_number)
            updates = []

            for lt in page.object_list:
                lt.avg_confidence = mean([graph["confidence"] for graph in lt.graphs])
                updates.append(lt)

            LineTranscription.objects.bulk_update(updates, ["avg_confidence"])

        # Now, compute average line confidence for all existing Transcriptions. This will be used
        # for summary views (project level).
        transcriptions = Transcription.objects.filter(
            linetranscription__avg_confidence__isnull=False
        ).distinct()

        paginator = Paginator(transcriptions, batch_size)

        for page_number in paginator.page_range:
            page = paginator.page(page_number)
            updates = []

            for t in page.object_list:
                lines = t.linetranscription_set.all()
                t.avg_confidence = lines.aggregate(avg=Avg("avg_confidence")).get("avg")
                updates.append(t)

            Transcription.objects.bulk_update(updates, ["avg_confidence"])

        # Finally, compute average line confidence for DocumentParts. This will be used for
        # summary views (document level).
        parts = DocumentPart.objects.all()

        paginator = Paginator(parts, batch_size)

        for page_number in paginator.page_range:
            page = paginator.page(page_number)
            updates = []

            # DocumentParts may be linked to more than one transcription (i.e. multiple OCR
            # models), so here we determine the greatest average as opposed to just the average.
            # This should be sufficient for overview/summary purposes.
            for part in page.object_list:
                avg_qs = LineTranscription.objects.filter(
                    line__document_part=part
                ).values(
                    "transcription",  # Since DocumentPart does not keep track of individual
                                      # transcriptions, and is only linked to lines, we have to
                                      # group lines by transcription.
                ).annotate(
                    avg=Coalesce(Avg("avg_confidence"), -1.0, output_field=FloatField()),  # Average "avg_confidence" for lines
                ).order_by("-avg")
                if avg_qs.count():
                    max_avg = avg_qs[0]
                    # the max will only be negative if Avg could not be calculated, i.e. part has
                    # manual transcriptions only
                    if max_avg["avg"] >= 0:
                        part.max_avg_confidence = max_avg["avg"]
                    else:
                        # in that case, it should not have max avg confidence; nullify if present
                        part.max_avg_confidence = None
                    updates.append(part)

            DocumentPart.objects.bulk_update(updates, ["max_avg_confidence"])
