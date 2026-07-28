import os
from io import BytesIO
from unittest.mock import Mock, patch
from zipfile import ZipFile

from lxml import etree
from requests.exceptions import RequestException

from core.models import (
    Block,
    DocumentMetadata,
    DocumentPartMetadata,
    Line,
    LineTranscription,
    Metadata,
)
from core.tests.factory import CoreFactoryTestCase
from imports.parsers import (
    METSRemoteParser,
    METSZipParser,
    ParseError,
    make_parser,
    safe_xml_parser,
)
from reporting.models import TaskReport

SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "samples",
)

PFX = "{http://www.loc.gov/METS/}"


def mocked_get(uri):
    with ZipFile(SAMPLES_DIR + "/complex_archive.zip") as archive:
        filename = os.path.basename(uri)
        try:
            with archive.open(filename) as file:
                return Mock(content=file.read(), status_code=200)
        except Exception:
            raise RequestException("Uhoh, something went wrong.")


class METSRemoteParserTestCase(CoreFactoryTestCase):
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

        with ZipFile(SAMPLES_DIR + "/simple_archive.zip") as archive:
            with archive.open("simple_mets.xml") as mets:
                self.simple_root = etree.parse(mets).getroot()

        with ZipFile(SAMPLES_DIR + "/simple_archive_prefixed.zip") as archive:
            with archive.open("transcript_prefixed.xml") as mets:
                self.simple_prefixed_root = etree.parse(mets).getroot()

        with ZipFile(SAMPLES_DIR + "/complex_archive.zip") as archive:
            with archive.open("transcript-ocr.xml") as mets:
                self.complex_root = etree.parse(mets).getroot()

    @patch("imports.mets.METSProcessor.process")
    def test_parse_error_during_mets_processing(self, mock_process):
        mock_process.side_effect = Exception("Uhoh, something went wrong.")

        parser = METSRemoteParser(self.document, None, self.report, self.simple_root, "https://whatever.com")
        with self.assertRaises(ParseError) as context:
            list(parser.parse())

        self.assertTrue("An error occurred during the processing of the remote METS file: Uhoh, something went wrong." in str(context.exception))

    @patch("requests.get")
    @patch("imports.mets.METSProcessor.check_is_image")
    def test_parse_mets_with_one_source(self, mock_check_is_image, mock_get):
        mock_get.side_effect = mocked_get
        mock_check_is_image.side_effect = [(True, "image/png"), (False, "text/xml")] * 4

        self.assertEqual(Metadata.objects.count(), 0)
        self.assertEqual(DocumentMetadata.objects.count(), 0)
        self.assertEqual(DocumentPartMetadata.objects.count(), 0)
        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(Line.objects.count(), 0)
        self.assertEqual(LineTranscription.objects.count(), 0)
        parser = METSRemoteParser(self.document, None, self.report, self.simple_root, "https://whatever.com")
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
        self.assertEqual(Metadata.objects.count(), 10)
        self.assertEqual(DocumentMetadata.objects.count(), 4)
        self.assertEqual(DocumentPartMetadata.objects.count(), 6)
        self.assertEqual(Block.objects.count(), 11)
        self.assertEqual(Line.objects.count(), 66)
        self.assertEqual(LineTranscription.objects.count(), 65)

    @patch("requests.get")
    @patch("imports.mets.METSProcessor.check_is_image")
    def test_parse_mets_with_tags_prefixed_by_namespace(self, mock_check_is_image, mock_get):
        mock_get.side_effect = mocked_get
        mock_check_is_image.side_effect = [(True, "image/png"), (False, "text/xml")] * 4

        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(Line.objects.count(), 0)
        self.assertEqual(LineTranscription.objects.count(), 0)
        parser = METSRemoteParser(self.document, None, self.report, self.simple_prefixed_root, "https://whatever.com")
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
        self.assertEqual(Block.objects.count(), 11)
        self.assertEqual(Line.objects.count(), 66)
        self.assertEqual(LineTranscription.objects.count(), 65)

    @patch("requests.get")
    @patch("imports.mets.METSProcessor.check_is_image")
    def test_parse_mets_with_multiple_sources(self, mock_check_is_image, mock_get):
        mock_get.side_effect = mocked_get
        mock_check_is_image.side_effect = [(True, "image/png"), (False, "text/xml"), (False, "text/xml")] * 4

        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(Line.objects.count(), 0)
        self.assertEqual(LineTranscription.objects.count(), 0)
        parser = METSRemoteParser(self.document, None, self.report, self.complex_root, "https://whatever.com")
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
        self.assertEqual(Block.objects.count(), 17)
        self.assertEqual(Line.objects.count(), 66)
        self.assertEqual(LineTranscription.objects.count(), 129)


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
        self.assertEqual(Metadata.objects.count(), 0)
        self.assertEqual(DocumentMetadata.objects.count(), 0)
        self.assertEqual(DocumentPartMetadata.objects.count(), 0)
        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(Line.objects.count(), 0)
        self.assertEqual(LineTranscription.objects.count(), 0)
        with open(f"{SAMPLES_DIR}/simple_archive.zip", "rb") as file_handler:
            parser = METSZipParser(self.document, file_handler, self.report)
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
        self.assertEqual(Metadata.objects.count(), 10)
        self.assertEqual(DocumentMetadata.objects.count(), 4)
        self.assertEqual(DocumentPartMetadata.objects.count(), 6)
        self.assertEqual(Block.objects.count(), 11)
        self.assertEqual(Line.objects.count(), 66)
        self.assertEqual(LineTranscription.objects.count(), 65)

    def test_parse_mets_with_tags_prefixed_by_namespace(self):
        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(Line.objects.count(), 0)
        self.assertEqual(LineTranscription.objects.count(), 0)
        with open(f"{SAMPLES_DIR}/simple_archive_prefixed.zip", "rb") as file_handler:
            parser = METSZipParser(self.document, file_handler, self.report)
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
        self.assertEqual(Block.objects.count(), 11)
        self.assertEqual(Line.objects.count(), 66)
        self.assertEqual(LineTranscription.objects.count(), 65)

    def test_parse_mets_with_multiple_sources(self):
        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(Line.objects.count(), 0)
        self.assertEqual(LineTranscription.objects.count(), 0)
        with open(f"{SAMPLES_DIR}/complex_archive.zip", "rb") as file_handler:
            parser = METSZipParser(self.document, file_handler, self.report)
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
        self.assertEqual(Block.objects.count(), 17)
        self.assertEqual(Line.objects.count(), 66)
        self.assertEqual(LineTranscription.objects.count(), 129)


