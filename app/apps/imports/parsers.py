import json
import logging
import os
import re
import time
import uuid
import zipfile
from statistics import mean

import pyvips
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import get_available_image_extensions
from django.db import transaction
from django.forms import ValidationError
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from easy_thumbnails.files import get_thumbnailer
from lxml import etree

from core.models import (
    Block,
    DocumentMetadata,
    DocumentPart,
    DocumentPartMetadata,
    Line,
    LineTranscription,
    Metadata,
    Transcription,
)
from imports.mets import METSProcessor
from users.consumers import send_event
from versioning.models import NoChangeException

logger = logging.getLogger(__name__)
XML_EXTENSIONS = ["xml", "alto"]  # , 'abbyy'
OWN_RISK = "the validity of the data can not be automatically checked, use at your own risks."


class DiskQuotaReachedError(Exception):
    pass


class ParseError(Exception):
    pass


class DownloadError(ParseError):
    pass


class ParserDocument:
    """
    The base class for parsing files to populate a core.Document object
    or/and its ancestors.
    """

    DEFAULT_NAME = None

    def __init__(self, document, file_handler, report, transcription_name=None):
        self.file = file_handler
        self.document = document
        self.report = report
        self.name = transcription_name or self.DEFAULT_NAME

    @property
    def total(self):
        # should return the number of elements returned by parse()
        raise NotImplementedError

    def parse(self, start_at=0, override=False, user=None):
        # iterator over created document parts
        raise NotImplementedError

    @cached_property
    def transcription(self):
        transcription, created = Transcription.objects.get_or_create(
            document=self.document, name=self.name
        )
        return transcription

    def clean(self):
        # remove import file if everything went well and any left over
        # this is only called if the import went to completion.
        pass

    def post_process_image(self, part):
        # generate the card thumbnail right away to show the image card
        if getattr(settings, 'THUMBNAIL_ENABLE', True):
            get_thumbnailer(part.image).get_thumbnail(
                settings.THUMBNAIL_ALIASES[""]["card"]
            )
        send_event("document", part.document.pk, "part:new", {
            "id": part.pk
        })
        part.task(
            "convert",
            user_pk=part.document.owner and part.document.owner.pk or None)


class PdfParser(ParserDocument):
    def __init__(self, document, file_handler, report):
        super().__init__(document, file_handler, report)
        pyvips.voperation.cache_set_max(10)  # 0 = no parallelisation at all; default is 1000

    def validate(self):
        try:
            self.doc = pyvips.Image.pdfload_buffer(self.file.read(), n=-1, access='sequential')
        except pyvips.error.Error as e:
            logger.exception(e)
            raise ParseError(_("Invalid PDF file."))

    @property
    def total(self):
        if 'n-pages' in self.doc.get_fields():
            return self.doc.get('n-pages')
        else:
            return 0

    def parse(self, start_at=0, override=False, user=None):
        assert (
            self.report
        ), "A TaskReport instance should be provided while parsing data."

        buff = self.file.read()
        doc = pyvips.Image.pdfload_buffer(buff, n=-1, access='sequential')
        n_pages = doc.get('n-pages')
        try:
            for page_nb in range(start_at, n_pages):
                # If quotas are enforced, assert that the user still has free disk storage
                if not settings.DISABLE_QUOTAS and not user.has_free_disk_storage():
                    raise DiskQuotaReachedError(
                        _(f"You ran out of disk storage. {n_pages - page_nb} pages were left to import (over {n_pages - start_at})")
                    )

                page = pyvips.Image.pdfload_buffer(buff,
                                                   page=page_nb,
                                                   dpi=300,
                                                   access='sequential')
                pdfname = os.path.basename(self.file.name)
                fname = '%s_page_%d.png' % (pdfname, page_nb + 1)
                try:
                    part = DocumentPart.objects.filter(
                        document=self.document,
                        original_filename=fname
                    )[0]
                except IndexError:
                    # we do not use DoesNotExist because documents could have
                    # duplicate image names at some point.
                    part = DocumentPart(
                        document=self.document,
                        original_filename=fname
                    )

                part.image_file_size = 0
                part.image.save(fname, ContentFile(page.write_to_buffer('.png')))
                part.image_file_size = part.image.size
                part.source = f"pdf//{pdfname}"
                part.workflow_state = DocumentPart.WORKFLOW_STATE_CONVERTED
                part.save()
                self.post_process_image(part)

                yield part
                page_nb = page_nb + 1

        except pyvips.error.Error as e:
            self.report.append(
                _("Parse error in {filename}: {page}: {error}, skipping it.").format(
                    filename=self.file.name, page=page_nb + 1, error=e.args[0]
                ),
                logger_fct=logger.warning,
            )

    def clean(self):
        # if the import went well we are safe to delete the file
        os.remove(os.path.join(settings.MEDIA_ROOT, self.file.path))


