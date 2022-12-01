import logging
import zipfile
from collections import namedtuple

from lxml import html
from PIL import Image

logger = logging.getLogger(__name__)

METSPage = namedtuple('METSPage', ['image', 'sources'], defaults=[None, {}])


class METSProcessor:
    NAMESPACES = {"mets": "http://www.loc.gov/METS/"}

    def __init__(self, mets_xml, archive=None):
        self.mets_xml = mets_xml
        self.archive = archive

    def retrieve_in_archive(self, filename):
        with zipfile.ZipFile(self.archive) as archive:
            return archive.open(filename)

    def get_files_from_file_sec(self):
        from imports.parsers import ParseError

        file_sec = self.mets_xml.find("mets:fileSec", namespaces=self.NAMESPACES)
        if file_sec is None:
            raise ParseError("The file section <fileSec/> wasn't found in the METS file.")

        files = {}
        for element in file_sec.findall(".//mets:file[@ID]", namespaces=self.NAMESPACES):
            files[element.get("ID")] = element

        return files

    def get_pages_from_struct_map(self):
        from imports.parsers import ParseError

        struct_map = self.mets_xml.find("mets:structMap", namespaces=self.NAMESPACES)
        if struct_map is None:
            raise ParseError("The structure mapping <structMap/> wasn't found in the METS file.")

        pages = []
        for element in struct_map.findall(".//mets:div[@TYPE]", namespaces=self.NAMESPACES):
            if "page" in element.get("TYPE", ""):
                pages.append(element)

        return pages

    def get_file_pointers(self, page):
        file_pointers = []

        for element in page.findall("mets:fptr", namespaces=self.NAMESPACES):
            file_pointers.append(element)

        return file_pointers

    def get_file_location(self, file):
        from imports.parsers import ParseError

        location = file.find("mets:FLocat", namespaces=self.NAMESPACES)
        if location is not None:
            for attrib, value in location.attrib.items():
                if "href" in attrib:
                    return value

        raise ParseError(f"Can't find a file location <FLocat/> holding a href attribute for the file {str(html.tostring(file))}.")

    def get_file_group_name(self, file):
        if file.get("USE"):
            return file.get("USE")

        parent = file.getparent()
        if parent is not None and "filegrp" in parent.tag.lower():
            return parent.get("USE")

    def process_single_page(self, page, files):
        mets_page_image = None
        mets_page_sources = {}
        layers_count = 1

        file_pointers = self.get_file_pointers(page)
        for file_pointer in file_pointers:
            file = files[file_pointer.get("FILEID")]
            href = self.get_file_location(file)
            layer_name = self.get_file_group_name(file) or f"Layer {layers_count}"

            try:
                file = self.retrieve_in_archive(href)
            except KeyError as e:
                logger.error(f"File not found in the provided archive: {e}")
                continue

            try:
                # Testing if the retrieved file is an image
                Image.open(file)
                # We only want to save the first provided image
                if not mets_page_image:
                    mets_page_image = href
            except IOError:
                # If it's not an image then we can add it as a data source to be loaded
                mets_page_sources[layer_name] = href
                layers_count += 1
            finally:
                file.close()

        return METSPage(image=mets_page_image, sources=mets_page_sources)

    def process(self):
        if not self.archive:
            # Retrieve the file from a distant source, this mode isn't supported yet
            raise NotImplementedError

        mets_pages = []
        files = self.get_files_from_file_sec()

        pages = self.get_pages_from_struct_map()
        for index, page in enumerate(pages, start=1):
            try:
                mets_page = self.process_single_page(page, files)
            # Catch any exception so that we don't fail when only one page is in error
            except Exception as e:
                logger.error(f"An exception occurred while processing the page n°{index} from the provided METS file: {e}")
                continue

            mets_pages.append(mets_page)

        return mets_pages
