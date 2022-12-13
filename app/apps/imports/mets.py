import io
import logging
import os
import zipfile
from collections import namedtuple
from urllib.parse import urljoin

import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from lxml import html
from PIL import Image

logger = logging.getLogger(__name__)

METSPage = namedtuple('METSPage', ['image', 'sources'], defaults=[None, {}])


class METSProcessor:
    NAMESPACES = {"mets": "http://www.loc.gov/METS/"}

    def __init__(self, mets_xml, archive=None, mets_base_uri=None):
        self.mets_xml = mets_xml
        self.archive = archive
        self.mets_base_uri = mets_base_uri
        self.url_validator = URLValidator()

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

    def handle_pointer_in_archive(self, href, mets_page_image, mets_page_sources, layer_name, layers_count):
        try:
            file = self.retrieve_in_archive(href)
        except KeyError as e:
            logger.error(f"File not found in the provided archive: {e}")
            return mets_page_image, mets_page_sources, layers_count

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

        return mets_page_image, mets_page_sources, layers_count

    def build_remote_uri(self, href):
        # Either the href is a full URI towards an element or we need to compose it using the base URI of the METS file
        try:
            self.url_validator(href)
            return href
        except ValidationError:
            return urljoin(f"{self.mets_base_uri}/", href.lstrip("/"))

    def check_is_image(self, uri, mets_page_image):
        head_resp = requests.head(uri)
        content_type = head_resp.headers["content-type"]

        # Pointing towards an image but we already found one for this METS page, we can skip it
        is_image = content_type in ["image/gif", "image/jpeg", "image/png", "image/tiff"]
        if is_image and mets_page_image:
            return is_image, True

        return is_image, False

    def handle_remote_pointer(self, href, mets_page_image, mets_page_sources, layer_name, layers_count):
        uri = self.build_remote_uri(href)

        is_image, stop = self.check_is_image(uri, mets_page_image)
        if stop:
            return mets_page_image, mets_page_sources, layers_count

        # Downloading the file content
        try:
            get_resp = requests.get(uri)
            get_resp.raise_for_status()
            content = get_resp.content
            file = io.BytesIO(content)
            file.name = os.path.basename(uri)
        except requests.exceptions.RequestException as e:
            logger.error(f"File not found on remote URI {uri}: {e}")
            return mets_page_image, mets_page_sources, layers_count

        if is_image:
            mets_page_image = file
        else:
            # If it's not an image then we can add it as a data source to be loaded
            mets_page_sources[layer_name] = file
            layers_count += 1

        return mets_page_image, mets_page_sources, layers_count

    def process_single_page(self, page, files):
        mets_page_image = None
        mets_page_sources = {}
        layers_count = 1

        file_pointers = self.get_file_pointers(page)
        for file_pointer in file_pointers:
            file = files[file_pointer.get("FILEID")]
            href = self.get_file_location(file)
            layer_name = self.get_file_group_name(file) or f"Layer {layers_count}"

            if self.archive:
                mets_page_image, mets_page_sources, layers_count = self.handle_pointer_in_archive(href, mets_page_image, mets_page_sources, layer_name, layers_count)
            else:
                mets_page_image, mets_page_sources, layers_count = self.handle_remote_pointer(href, mets_page_image, mets_page_sources, layer_name, layers_count)

        return METSPage(image=mets_page_image, sources=mets_page_sources)

    def process(self):
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