class ZipParser(ParserDocument):
    """
    For now only deals with a flat list of ALTO files
    """

    DEFAULT_NAME = _("Zip Import")

    def validate(self):
        try:
            with zipfile.ZipFile(self.file) as zfh:
                if zfh.testzip() is not None:
                    raise ParseError(_("File appears to not be a valid zip."))
                # for i,finfo in enumerate(zfh.infolist()):
                #     with zfh.open(finfo) as zipedfh:
                #         parser = make_parser(self.document, zipedfh)
                #         parser.validate()
        except Exception as e:
            logger.exception(e)
            raise ParseError(_("Zip file appears to be corrupted."))

    @property
    def total(self):
        # TODO: we open the file twice on upload
        with zipfile.ZipFile(self.file) as zfh:
            return len(zfh.infolist())

    def parse(self, start_at=0, override=False, user=None):
        assert (
            self.report
        ), "A TaskReport instance should be provided while parsing data."

        with zipfile.ZipFile(self.file) as zfh:
            total = len(zfh.infolist())
            for index, finfo in enumerate(zfh.infolist()):
                if index < start_at:
                    continue
                with zfh.open(finfo) as zipedfh:
                    try:
                        filename = os.path.basename(zipedfh.name)
                        file_extension = os.path.splitext(filename)[1][1:]
                        # image
                        if file_extension.lower() in get_available_image_extensions():
                            # If quotas are enforced, assert that the user still has free disk storage
                            if not settings.DISABLE_QUOTAS and not user.has_free_disk_storage():
                                raise DiskQuotaReachedError(
                                    _(f"You ran out of disk storage. {total - index} files were left to import (over {total - start_at})")
                                )
                            try:
                                part = DocumentPart.objects.filter(
                                    document=self.document,
                                    original_filename=filename
                                )[0]
                            except IndexError:
                                # we do not use DoesNotExist because documents could have
                                # duplicate image names at some point.
                                part = DocumentPart(
                                    document=self.document,
                                    original_filename=filename
                                )
                            part.image_file_size = 0
                            part.image.save(filename, ContentFile(zipedfh.read()))
                            part.image_file_size = part.image.size
                            part.source = "zip//{0}/{1}".format(
                                os.path.basename(self.file.name),
                                filename
                            )
                            part.workflow_state = DocumentPart.WORKFLOW_STATE_CONVERTED
                            part.save()
                            self.post_process_image(part)

                        # xml
                        elif file_extension in XML_EXTENSIONS:
                            parser = make_parser(self.document, zipedfh,
                                                 name=self.name, report=self.report)

                            for part in parser.parse(override=override, user=user):
                                yield part
                    except IndexError:
                        # no file extension!?
                        pass
                    except ParseError as e:
                        # we let go to try other documents
                        msg = _(
                            "Parse error in {filename}: {xmlfile}: {error}, skipping it."
                        ).format(
                            filename=self.file.name, xmlfile=filename, error=e.args[0]
                        )
                        self.report.append(msg, logger_fct=logger.warning)
                        if user:
                            user.notify(msg, id="import:warning", level="warning")

    def clean(self):
        # if the import went well we are safe to delete the file
        os.remove(os.path.join(settings.MEDIA_ROOT, self.file.path))


class METSBaseParser():
    def parse_image(self, user, total, index, start_at, filename, image, source):
        # If quotas are enforced, assert that the user still has free disk storage
        if not settings.DISABLE_QUOTAS and not user.has_free_disk_storage():
            raise DiskQuotaReachedError(
                _(f"You ran out of disk storage. {total - index} files were left to import (over {total - start_at})")
            )

        try:
            part = DocumentPart.objects.filter(
                document=self.document,
                original_filename=filename
            )[0]
        except IndexError:
            # we do not use DoesNotExist because documents could have
            # duplicate image names at some point.
            part = DocumentPart(
                document=self.document,
                original_filename=filename
            )
        part.image_file_size = 0
        part.image.save(filename, ContentFile(image.read()))
        part.image_file_size = part.image.size
        part.source = source
        part.workflow_state = DocumentPart.WORKFLOW_STATE_CONVERTED
        part.save()
        self.post_process_image(part)

        return part

    def store_document_metadata(self, metadata):
        for md_name, md_value in metadata.items():
            if not md_value:
                continue
            md, created = Metadata.objects.get_or_create(name=md_name)
            DocumentMetadata.objects.get_or_create(document=self.document, key=md, defaults={'value': md_value[:512]})

    def store_part_metadata(self, metadata, part):
        for md_name, md_value in metadata.items():
            if not md_value:
                continue
            md, created = Metadata.objects.get_or_create(name=md_name)
            DocumentPartMetadata.objects.get_or_create(part=part, key=md, defaults={'value': md_value[:512]})


