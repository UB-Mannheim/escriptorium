import os
from unittest.mock import patch
from zipfile import ZipFile

from core.models import Block, Line, LineTranscription
from core.tests.factory import CoreFactoryTestCase
from imports.parsers import METSZipParser, ParseError
from reporting.models import TaskReport

SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "samples",
)

PFX = "{http://www.loc.gov/METS/}"


class METSZipParserTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()

        user = self.factory.make_user()
        self.document = self.factory.make_document()
        self.report = TaskReport.objects.create(
            user=user,
            label="METS import from an archive",
            document=self.document,
            method="imports.tasks.document_import",
        )

    def test_parse_no_mets_in_archive(self):
        archive_path = f"{SAMPLES_DIR}/archive_without_mets.zip"
        with ZipFile(archive_path, 'w') as archive:
            archive.write(f"{SAMPLES_DIR}/alto_export_full_part1.xml", "test.xml")

        parser = METSZipParser(self.document, archive_path, self.report)
        with self.assertRaises(ParseError) as context:
            list(parser.parse())

        self.assertTrue("Couldn't find the METS file that should be there to define the archive." in str(context.exception))

        os.remove(f"{SAMPLES_DIR}/archive_without_mets.zip")

    @patch("imports.mets.METSProcessor.process")
    def test_parse_error_during_mets_processing(self, mock_process):
        mock_process.side_effect = Exception("Uhoh, something went wrong.")

        parser = METSZipParser(self.document, f"{SAMPLES_DIR}/simple_archive.zip", self.report)
        with self.assertRaises(ParseError) as context:
            list(parser.parse())

        self.assertTrue("An error occurred during the processing of the METS file contained in the archive: Uhoh, something went wrong." in str(context.exception))

    def test_parse_mets_with_one_source(self):
        self.assertEqual(Block.objects.all().count(), 0)
        self.assertEqual(Line.objects.all().count(), 0)
        self.assertEqual(LineTranscription.objects.all().count(), 0)
        parser = METSZipParser(self.document, f"{SAMPLES_DIR}/simple_archive.zip", self.report)
        list(parser.parse())

        self.assertListEqual(list(self.document.parts.values_list("original_filename", flat=True)), [
            "Kifayat_al-ghulam.pdf_000005.png",
            "Kifayat_al-ghulam.pdf_000006.png",
            "Kifayat_al-ghulam.pdf_000007.png",
            "Kifayat_al-ghulam.pdf_000008.png",
        ])
        self.assertListEqual(list(self.document.transcriptions.values_list("name", flat=True)), [
            "METS Import | transcript", "manual"
        ])
        # Assert that it clearly imported some data
        self.assertEqual(Block.objects.all().count(), 11)
        self.assertEqual(Line.objects.all().count(), 66)
        self.assertEqual(LineTranscription.objects.all().count(), 65)

    def test_parse_mets_with_tags_prefixed_by_namespace(self):
        self.assertEqual(Block.objects.all().count(), 0)
        self.assertEqual(Line.objects.all().count(), 0)
        self.assertEqual(LineTranscription.objects.all().count(), 0)
        parser = METSZipParser(self.document, f"{SAMPLES_DIR}/simple_archive_prefixed.zip", self.report)
        list(parser.parse())

        self.assertListEqual(list(self.document.parts.values_list("original_filename", flat=True)), [
            "Kifayat_al-ghulam.pdf_000005.png",
            "Kifayat_al-ghulam.pdf_000006.png",
            "Kifayat_al-ghulam.pdf_000007.png",
            "Kifayat_al-ghulam.pdf_000008.png",
        ])
        self.assertListEqual(list(self.document.transcriptions.values_list("name", flat=True)), [
            "METS Import | Layer 1", "manual"
        ])
        # Assert that it clearly imported some data
        self.assertEqual(Block.objects.all().count(), 11)
        self.assertEqual(Line.objects.all().count(), 66)
        self.assertEqual(LineTranscription.objects.all().count(), 65)

    def test_parse_mets_with_multiple_sources(self):
        self.assertEqual(Block.objects.all().count(), 0)
        self.assertEqual(Line.objects.all().count(), 0)
        self.assertEqual(LineTranscription.objects.all().count(), 0)
        parser = METSZipParser(self.document, f"{SAMPLES_DIR}/complex_archive.zip", self.report)
        list(parser.parse())

        self.assertListEqual(list(self.document.parts.values_list("original_filename", flat=True)), [
            "Kifayat_al-ghulam.pdf_000005.png",
            "Kifayat_al-ghulam.pdf_000006.png",
            "Kifayat_al-ghulam.pdf_000007.png",
            "Kifayat_al-ghulam.pdf_000008.png",
        ])
        self.assertListEqual(list(self.document.transcriptions.values_list("name", flat=True)), [
            "METS Import | ocr", "METS Import | transcript", "manual"
        ])
        # Assert that it clearly imported some data
        self.assertEqual(Block.objects.all().count(), 17)
        self.assertEqual(Line.objects.all().count(), 66)
        self.assertEqual(LineTranscription.objects.all().count(), 129)