class ExternalEntityTestCase(CoreFactoryTestCase):
    """Imported XML is uploaded or fetched by URL.

    Recent lxml refuses the external entity on its own, but lxml is transitive
    here and unpinned, so these assert the parser we pass rather than the
    default we happen to get.
    """

    SAMPLE = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE alto [ <!ENTITY ext SYSTEM "file:///etc/passwd"> ]>'
        b'<alto xmlns="http://www.loc.gov/standards/alto/ns-v4#">'
        b'<Description><fileName>&ext;</fileName></Description></alto>'
    )

    def make_upload(self, content, name="sample.xml"):
        handler = BytesIO(content)
        handler.name = name
        return handler

    def test_safe_parser_does_not_resolve_external_entities(self):
        root = etree.parse(self.make_upload(self.SAMPLE), safe_xml_parser()).getroot()
        self.assertNotIn("root:x:0:0", etree.tostring(root).decode())

    def test_make_parser_does_not_resolve_external_entities(self):
        document = self.factory.make_document()
        report = TaskReport.objects.create(user=document.owner, label="entities")
        parser = make_parser(document, self.make_upload(self.SAMPLE), report=report)
        self.assertNotIn("root:x:0:0", etree.tostring(parser.root).decode())

    def test_entity_expansion_is_bounded(self):
        entities = b"".join(
            b'<!ENTITY e%d "' % i + b"&e%d;" % (i - 1) * 10 + b'">'
            for i in range(1, 10)
        )
        nested = (b'<!DOCTYPE r [<!ENTITY e0 "AAAAAAAAAA">' + entities
                + b"]><alto xmlns=\"http://www.loc.gov/standards/alto/ns-v4#\">"
                b"<x>&e9;</x></alto>")
        with self.assertRaises(etree.XMLSyntaxError):
            etree.parse(self.make_upload(nested), safe_xml_parser())