class METSRemoteParser(ParserDocument, METSBaseParser):
    DEFAULT_NAME = _("METS Import")

    def __init__(self, document, file_handler, report, xml_root, mets_base_uri, transcription_name=None):
        self.mets_file_content = xml_root
        self.mets_base_uri = mets_base_uri
        self.mets_pages = []
        super().__init__(document, file_handler, report, transcription_name=transcription_name)

    @property
    def total(self):
        total = 0
        for page in self.mets_pages:
            if page.image:
                total += 1
            if page.sources:
                total += len(page.sources.keys())
        return total

    def validate(self):
        pass

    def parse(self, start_at=0, override=False, user=None):
        assert (
            self.report
        ), "A TaskReport instance should be provided while parsing data."

        # Retrieving all the pages described by the METS file
        try:
            self.mets_pages, metadata = METSProcessor(self.mets_file_content, report=self.report, mets_base_uri=self.mets_base_uri).process()
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"An error occurred during the processing of the remote METS file: {e}")

        self.store_document_metadata(metadata)

        total = self.total
        global_index = 0
        for index, mets_page in enumerate(self.mets_pages):
            metadata_already_stored = False

            if mets_page.image:
                if global_index < start_at:
                    global_index += 1 + len(mets_page.sources.keys())
                    continue

                filename = mets_page.image.name
                part = self.parse_image(user, total, index, start_at, filename,
                                        mets_page.image, self.mets_base_uri)
                # If we have a page with an image + multiple sources, we don't want to
                # store the same metadata multiple times and spam the database for nothing
                if not metadata_already_stored:
                    self.store_part_metadata(mets_page.metadata, part)
                    metadata_already_stored = True

            for index, (layer_name, source) in enumerate(mets_page.sources.items()):
                if global_index < start_at:
                    global_index += 1 + len(mets_page.sources.keys())
                    continue

                filename = source.name

                try:
                    parser = make_parser(self.document, source, name=f"{self.name} | {layer_name}", report=self.report, zip_allowed=False, pdf_allowed=False)
                    # We only want to override for the first imported source if there are multiple ones
                    for part in parser.parse(override=(override and index == 0), user=user):
                        # If we have a page with an image + multiple sources, we don't want to
                        # store the same metadata multiple times and spam the database for nothing
                        if not metadata_already_stored:
                            self.store_part_metadata(mets_page.metadata, part)
                            metadata_already_stored = True

                        yield part
                except (ValueError, ParseError) as e:
                    # We let go to try other sources
                    msg = _(
                        "Parse error in {filename}: {xmlfile}: {error}, skipping it."
                    ).format(filename=self.file.name, xmlfile=filename, error=e.args[0])
                    self.report.append(msg, logger_fct=logger.warning)
                    if user:
                        user.notify(msg, id="import:warning", level="warning")


class METSZipParser(ZipParser, METSBaseParser):
    DEFAULT_NAME = _("METS Import")

    def parse(self, start_at=0, override=False, user=None):
        assert (
            self.report
        ), "A TaskReport instance should be provided while parsing data."

        # Searching for the METS file in the archive
        with zipfile.ZipFile(self.file) as archive:
            total = len(archive.infolist())
            xml_filenames = [filename for filename in archive.namelist() if os.path.splitext(filename)[1][1:] == "xml"]

            mets_file_content = None
            for xml_filename in xml_filenames:
                with archive.open(xml_filename) as ziped_file:
                    try:
                        root = etree.parse(ziped_file).getroot()
                        schemas = root.nsmap.values()
                    except (etree.XMLSyntaxError, KeyError):
                        logger.debug(f"Skipping file {xml_filename} in archive as it isn't a METS file")
                        continue

                    if METSProcessor.NAMESPACES["mets"] in schemas:
                        mets_file_content = root
                        break

        # If we didn't find a METS file in the archive after browsing everything, something is wrong
        if mets_file_content is None:
            raise ParseError(
                "Couldn't find the METS file that should be there to define the archive."
            )

        # Retrieving all the pages described by the METS file
        try:
            mets_pages, metadata = METSProcessor(mets_file_content, report=self.report, archive=self.file).process()
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"An error occurred during the processing of the METS file contained in the archive: {e}")

        self.store_document_metadata(metadata)

        with zipfile.ZipFile(self.file) as archive:
            info_list = [info.filename for info in archive.infolist()]

            for index, mets_page in enumerate(mets_pages):
                metadata_already_stored = False

                if mets_page.image:
                    if info_list.index(mets_page.image) < start_at:
                        continue

                    with archive.open(mets_page.image) as ziped_image:
                        filename = os.path.basename(ziped_image.name)
                        image_source = "mets//{0}/{1}".format(os.path.basename(self.file.name), filename)
                        part = self.parse_image(user, total, index, start_at, filename,
                                                ziped_image, image_source)
                        # If we have a page with an image + multiple sources, we don't want to
                        # store the same metadata multiple times and spam the database for nothing
                        if not metadata_already_stored:
                            self.store_part_metadata(mets_page.metadata, part)
                            metadata_already_stored = True

                for index, (layer_name, source) in enumerate(mets_page.sources.items()):
                    if info_list.index(source) < start_at:
                        continue

                    with archive.open(source) as ziped_source:
                        filename = os.path.basename(ziped_source.name)

                        try:
                            parser = make_parser(self.document, ziped_source, name=f"{self.name} | {layer_name}", report=self.report, zip_allowed=False, pdf_allowed=False)
                            # We only want to override for the first imported source if there are multiple ones
                            for part in parser.parse(override=(override and index == 0), user=user):
                                # If we have a page with an image + multiple sources, we don't want to
                                # store the same metadata multiple times and spam the database for nothing
                                if not metadata_already_stored:
                                    self.store_part_metadata(mets_page.metadata, part)
                                    metadata_already_stored = True

                                yield part
                        except (ValueError, ParseError) as e:
                            # We let go to try other sources
                            msg = _(
                                "Parse error in {filename}: {xmlfile}: {error}, skipping it."
                            ).format(
                                filename=self.file.name,
                                xmlfile=filename,
                                error=e.args[0],
                            )
                            self.report.append(msg, logger_fct=logger.warning)
                            if user:
                                user.notify(msg, id="import:warning", level="warning")

    def clean(self):
        # if the import went well we are safe to delete the file
        os.remove(os.path.join(settings.MEDIA_ROOT, self.file.path))


