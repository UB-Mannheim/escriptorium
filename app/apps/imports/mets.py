import io
import logging
import os
import zipfile
from collections import namedtuple
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from lxml import html
from PIL import Image

logger = logging.getLogger(__name__)

DOCUMENT_METADATA_MAPPING = {
    "ID": "mets-header/id",
    "ADMID": "mets-header/adm-id",
    "CREATEDATE": "mets-header/created",
    "LASTMODDATE": "mets-header/last-modified",
    "RECORDSTATUS": "mets-header/status",
}

PAGE_METADATA_MAPPING = {
    "mods:part/mods:extent/mods:start": "mods/page-index",
    "mods:relatedItem/mods:physicalDescription/mods:form": "mods/item-physical-form",
    'mods:relatedItem/mods:identifier[@type="reel number"]': "mods/item-reel-number",
    'mods:relatedItem/mods:identifier[@type="reel sequence number"]': "mods/item-reel-sequence-number",
    "mods:relatedItem/mods:location/mods:physicalLocation": "mods/item-physical-location",
    'mods:note[@type="agencyResponsibleForReproduction"]': "mods/agency-responsible-for-reproduction",
    'mods:note[@type="noteAboutReproduction"]': "mods/note-about-reproduction",
}

# For consistency, we use mimetypes for both the remote and the archive parsings
SUPPORTED_IMAGE_MIMETYPES = ["image/gif", "image/jpeg", "image/png", "image/jp2"]

METSPage = namedtuple('METSPage', ['image', 'sources', 'metadata'], defaults=[None, {}, {}])


