import io
import os
from unittest.mock import Mock, patch
from zipfile import ZipFile

from lxml import etree, html
from requests.exceptions import RequestException

from core.tests.factory import CoreFactoryTestCase
from imports.mets import METSPage, METSProcessor
from imports.parsers import ParseError

SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "samples",
)

PFX = "{http://www.loc.gov/METS/}"


class METSProcessorTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()

        self.archive_path = SAMPLES_DIR + "/simple_archive.zip"

        with ZipFile(self.archive_path) as archive:
            with archive.open("simple_mets.xml") as mets:
                self.root = etree.parse(mets).getroot()

    def test_retrieve_in_archive_no_archive(self):
        processor = METSProcessor(None)
        with self.assertRaises(AttributeError) as context:
            processor.retrieve_in_archive("simple_mets.xml")

        self.assertTrue("'NoneType' object has no attribute 'seek'" in str(context.exception))

    def test_retrieve_in_archive_not_in_archive(self):
        processor = METSProcessor(None, archive=self.archive_path)
        with self.assertRaises(KeyError):
            processor.retrieve_in_archive("not_my_mets.xml")

    def test_retrieve_in_archive(self):
        processor = METSProcessor(None, archive=self.archive_path)
        file = processor.retrieve_in_archive("simple_mets.xml")

        self.assertTrue(isinstance(file, io.IOBase))
        file.close()

    def test_get_files_from_file_sec_no_section(self):
        root = etree.Element("mets")

        processor = METSProcessor(root)
        with self.assertRaises(ParseError) as context:
            processor.get_files_from_file_sec()

        self.assertTrue("The file section <fileSec/> wasn't found in the METS file." in str(context.exception))

    def test_get_files_from_file_sec(self):
        processor = METSProcessor(self.root)
        files = processor.get_files_from_file_sec()
        self.assertListEqual(list(files.keys()), [
            "binarized1", "binarized2", "binarized3", "binarized4",
            "transcript1", "transcript2", "transcript3", "transcript4",
        ])

        for file in files.values():
            self.assertTrue(etree.iselement(file))
            self.assertTrue(file.tag == "{http://www.loc.gov/METS/}file")

    def test_get_pages_from_struct_map_no_mapping(self):
        root = etree.Element("mets")

        processor = METSProcessor(root)
        with self.assertRaises(ParseError) as context:
            processor.get_pages_from_struct_map()

        self.assertTrue("The structure mapping <structMap/> wasn't found in the METS file." in str(context.exception))

    def test_get_pages_from_struct_map(self):
        processor = METSProcessor(self.root)
        pages = processor.get_pages_from_struct_map()
        self.assertEqual(len(pages), 4)

        for page in pages:
            self.assertTrue(etree.iselement(page))
            self.assertTrue(page.tag == "{http://www.loc.gov/METS/}div")

    def test_get_file_pointers(self):
        processor = METSProcessor(self.root)
        pages = processor.get_pages_from_struct_map()

        pointers = processor.get_file_pointers(pages[0])
        self.assertEqual(len(pointers), 2)

        for pointer in pointers:
            self.assertTrue(etree.iselement(pointer))
            self.assertTrue(pointer.tag == "{http://www.loc.gov/METS/}fptr")

    def test_get_file_location_no_location(self):
        file = etree.Element(f"{PFX}file")

        processor = METSProcessor(self.root)
        with self.assertRaises(ParseError) as context:
            processor.get_file_location(file)

        self.assertTrue(f"Can't find a file location <FLocat/> holding a href attribute for the file {str(html.tostring(file))}." in str(context.exception))

    def test_get_file_location_no_href(self):
        file = etree.Element(f"{PFX}file")
        file.append(etree.Element(f"{PFX}FLocat"))

        processor = METSProcessor(self.root)
        with self.assertRaises(ParseError) as context:
            processor.get_file_location(file)

        self.assertTrue(f"Can't find a file location <FLocat/> holding a href attribute for the file {str(html.tostring(file))}." in str(context.exception))

    def test_get_file_location(self):
        file = etree.Element(f"{PFX}file")
        file.append(etree.Element(f"{PFX}FLocat", href="path/file.txt"))

        processor = METSProcessor(self.root)
        location = processor.get_file_location(file)

        self.assertEqual(location, "path/file.txt")

    def test_get_file_group_name_not_found(self):
        processor = METSProcessor(self.root)
        # No USE on file and no parent
        file = etree.Element(f"{PFX}file")
        group_name = processor.get_file_group_name(file)
        self.assertIsNone(group_name)

        # No USE on file and wrong parent tag
        div = etree.Element(f"{PFX}div")
        file = etree.SubElement(div, f"{PFX}file")
        group_name = processor.get_file_group_name(file)
        self.assertIsNone(group_name)

        # No USE on file nor parent
        file_grp = etree.Element(f"{PFX}filegrp")
        file = etree.SubElement(file_grp, f"{PFX}file")
        group_name = processor.get_file_group_name(file)
        self.assertIsNone(group_name)

    def test_get_file_group_name_on_file(self):
        file_grp = etree.Element(f"{PFX}filegrp", USE="parent_transcription")
        file = etree.SubElement(file_grp, f"{PFX}file", USE="transcription")

        processor = METSProcessor(self.root)
        group_name = processor.get_file_group_name(file)
        self.assertEqual(group_name, "transcription")

    def test_get_file_group_name_on_parent(self):
        file_grp = etree.Element(f"{PFX}filegrp", USE="parent_transcription")
        file = etree.SubElement(file_grp, f"{PFX}file")

        processor = METSProcessor(self.root)
        group_name = processor.get_file_group_name(file)
        self.assertEqual(group_name, "parent_transcription")

    def test_build_remote_uri_relative_href(self):
        processor = METSProcessor(self.root, mets_base_uri="https://whatever.com")
        uri = processor.build_remote_uri("path/to/a-simple-image.png")
        self.assertEqual(uri, "https://whatever.com/path/to/a-simple-image.png")

    def test_build_remote_uri_external_href(self):
        processor = METSProcessor(self.root, mets_base_uri="https://whatever.com")
        uri = processor.build_remote_uri("https://somethingelse.com/a-simple-image.png")
        self.assertEqual(uri, "https://somethingelse.com/a-simple-image.png")

    @patch("requests.head")
    def test_check_is_image_true_and_already_exists(self, mock_head):
        mock_head.return_value = Mock(headers={"content-type": "image/png"}, status_code=200)
        processor = METSProcessor(self.root)
        is_image, stop = processor.check_is_image("https://whatever.com/a-simple-image.png", True)
        self.assertTrue(is_image)
        self.assertTrue(stop)

    @patch("requests.head")
    def test_check_is_image_true_and_do_not_exists(self, mock_head):
        mock_head.return_value = Mock(headers={"content-type": "image/png"}, status_code=200)
        processor = METSProcessor(self.root)
        is_image, stop = processor.check_is_image("https://whatever.com/a-simple-image.png", False)
        self.assertTrue(is_image)
        self.assertFalse(stop)

    @patch("requests.head")
    def test_check_is_image_false(self, mock_head):
        mock_head.return_value = Mock(headers={"content-type": "text/xml"}, status_code=200)
        processor = METSProcessor(self.root)
        is_image, stop = processor.check_is_image("https://whatever.com/a-simple-xml.xml", True)
        self.assertFalse(is_image)
        self.assertFalse(stop)

    def test_process_single_page_no_file_pointers(self):
        processor = METSProcessor(self.root)
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        page = pages[0]
        for pointer in page.findall("mets:fptr", namespaces=processor.NAMESPACES):
            page.remove(pointer)

        mets_page = processor.process_single_page(page, files)
        self.assertEqual(mets_page, METSPage(image=None, sources={}))

    def test_process_single_page_missing_file_location(self):
        processor = METSProcessor(self.root)
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        page = pages[0]
        for pointer in page.findall("mets:fptr", namespaces=processor.NAMESPACES):
            file = files[pointer.get("FILEID")]
            location = file.find("mets:FLocat", namespaces=processor.NAMESPACES)
            file.remove(location)

        with self.assertRaises(ParseError) as context:
            processor.process_single_page(page, files)

        self.assertTrue("Can't find a file location <FLocat/> holding a href attribute for the file" in str(context.exception))

    def test_process_single_page_no_group_name(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        for element in self.root.findall(".//mets:fileGrp", namespaces=processor.NAMESPACES):
            del element.attrib["USE"]

        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        mets_page = processor.process_single_page(pages[0], files)

        # Using the default name "Layer 1"
        self.assertEqual(mets_page, METSPage(image="Kifayat_al-ghulam.pdf_000005.png", sources={"Layer 1": "Kifayat_al-ghulam.pdf_000005.xml"}))

    def test_process_single_page_archive_file_not_found(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        page = pages[0]
        for pointer in page.findall("mets:fptr", namespaces=processor.NAMESPACES):
            file = files[pointer.get("FILEID")]
            location = file.find("mets:FLocat", namespaces=processor.NAMESPACES)
            for attrib in location.attrib.keys():
                if "href" in attrib:
                    location.attrib[attrib] = "not_in_archive.file"

        with self.assertLogs("imports.mets") as mock_log:
            mets_page = processor.process_single_page(page, files)

        self.assertEqual(mock_log.output, [
            'ERROR:imports.mets:File not found in the provided archive: "There is no item named \'not_in_archive.file\' in the archive"',
            'ERROR:imports.mets:File not found in the provided archive: "There is no item named \'not_in_archive.file\' in the archive"',
        ])
        self.assertEqual(mets_page, METSPage(image=None, sources={}))

    @patch("requests.get")
    @patch("imports.mets.METSProcessor.check_is_image")
    def test_process_single_page_remote_file_not_found(self, mock_check_is_image, mock_get):
        mock_get.side_effect = RequestException("Uhoh, something went wrong.")
        mock_check_is_image.side_effect = [(True, False), (False, False)]

        processor = METSProcessor(self.root, mets_base_uri="https://whatever.com")
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        page = pages[0]
        for pointer in page.findall("mets:fptr", namespaces=processor.NAMESPACES):
            file = files[pointer.get("FILEID")]
            location = file.find("mets:FLocat", namespaces=processor.NAMESPACES)
            for attrib in location.attrib.keys():
                if "href" in attrib:
                    location.attrib[attrib] = "https://a-file-that-does-not-exists.com/"

        with self.assertLogs("imports.mets") as mock_log:
            mets_page = processor.process_single_page(page, files)

        self.assertEqual(mock_log.output, [
            'ERROR:imports.mets:File not found on remote URI https://a-file-that-does-not-exists.com/: Uhoh, something went wrong.',
            'ERROR:imports.mets:File not found on remote URI https://a-file-that-does-not-exists.com/: Uhoh, something went wrong.',
        ])
        self.assertEqual(mets_page, METSPage(image=None, sources={}))

    def test_process_single_page_in_archive(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        mets_page = processor.process_single_page(pages[0], files)

        self.assertEqual(mets_page, METSPage(image="Kifayat_al-ghulam.pdf_000005.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000005.xml"}))

    @patch("requests.get")
    @patch("imports.mets.METSProcessor.check_is_image")
    def test_process_single_page_remote_file(self, mock_check_is_image, mock_get):
        mock_get.return_value = Mock(content=b"some content", status_code=200)
        mock_check_is_image.side_effect = [(True, False), (False, False)]

        processor = METSProcessor(self.root, mets_base_uri="https://whatever.com")
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        mets_page = processor.process_single_page(pages[0], files)

        self.assertEqual(mets_page.image.name, "Kifayat_al-ghulam.pdf_000005.png")
        self.assertTrue(isinstance(mets_page.image, io.BytesIO))
        self.assertEqual(mets_page.image.read(), b"some content")

        self.assertEqual(list(mets_page.sources.keys()), ["transcript"])
        self.assertEqual(mets_page.sources["transcript"].name, "Kifayat_al-ghulam.pdf_000005.xml")
        self.assertTrue(isinstance(mets_page.sources["transcript"], io.BytesIO))
        self.assertEqual(mets_page.sources["transcript"].read(), b"some content")

    def test_process_no_file_sec(self):
        root = etree.Element("mets")

        processor = METSProcessor(root)
        with self.assertRaises(ParseError) as context:
            processor.process()

        self.assertTrue("The file section <fileSec/> wasn't found in the METS file." in str(context.exception))

    def test_process_no_struct_map(self):
        root = etree.Element("mets")
        root.append(etree.Element(f"{PFX}fileSec"))

        processor = METSProcessor(root)
        with self.assertRaises(ParseError) as context:
            processor.process()

        self.assertTrue("The structure mapping <structMap/> wasn't found in the METS file." in str(context.exception))

    @patch("imports.mets.METSProcessor.process_single_page")
    def test_process_pages_in_error(self, mock_process_single_page):
        mock_process_single_page.side_effect = Exception("Uhoh, something went wrong.")

        processor = METSProcessor(self.root)
        with self.assertLogs("imports.mets") as mock_log:
            mets_pages = processor.process()

        self.assertEqual(mock_log.output, [
            "ERROR:imports.mets:An exception occurred while processing the page n°1 from the provided METS file: Uhoh, something went wrong.",
            "ERROR:imports.mets:An exception occurred while processing the page n°2 from the provided METS file: Uhoh, something went wrong.",
            "ERROR:imports.mets:An exception occurred while processing the page n°3 from the provided METS file: Uhoh, something went wrong.",
            "ERROR:imports.mets:An exception occurred while processing the page n°4 from the provided METS file: Uhoh, something went wrong.",
        ])
        self.assertListEqual(mets_pages, [])

    def test_process_in_archive(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        mets_pages = processor.process()

        self.assertListEqual(mets_pages, [
            METSPage(image="Kifayat_al-ghulam.pdf_000005.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000005.xml"}),
            METSPage(image="Kifayat_al-ghulam.pdf_000006.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000006.xml"}),
            METSPage(image="Kifayat_al-ghulam.pdf_000007.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000007.xml"}),
            METSPage(image="Kifayat_al-ghulam.pdf_000008.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000008.xml"}),
        ])

    @patch("requests.get")
    @patch("imports.mets.METSProcessor.check_is_image")
    def test_process_remote_file(self, mock_check_is_image, mock_get):
        mock_get.return_value = Mock(content=b"some content", status_code=200)
        mock_check_is_image.side_effect = [(True, False), (False, False)] * 4

        processor = METSProcessor(self.root, mets_base_uri="https://whatever.com")
        mets_pages = processor.process()

        names = [
            "Kifayat_al-ghulam.pdf_000005",
            "Kifayat_al-ghulam.pdf_000006",
            "Kifayat_al-ghulam.pdf_000007",
            "Kifayat_al-ghulam.pdf_000008",
        ]
        for index, mets_page in enumerate(mets_pages):
            self.assertEqual(mets_page.image.name, f"{names[index]}.png")
            self.assertTrue(isinstance(mets_page.image, io.BytesIO))
            self.assertEqual(mets_page.image.read(), b"some content")

            self.assertEqual(list(mets_page.sources.keys()), ["transcript"])
            self.assertEqual(mets_page.sources["transcript"].name, f"{names[index]}.xml")
            self.assertTrue(isinstance(mets_page.sources["transcript"], io.BytesIO))
            self.assertEqual(mets_page.sources["transcript"].read(), b"some content")
