import logging

from django.core.management.base import BaseCommand

from core.models import Document
from imports.parsers import METSZipParser
from reporting.models import TaskReport
from users.models import User

logger = logging.getLogger("es_indexing")
logger.setLevel(logging.ERROR)


class Command(BaseCommand):
    help = "A demonstration command to test the METS import from archive code. To be removed once the code is callable through eScriptorium frontend."

    def add_arguments(self, parser):
        parser.add_argument(
            "archive_path",
            type=str,
            help="Path towards a ZIP archive described by a METS file (contained inside it).",
        )
        parser.add_argument(
            "--document-pk",
            type=int,
            help="The document where to import the data retrieve from the METS archive.",
        )
        parser.add_argument(
            "--user-pk",
            type=int,
            help="The user to use to create the TaskReport object.",
        )

    def handle(self, *args, **options):
        document = Document.objects.get(pk=options["document_pk"])
        report = TaskReport.objects.create(
            user=User.objects.get(pk=options["user_pk"]),
            label="METS import from an archive (launched by the demo command)",
            document=document,
            method="imports.tasks.document_import",
        )

        parser = METSZipParser(document, options["archive_path"], report)
        parser.validate()
        list(parser.parse())
