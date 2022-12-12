import io
import os
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree, html

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

        processor = METSProcessor(root, archive=self.archive_path)
        with self.assertRaises(ParseError) as context:
            processor.get_files_from_file_sec()

        self.assertTrue("The file section <fileSec/> wasn't found in the METS file." in str(context.exception))

    def test_get_files_from_file_sec(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
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

        processor = METSProcessor(root, archive=self.archive_path)
        with self.assertRaises(ParseError) as context:
            processor.get_pages_from_struct_map()

        self.assertTrue("The structure mapping <structMap/> wasn't found in the METS file." in str(context.exception))

    def test_get_pages_from_struct_map(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        pages = processor.get_pages_from_struct_map()
        self.assertEqual(len(pages), 4)

        for page in pages:
            self.assertTrue(etree.iselement(page))
            self.assertTrue(page.tag == "{http://www.loc.gov/METS/}div")

    def test_get_file_pointers(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        pages = processor.get_pages_from_struct_map()

        pointers = processor.get_file_pointers(pages[0])
        self.assertEqual(len(pointers), 2)

        for pointer in pointers:
            self.assertTrue(etree.iselement(pointer))
            self.assertTrue(pointer.tag == "{http://www.loc.gov/METS/}fptr")

    def test_get_file_location_no_location(self):
        file = etree.Element(f"{PFX}file")

        processor = METSProcessor(self.root, archive=self.archive_path)
        with self.assertRaises(ParseError) as context:
            processor.get_file_location(file)

        self.assertTrue(f"Can't find a file location <FLocat/> holding a href attribute for the file {str(html.tostring(file))}." in str(context.exception))

    def test_get_file_location_no_href(self):
        file = etree.Element(f"{PFX}file")
        file.append(etree.Element(f"{PFX}FLocat"))

        processor = METSProcessor(self.root, archive=self.archive_path)
        with self.assertRaises(ParseError) as context:
            processor.get_file_location(file)

        self.assertTrue(f"Can't find a file location <FLocat/> holding a href attribute for the file {str(html.tostring(file))}." in str(context.exception))

    def test_get_file_location(self):
        file = etree.Element(f"{PFX}file")
        file.append(etree.Element(f"{PFX}FLocat", href="path/file.txt"))

        processor = METSProcessor(self.root, archive=self.archive_path)
        location = processor.get_file_location(file)

        self.assertEqual(location, "path/file.txt")

    def test_get_file_group_name_not_found(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
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

        processor = METSProcessor(self.root, archive=self.archive_path)
        group_name = processor.get_file_group_name(file)
        self.assertEqual(group_name, "transcription")

    def test_get_file_group_name_on_parent(self):
        file_grp = etree.Element(f"{PFX}filegrp", USE="parent_transcription")
        file = etree.SubElement(file_grp, f"{PFX}file")

        processor = METSProcessor(self.root, archive=self.archive_path)
        group_name = processor.get_file_group_name(file)
        self.assertEqual(group_name, "parent_transcription")

    def test_process_single_page_no_file_pointers(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        page = pages[0]
        for pointer in page.findall("mets:fptr", namespaces=processor.NAMESPACES):
            page.remove(pointer)

        mets_page = processor.process_single_page(page, files)
        self.assertEqual(mets_page, METSPage(image=None, sources={}))

    def test_process_single_page_missing_file_location(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
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

    def test_process_single_page_file_not_found(self):
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

    def test_process_single_page(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        files = processor.get_files_from_file_sec()
        pages = processor.get_pages_from_struct_map()
        mets_page = processor.process_single_page(pages[0], files)

        self.assertEqual(mets_page, METSPage(image="Kifayat_al-ghulam.pdf_000005.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000005.xml"}))

    def test_process_distant_files(self):
        processor = METSProcessor(self.root)
        with self.assertRaises(NotImplementedError):
            processor.process()

    def test_process_no_file_sec(self):
        root = etree.Element("mets")

        processor = METSProcessor(root, archive=self.archive_path)
        with self.assertRaises(ParseError) as context:
            processor.process()

        self.assertTrue("The file section <fileSec/> wasn't found in the METS file." in str(context.exception))

    def test_process_no_struct_map(self):
        root = etree.Element("mets")
        root.append(etree.Element(f"{PFX}fileSec"))

        processor = METSProcessor(root, archive=self.archive_path)
        with self.assertRaises(ParseError) as context:
            processor.process()

        self.assertTrue("The structure mapping <structMap/> wasn't found in the METS file." in str(context.exception))

    @patch("imports.mets.METSProcessor.process_single_page")
    def test_process_pages_in_error(self, mock_process_single_page):
        mock_process_single_page.side_effect = Exception("Uhoh, something went wrong.")

        processor = METSProcessor(self.root, archive=self.archive_path)
        with self.assertLogs("imports.mets") as mock_log:
            mets_pages = processor.process()

        self.assertEqual(mock_log.output, [
            "ERROR:imports.mets:An exception occurred while processing the page n°1 from the provided METS file: Uhoh, something went wrong.",
            "ERROR:imports.mets:An exception occurred while processing the page n°2 from the provided METS file: Uhoh, something went wrong.",
            "ERROR:imports.mets:An exception occurred while processing the page n°3 from the provided METS file: Uhoh, something went wrong.",
            "ERROR:imports.mets:An exception occurred while processing the page n°4 from the provided METS file: Uhoh, something went wrong.",
        ])
        self.assertListEqual(mets_pages, [])

    def test_process(self):
        processor = METSProcessor(self.root, archive=self.archive_path)
        mets_pages = processor.process()

        self.assertListEqual(mets_pages, [
            METSPage(image="Kifayat_al-ghulam.pdf_000005.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000005.xml"}),
            METSPage(image="Kifayat_al-ghulam.pdf_000006.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000006.xml"}),
            METSPage(image="Kifayat_al-ghulam.pdf_000007.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000007.xml"}),
            METSPage(image="Kifayat_al-ghulam.pdf_000008.png", sources={"transcript": "Kifayat_al-ghulam.pdf_000008.xml"}),
        ])