class METSProcessor:
    NAMESPACES = {"mets": "http://www.loc.gov/METS/", "mods": "http://www.loc.gov/mods/v3"}

    def __init__(self, mets_xml, report, archive=None, mets_base_uri=None):
        self.mets_xml = mets_xml
        self.report = report
        self.archive = archive
        self.mets_base_uri = mets_base_uri
        self.url_validator = URLValidator()

    def retrieve_in_archive(self, filename):
        with zipfile.ZipFile(self.archive) as archive:
            return archive.open(filename)

    def get_document_metadata(self):
        metadata = {}

        mets_header = self.mets_xml.find("mets:metsHdr", namespaces=self.NAMESPACES)
        if mets_header is None:
            return metadata

        for mets_key, db_key in DOCUMENT_METADATA_MAPPING.items():
            value = mets_header.get(mets_key)
            if value:
                metadata[db_key] = value

        # Parse optional <agent/> metadata
        agents = mets_header.findall("mets:agent", namespaces=self.NAMESPACES)
        for agent in agents:
            name = agent.find("mets:name", namespaces=self.NAMESPACES)
            if name is None:
                continue

            db_key = "mets-header/agent"
            if agent.get("ID"):
                db_key += f'-id-{agent.get("ID")}'
            if agent.get("ROLE"):
                db_key += f'-role-{agent.get("ROLE")}'
            if agent.get("TYPE"):
                db_key += f'-type-{agent.get("TYPE")}'

            metadata[db_key] = name.text

        return metadata

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

        struct_map = (self.mets_xml.find("mets:structMap[@TYPE='PHYSICAL']", namespaces=self.NAMESPACES)
                      or self.mets_xml.find("mets:structMap[@TYPE='physical']", namespaces=self.NAMESPACES))

        if struct_map is None:
            raise ParseError("The physical structure mapping <structMap/> wasn't found in the METS file.")

        pages = []
        for element in struct_map.findall(".//mets:div[@TYPE]", namespaces=self.NAMESPACES):
            if "page" in element.get("TYPE", ""):
                pages.append(element)

        return pages

    def get_page_metadata(self, page):
        metadata = {}

        page_dmd_id = page.get("DMDID")
        if not page_dmd_id:
            return metadata

        mods_sec = self.mets_xml.find(f'mets:dmdSec[@ID="{page_dmd_id}"]/mets:mdWrap/mets:xmlData/mods:mods', namespaces=self.NAMESPACES)
        if mods_sec is None:
            return metadata

        for mets_path, db_key in PAGE_METADATA_MAPPING.items():
            found = mods_sec.xpath(mets_path, namespaces=self.NAMESPACES)
            if not found:
                continue

            metadata[db_key] = found[0].text

        return metadata

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
            self.report.append(f"File not found in the provided archive: {e}", logger_fct=logger.error)
            return mets_page_image, mets_page_sources, layers_count

        try:
            # Testing if the retrieved file is an image
            image = Image.open(file)
            # We only want to save the first provided image
            if not mets_page_image and Image.MIME[image.format] in SUPPORTED_IMAGE_MIMETYPES:
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

    def check_is_image(self, uri):
        head_resp = requests.head(uri)
        content_type = head_resp.headers["content-type"]
        return content_type.startswith("image/"), content_type

    def handle_remote_pointer(self, href, mets_page_image, mets_page_sources, layer_name, layers_count):
        uri = self.build_remote_uri(href)

        domain = urlparse(uri).netloc
        if '*' not in settings.IMPORT_ALLOWED_DOMAINS and domain not in settings.IMPORT_ALLOWED_DOMAINS:
            self.report.append(f'The domain of the file URI is not allowed during import. Please contact an administrator to add the following domain to the list: "{domain}".', logger_fct=logger.error)
            return mets_page_image, mets_page_sources, layers_count

        is_image, content_type = self.check_is_image(uri)
        # Pointing towards an image but we already found one for this METS page or its format isn't supported, we can skip it
        if is_image and (mets_page_image or content_type not in SUPPORTED_IMAGE_MIMETYPES):
            return mets_page_image, mets_page_sources, layers_count

        # Downloading the file content
        try:
            get_resp = requests.get(uri)
            get_resp.raise_for_status()
            content = get_resp.content
            file = io.BytesIO(content)
            file.name = os.path.basename(uri)
            if file.name == 'default.jpg':
                # Images from IIIF image servers require special handling.
                # {scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
                scheme_server_prefix, identifier, region, size, rotation, quality_format = uri.rsplit('/', 5)
                file.name = identifier + '.jpg'
        except requests.exceptions.RequestException as e:
            self.report.append(f"File not found on remote URI {uri}: {e}", logger_fct=logger.error)
            return mets_page_image, mets_page_sources, layers_count

        if is_image:
            mets_page_image = file
        else:
            # If it's not an image then we can add it as a data source to be loaded
            mets_page_sources[layer_name] = file
            layers_count += 1

        return mets_page_image, mets_page_sources, layers_count

    def process_single_page(self, page, files):
        try:
            metadata = self.get_page_metadata(page)
        except Exception as e:
            self.report.append(f"An exception occurred while retrieving metadata on the page: {e}", logger_fct=logger.warning)
            metadata = {}

        mets_page_image = None
        mets_page_sources = {}
        layers_count = 1

        file_pointers = self.get_file_pointers(page)
        for file_pointer in file_pointers:
            file = files[file_pointer.get("FILEID")]
            href = self.get_file_location(file)
            layer_name = self.get_file_group_name(file) or f"Layer {layers_count}"
            # Skip files in some file groups
            if layer_name in ['DOWNLOAD', 'FULLTEXT', 'MAX', 'MEDIUM', 'MIN', 'THUMBS']:
                continue

            if self.archive:
                mets_page_image, mets_page_sources, layers_count = self.handle_pointer_in_archive(href, mets_page_image, mets_page_sources, layer_name, layers_count)
            else:
                mets_page_image, mets_page_sources, layers_count = self.handle_remote_pointer(href, mets_page_image, mets_page_sources, layer_name, layers_count)

        return METSPage(image=mets_page_image, sources=mets_page_sources, metadata=metadata)

    def process(self):
        try:
            metadata = self.get_document_metadata()
        except Exception as e:
            self.report.append(f"An exception occurred while retrieving metadata from the METS header: {e}", logger_fct=logger.warning)
            metadata = {}

        mets_pages = []
        files = self.get_files_from_file_sec()

        pages = self.get_pages_from_struct_map()
        for index, page in enumerate(pages, start=1):
            self.report.append(f"Processing the page n°{index} from the provided METS file", logger_fct=logger.info)
            try:
                mets_page = self.process_single_page(page, files)
            # Catch any exception so that we don't fail when only one page is in error
            except Exception as e:
                self.report.append(f"An exception occurred while processing the page: {e}", logger_fct=logger.error)
                continue

            mets_pages.append(mets_page)

        return mets_pages, metadata