class XMLParser(ParserDocument):
    ACCEPTED_SCHEMAS = ()

    def __init__(self, document, file_handler, report, transcription_name=None, xml_root=None):
        super().__init__(document,
                         file_handler,
                         transcription_name=transcription_name,
                         report=report)
        if xml_root is not None:
            self.root = xml_root
            try:
                self.schema_location = self.root.xpath(
                    "//*/@xsi:schemaLocation",
                    namespaces={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
                )[0].split(" ")[-1]
            except (etree.XPathEvalError, IndexError) as e:
                message = "Cannot Find Schema location %s, %s" % (e.args[0], OWN_RISK)
                if report:
                    report.append(message)
                else:
                    raise ParseError(message)
        else:
            try:
                self.root = etree.parse(self.file).getroot()
            except (AttributeError, etree.XMLSyntaxError) as e:
                raise ParseError("Invalid XML. %s" % e.args[0])
        # instance attribute storing all line confidences, for computing the average at the end
        # of the import
        self.all_line_confidences = []

    def validate(self):
        if self.schema_location in self.ACCEPTED_SCHEMAS:
            try:
                response = requests.get(self.schema_location)
                content = response.content
                schema_root = etree.XML(content)
            except requests.exceptions.RequestException as e:
                logger.exception(e)
                if self.report:
                    self.report.append("Can't reach validation document %s, %s" % (
                        self.schema_location, OWN_RISK))
            else:
                try:
                    xmlschema = etree.XMLSchema(schema_root)
                    xmlschema.assertValid(self.root)
                except (
                    AttributeError,
                    etree.DocumentInvalid,
                    etree.XMLSyntaxError,
                ) as e:
                    if self.report:
                        self.report.append("Document didn't validate. %s, %s" % (e.args[0], OWN_RISK))
        else:
            if self.report:
                self.report.append("Document Schema %s is not in the accepted escriptorium list. Valid schemas are: %s, %s" %
                                   (self.schema_location, self.ACCEPTED_SCHEMAS, OWN_RISK))

    def get_filename(self, pageTag):
        raise NotImplementedError

    def get_pages(self):
        raise NotImplementedError

    def get_blocks(self, pageTag):
        raise NotImplementedError

    def get_lines(self, blockTag):
        raise NotImplementedError

    def update_block(self, block, blockTag):
        raise NotImplementedError

    def update_line(self, line, lineTag):
        raise NotImplementedError

    def get_avg_confidence(self, lineTag):
        raise NotImplementedError

    def get_transcription_content(self, lineTag):
        raise NotImplementedError

    def make_transcription(self, line, lineTag, content, avg_confidence=None, user=None):
        try:
            # lazily creates the Transcription on the fly if need be cf transcription() property
            lt = LineTranscription.objects.get(
                transcription=self.transcription, line=line
            )
        except LineTranscription.DoesNotExist:
            lt = LineTranscription(
                version_source="import",
                version_author=user and user.username or "",
                transcription=self.transcription,
                line=line,
            )
        else:
            try:
                lt.new_version(author=user and user.username,
                               source='import')  # save current content in history
            except NoChangeException:
                pass
        finally:
            lt.content = content
            if avg_confidence:
                lt.avg_confidence = avg_confidence
            lt.save()

            # update the avg confidence across the whole transcription
            if self.all_line_confidences:
                lt.transcription.avg_confidence = mean(self.all_line_confidences)
            lt.transcription.save()

    def parse(self, start_at=0, override=False, user=None):
        assert (
            self.report
        ), "A TaskReport instance should be provided while parsing data."

        pages = self.get_pages()
        n_pages = len(pages)
        n_blocks = 0
        n_lines = 0

        for pageTag in pages:
            # find the filename to match with existing images
            filename = self.get_filename(pageTag)
            try:
                part = DocumentPart.objects.filter(
                    document=self.document, original_filename=filename
                )[0]
            except IndexError:
                self.report.append(
                    _('No match found for file {} with filename "{}".').format(
                        os.path.basename(self.file.name), filename
                    )
                )
            else:
                # if something fails, revert everything for this document part
                with transaction.atomic():
                    if override:
                        part.lines.all().delete()
                        part.blocks.all().delete()

                    # list to store all computed avg confidences for lines on this document part
                    part_line_confidences = []
                    # store the max average confidence for comparison
                    max_avg_confidence = part.max_avg_confidence

                    blocks = self.get_blocks(pageTag)
                    n_blocks += len(blocks)

                    for block_id, blockTag in blocks:
                        if block_id and not block_id.startswith("eSc_dummyblock_"):
                            try:
                                block = Block.objects.get(document_part=part, external_id=block_id)
                            except Block.DoesNotExist:
                                # not found, create it then
                                block = Block(document_part=part, external_id=block_id)
                            try:
                                self.update_block(block, blockTag)
                            except TypeError:
                                block = None
                            else:
                                try:
                                    block.full_clean()
                                except ValidationError as e:
                                    self.report.append(
                                        _(
                                            "Block in '{filen}' line N°{line} was skipped because: {error}"
                                        ).format(
                                            filen=self.file.name,
                                            line=blockTag.sourceline,
                                            error=e,
                                        )
                                    )
                                else:
                                    block.save()
                        else:
                            block = None

                        lines = self.get_lines(blockTag)
                        n_lines += len(lines)

                        for line_id, lineTag in lines:
                            if line_id:
                                try:
                                    line = Line.objects.get(document_part=part, external_id=line_id)
                                except Line.DoesNotExist:
                                    line = None
                            else:
                                line = None

                            if line is None:
                                # not found, create it then
                                line = Line(document_part=part, block=block, external_id=line_id)

                            self.update_line(line, lineTag)
                            try:
                                line.full_clean()
                            except ValidationError as e:
                                self.report.append(
                                    _(
                                        "Line in '{filen}' line N°{line} (id: {lineid}) was skipped because: {error}"
                                    ).format(
                                        filen=self.file.name,
                                        line=blockTag.sourceline,
                                        lineid=line_id,
                                        error=e,
                                    )
                                )
                            else:
                                line.save()

                            # needs to be done after line is created!
                            tc = self.get_transcription_content(lineTag)
                            ac = self.get_avg_confidence(lineTag)
                            if ac:
                                self.all_line_confidences.append(ac)
                                part_line_confidences.append(ac)
                            if tc:
                                self.make_transcription(line, lineTag, tc, avg_confidence=ac, user=user)
                    if part_line_confidences:
                        # if applicable, store max avg confidence / best transcription on document part
                        part_avg_confidence = mean(part_line_confidences)
                        if not max_avg_confidence or (max_avg_confidence and part_avg_confidence > max_avg_confidence):
                            part.max_avg_confidence = part_avg_confidence

                # TODO: store glyphs too
                logger.info("Uncompressed and parsed %s (%i page(s), %i block(s), %i line(s))" % (self.file.name, n_pages, n_blocks, n_lines))
                part.calculate_progress()
                yield part


class AltoParser(XMLParser):
    DEFAULT_NAME = _("Default ALTO Import")
    escriptorium_alto = "https://gitlab.inria.fr/scripta/escriptorium/-/raw/develop/app/escriptorium/static/alto-4-1-baselines.xsd"

    ACCEPTED_SCHEMAS = (
        "http://www.loc.gov/standards/alto/v4/alto.xsd",
        "http://www.loc.gov/standards/alto/v4/alto-4-0.xsd",
        "http://www.loc.gov/standards/alto/v4/alto-4-1.xsd",
        "http://www.loc.gov/standards/alto/v4/alto-4-2.xsd",
        escriptorium_alto
    )

    @property
    def total(self):
        # An alto file always describes 1 'document part'
        return 1

    def get_filename(self, pageTag):
        try:
            filename = self.root.find(
                "Description/sourceImageInformation/fileName", self.root.nsmap
            ).text
        except (IndexError, AttributeError):
            raise ParseError("""
The ALTO file should contain a Description/sourceImageInformation/fileName tag for matching.
            """)
        else:
            return filename

    def get_pages(self):
        return self.root.findall("Layout/Page", self.root.nsmap)

    def get_blocks(self, pageTag):
        return [
            (b.get("ID"), b)
            for b in pageTag.findall("PrintSpace//TextBlock", self.root.nsmap)
        ]

    def get_lines(self, blockTag):
        return [(line.get("ID"), line) for line in blockTag.findall("TextLine", self.root.nsmap)]

    def update_block(self, block, blockTag):
        polygon = blockTag.find("Shape/Polygon", self.root.nsmap)
        if polygon is not None:
            try:
                coords = tuple(map(float, polygon.get("POINTS").strip().split(" ")))
                block.box = tuple(zip(coords[::2], coords[1::2]))
            except ValueError:
                logger.warning("Invalid polygon %s" % polygon)
        else:
            x = int(float(blockTag.get("HPOS")))
            y = int(float(blockTag.get("VPOS")))
            w = int(float(blockTag.get("WIDTH")))
            h = int(float(blockTag.get("HEIGHT")))
            block.box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

        try:
            tag = blockTag.get("TAGREFS").strip().split(" ")[0]
            type_ = self.root.find("./Tags/*[@ID='" + tag + "']", self.root.nsmap).get("LABEL")
        except (IndexError, AttributeError):
            # Index to catch empty tagrefs, Attribute to catch no tagrefs or invalid
            type_ = None

        if type_:
            typo, created = self.document.valid_block_types.get_or_create(name=type_)
            block.typology = typo
            if created:
                self.report.append(
                    _("Block type {0} was automatically added to the ontology").format(typo.name)
                )

    def update_line(self, line, lineTag):
        baseline = lineTag.get("BASELINE")

        if baseline is not None:
            # sometimes baseline is just a single number,
            # an offset maybe it's not super clear
            try:
                int(baseline)
            except ValueError:
                # it's an expected polygon
                try:
                    coords = tuple(map(float, baseline.strip().split(" ")))
                    line.baseline = tuple(zip(coords[::2], coords[1::2]))
                except ValueError:
                    self.report.append(
                        _("Invalid baseline {baseline} in {filen} line {linen}").format(
                            baseline=baseline,
                            filen=self.file.name,
                            linen=lineTag.sourceline,
                        ),
                        logger_fct=logger.warning,
                    )
        else:
            # extract it from <String>s then
            strings = lineTag.findall("String", self.root.nsmap)
            last_segment = strings[-1]
            line.baseline = [(int(float(e.get('HPOS'))), int(float(e.get('VPOS')))) for e in strings]
            line.baseline.append((int(float(last_segment.get('HPOS'))) + int(float(last_segment.get('WIDTH'))),
                                  int(float(last_segment.get('VPOS')))))

        polygon = lineTag.find("Shape/Polygon", self.root.nsmap)
        if polygon is not None:
            try:
                coords = tuple(map(float, polygon.get("POINTS").strip().split(" ")))
                line.mask = tuple(zip(coords[::2], coords[1::2]))
            except ValueError:
                self.report.append(
                    "Invalid polygon %s in %s line %d"
                    % (polygon, self.file.name, lineTag.sourceline),
                    logger_fct=logger.warning,
                )
        else:
            line.box = [
                int(float(lineTag.get("HPOS"))),
                int(float(lineTag.get("VPOS"))),
                int(float(lineTag.get("HPOS"))) + int(float(lineTag.get("WIDTH"))),
                int(float(lineTag.get("VPOS"))) + int(float(lineTag.get("HEIGHT"))),
            ]

        try:
            tag = lineTag.get("TAGREFS").strip().split(" ")[0]
            type_ = self.root.find("./Tags/*[@ID='" + tag + "']", self.root.nsmap).get("LABEL")
        except (IndexError, AttributeError):
            type_ = None

        if type_:
            typo, created = self.document.valid_line_types.get_or_create(name=type_)
            line.typology = typo
            if created:
                self.report.append(
                    _("Line type {0} was automatically added to the ontology").format(typo.name)
                )

    def get_transcription_content(self, lineTag):
        return " ".join(
            [e.get("CONTENT") for e in lineTag.findall("String", self.root.nsmap)]
        )

    def get_avg_confidence(self, lineTag):
        # WC attribute (a float between 0.0 and 1.0) is used for confidence
        confidences = [float(e.get("WC")) for e in lineTag.findall("String", self.root.nsmap) if e.get("WC")]
        return mean(confidences) if confidences else None


class PagexmlParser(XMLParser):
    DEFAULT_NAME = _("Default PAGE Import")
    ACCEPTED_SCHEMAS = (
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2016-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd",
    )

    @property
    def total(self):
        # PAGE file can contain multiple parts
        if not self.root:
            self.root = etree.parse(self.file).getroot()
        return len(self.root.findall("Page", self.root.nsmap))

    def get_filename(self, pageTag):
        try:
            filename = pageTag.get("imageFilename")
        except (IndexError, AttributeError):
            raise ParseError("""
The PAGE file should contain an attribute imageFilename in Page tag for matching.
            """)
        else:
            return filename

    def get_pages(self):
        return self.root.findall("Page", self.root.nsmap)

    def get_blocks(self, pageTag):
        return [
            (b.get("id"), b) for b in pageTag.findall("TextRegion", self.root.nsmap)
        ]

    def get_lines(self, blockTag):
        return [(line.get("id"), line) for line in blockTag.findall("TextLine", self.root.nsmap)]

    def update_block(self, block, blockTag):
        coords = blockTag.find("Coords", self.root.nsmap).get("points")
        #  for PAGE file a box is multiple points x1,y1 x2,y2 x3,y3 ...
        block.box = [list(map(lambda x: int(float(x)), pt.split(","))) for pt in coords.strip().split(" ")]

        type_ = blockTag.get("type")
        if not type_:
            custom = blockTag.get("custom")
            if custom:
                match = re.search(r'structure\s?{.*?type:\s?(.+);', custom)
                if match:
                    type_ = match.groups()[0]

        if type_:
            typo, created = self.document.valid_block_types.get_or_create(name=type_)
            block.typology = typo
            if created:
                self.report.append(
                    _("Block type {0} was automatically added to the ontology").format(typo.name)
                )

    def update_line(self, line, lineTag):
        try:
            baseline = lineTag.find("Baseline", self.root.nsmap)
            if baseline is not None:
                line.baseline = self.clean_coords(baseline)
            else:
                self.report.append(
                    _(
                        "Line without baseline in {filen} line #{linen}, very likely that it will not be usable!"
                    ).format(filen=self.file.name, linen=lineTag.sourceline)
                )
        except ParseError:
            #  to check if the baseline is good
            line.baseline = None

        try:
            polygon = lineTag.find("Coords", self.root.nsmap)
            if polygon is not None:
                line.mask = self.clean_coords(polygon)
        except ParseError:
            line.mask = None

        type_ = lineTag.get("type")
        if not type_:
            custom = lineTag.get("custom")
            if custom:
                match = re.search(r'structure\s?{.*?type:\s?(.+);', custom)
                if match:
                    type_ = match.groups()[0]

        if type_:
            typo, created = self.document.valid_line_types.get_or_create(name=type_)
            line.typology = typo
            if created:
                self.report.append(
                    _("Line type {0} was automatically added to the ontology").format(typo.name)
                )

    def clean_coords(self, coordTag):
        try:
            return [
                list(map(int, pt.split(",")))
                for pt in coordTag.get("points").strip().split(" ")
            ]
        except (AttributeError, ValueError):
            msg = _("Invalid coordinates for {tag} in {filen} line {line}").format(
                tag=coordTag.tag, filen=self.file.name, line=coordTag.sourceline
            )
            self.report.append(msg)
            raise ParseError(msg)

    def get_transcription_content(self, lineTag):
        # PAGE XML can have content for each word inside a word tag or the whole line in textline tag
        words = lineTag.findall("Word", self.root.nsmap)
        if len(words) > 0:
            return " ".join([
                e.text if e.text is not None else ""
                for e in lineTag.findall("Word/TextEquiv/Unicode", self.root.nsmap)
            ])
        else:
            return " ".join(
                [
                    e.text if e.text is not None else ""
                    for e in lineTag.findall("TextEquiv/Unicode", self.root.nsmap)
                ]
            )

    def get_avg_confidence(self, lineTag):
        # PAGE XML can have content for each word inside a word tag or the whole line in textline tag
        words = lineTag.findall("Word", self.root.nsmap)
        # get @conf attribute from TextEquiv if present
        if len(words) > 0:
            confidences = [float(e.get("@conf")) for e in lineTag.findall("Word/TextEquiv", self.root.nsmap) if e.get("@conf")]
        else:
            confidences = [float(e.get("@conf")) for e in lineTag.findall("TextEquiv", self.root.nsmap) if e.get("@conf")]
        return mean(confidences) if confidences else None


class IIIFManifestParser(ParserDocument):
    @cached_property
    def manifest(self):
        try:
            return json.loads(self.file.read())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ParseError(_("Couldn't decode invalid manifest ({error})").format(error=e))

    @cached_property
    def canvases(self):
        try:
            return self.manifest["sequences"][0]["canvases"]
        except (KeyError, IndexError):
            return []

    def validate(self):
        if len(self.canvases) < 1:
            raise ParseError(_("Empty or invalid manifest, no images found."))

    @property
    def total(self):
        return len(self.canvases)

    @staticmethod
    def get_image(url: str, retry_limit: int = 4) -> requests.Response:
        """Retrieve a iiif image from a iiif server

        This method will retry on certain 5XX errors, network and timeout.
        It will only retry a fixed number of times (default 3),
        and it backs off a little more on each retry. Failure to retrieve
        the image within the retry limit will result in a DownloadError
        being raised. All other unsuccessful requests will raise a
        DownloadError as well.
        """

        current_retry = 0
        while current_retry < retry_limit:
            current_retry = current_retry + 1
            time.sleep(0.1 * current_retry)  # avoid being throttled; add a little backoff
            try:
                response = requests.get(url, stream=True, verify=False, timeout=10)
                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as http_error:
                # retry on transient 5XX errors, but keep a record of the retry count
                if http_error.response.status_code in [500, 502, 503, 504, 507, 508]:
                    continue

                if http_error.response.status_code == 429:
                    # the server might tell us when we are free to go, if not let's wait 1s
                    sleep_time = http_error.response.headers.get('Retry-After', 1)
                    time.sleep(sleep_time)
                    continue

                # We probably got a 4XX error, but whatever it is just raise it
                raise DownloadError(http_error)

            except requests.exceptions.ConnectionError:
                # network error, retry
                continue

            except requests.exceptions.Timeout:
                # timeout, retry
                continue

        # Max retries has been exceeded
        raise DownloadError(f"After {current_retry} tries, the server still errors out loading"
                            f": {url}")

    def parse(self, start_at=0, override=False, user=None):
        assert (
            self.report
        ), "A TaskReport instance should be provided while parsing data."

        try:
            for metadata in self.manifest["metadata"]:
                if metadata["value"]:
                    name = str(metadata["label"])[:128]
                    md, created = Metadata.objects.get_or_create(name=name)
                    DocumentMetadata.objects.get_or_create(
                        document=self.document, key=md, value=str(metadata["value"])[:512]
                    )
        except KeyError:
            pass

        total = len(self.canvases)
        for i, canvas in enumerate(self.canvases):
            if i < start_at:
                continue

            # If quotas are enforced, assert that the user still has free disk storage
            if not settings.DISABLE_QUOTAS and not user.has_free_disk_storage():
                raise DiskQuotaReachedError(
                    _(f"You ran out of disk storage. {total - i} canvases were left to import (over {total - start_at})")
                )

            try:
                resource = canvas["images"][0]["resource"]
                uri_template = "{image}/{region}/{size}/{rotation}/{quality}.{format}"
                url = uri_template.format(
                    image=resource["service"]["@id"],
                    region="full",
                    size=getattr(settings, "IIIF_IMPORT_QUALITY", "full"),
                    rotation=0,
                    quality="default",
                    format="jpg",
                )  # we could gain some time by fetching png, but it's not implemented everywhere.
                # TODO, we should probably grab the iiif image manifest, it will tell
                # us important things about the supported file types and the available sizing.
                r = self.get_image(url)

                try:
                    part = DocumentPart.objects.filter(
                        document=self.document,
                        source=url)[0]
                except IndexError:
                    # we do not use DoesNotExist because documents could have
                    # duplicate image names at some point.
                    part = DocumentPart(
                        document=self.document,
                        source=url)
                if "label" in resource:
                    part.name = resource["label"]
                # iiif file names are always default.jpg or close to
                name = "%d_%s_%s" % (i, uuid.uuid4().hex[:5], url.split("/")[-1])
                part.original_filename = name
                part.image_file_size = 0
                part.image.save(name, ContentFile(r.content), save=False)
                part.image_file_size = part.image.size
                part.save()
                self.post_process_image(part)

                yield part
                time.sleep(0.1)  # avoid being throttled

            except (KeyError, IndexError, DownloadError) as e:
                self.report.append(
                    _("Error while fetching {filename}: {error}").format(
                        filename=name, error=e
                    )
                )
                if isinstance(e, DownloadError):
                    error_msg = f"Could not download image: {url}"
                    user.notify(error_msg, level="warning", id="import:warning")
                    self.report.append(error_msg)


class TranskribusPageXmlParser(PagexmlParser):
    """
    A PAGE XML Parser for documents exported from Transkribus to handle data
    """

    # def validate(self):
    #     warnings.warn(
    #         "Validation is skipped for Transkribus Files but coordinates will be corrected",
    #         SyntaxWarning,
    #         2,
    #     )

    def clean_coords(self, coordTag):
        try:
            return [
                list(map(lambda x: 0 if float(x) < 0 else float(x), pt.split(",")))
                for pt in coordTag.get("points").strip().split(" ")
            ]
        except (AttributeError, ValueError):
            msg = _("Invalid coordinates for {tag} in {filen} line {line}").format(
                tag=coordTag.tag, filen=self.file.name, line=coordTag.sourceline
            )
            self.report.append(msg)
            raise ParseError(msg)


def make_parser(document, file_handler, name=None, report=None, zip_allowed=True, pdf_allowed=True, mets_describer=False, mets_base_uri=None):
    # TODO: not great to rely on file name extension
    ext = os.path.splitext(file_handler.name)[1][1:]
    if ext in XML_EXTENSIONS:
        try:
            root = etree.parse(file_handler).getroot()
        except etree.XMLSyntaxError as e:
            raise ParseError(e.msg)
        try:
            schema = root.nsmap[None]
            schemas = root.nsmap.values()
        except KeyError:
            raise ParseError(
                "Couldn't determine xml schema, xmlns attribute missing on root element."
            )
        # if 'abbyy' in schema:  # Not super robust
        #     return AbbyyParser(root, name=name)
        if "alto" in schema.lower():
            return AltoParser(
                document, file_handler, report, transcription_name=name, xml_root=root
            )
        elif "PAGE" in schema:
            if b"Transkribus" in etree.tostring(root):
                return TranskribusPageXmlParser(
                    document, file_handler, report, transcription_name=name, xml_root=root
                )
            else:
                return PagexmlParser(
                    document, file_handler, report, transcription_name=name, xml_root=root
                )
        elif METSProcessor.NAMESPACES["mets"] in schemas:
            return METSRemoteParser(document, file_handler, report, root, mets_base_uri, transcription_name=name)

        else:
            raise ParseError(
                "Couldn't determine xml schema, check the content of the root tag."
            )
    elif ext == "json":
        return IIIFManifestParser(document, file_handler, report)
    elif zip_allowed and ext == "zip":
        if mets_describer:
            return METSZipParser(document, file_handler, report, transcription_name=name)
        else:
            return ZipParser(document, file_handler, report, transcription_name=name)
    elif pdf_allowed and ext == "pdf":
        return PdfParser(document, file_handler, report)
    else:
        raise ValueError(
            "Invalid extension for the file to be parsed %s." % file_handler.name
        )
