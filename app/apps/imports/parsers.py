import json
import logging
import os.path
import re
import requests
import time
import uuid
import zipfile
import pyvips
from lxml import etree

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import get_available_image_extensions
from django.db import transaction
from django.forms import ValidationError
from django.utils.translation import gettext as _
from django.utils.functional import cached_property

from core.models import (Block,
                         Line,
                         Transcription,
                         LineTranscription,
                         DocumentPart,
                         Metadata,
                         DocumentMetadata)
from versioning.models import NoChangeException

logger = logging.getLogger(__name__)
XML_EXTENSIONS = ["xml", "alto"]  # , 'abbyy'
OWN_RISK = "the validity of the data can not be automaatically checked, use at your own risks."


class ParseError(Exception):
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

    def parse(self, start_index=0, override=False, user=None):
        # iterator over created document parts
        raise NotImplementedError

    @cached_property
    def transcription(self):
        transcription, created = Transcription.objects.get_or_create(
            document=self.document, name=self.name
        )
        return transcription


class PdfParser(ParserDocument):
    def validate(self):
        try:
            self.doc = pyvips.Image.new_from_buffer(self.file.read(), "",
                                                    dpi=300, n=-1,
                                                    access="sequential")
        except pyvips.error.Error as e:
            logger.exception(e)
            raise ParseError(_("Invalid pdf file."))

    @property
    def total(self):
        if 'n-pages' in self.doc.get_fields():
            return self.doc.get('n-pages')
        else:
            return 0

    def parse(self, start_at=0, override=False, user=None):
        buff = self.file.read()
        doc = pyvips.Image.new_from_buffer(buff, "",
                                           dpi=300, n=-1,
                                           access="sequential")
        n_pages = doc.get('n-pages')
        try:
            for page_nb in range(start_at, n_pages):
                page = pyvips.Image.new_from_buffer(buff, "", dpi=300,
                                                    access="sequential",
                                                    page=page_nb)
                part = DocumentPart(document=self.document)
                part.image.save('%s_page_%d.png' % (self.file.name, page_nb+1),
                                ContentFile(page.write_to_buffer('.png')))
                part.save()
                yield part
                page_nb = page_nb + 1
        except pyvips.error.Error as e:
            msg = _("Parse error in {filename}: {error}, skipping it.").format(
                filename=self.file.name, error=e.args[0]
            )
            logger.warning(msg)
            if self.report:
                self.report.append(msg)


class ZipParser(ParserDocument):
    """
    For now only deals with a flat list of Alto files
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
        with zipfile.ZipFile(self.file) as zfh:
            for index, finfo in enumerate(zfh.infolist()):
                if index < start_at:
                    continue
                with zfh.open(finfo) as zipedfh:
                    try:
                        file_extension = os.path.splitext(zipedfh.name)[1][1:]
                        # image
                        if file_extension in get_available_image_extensions():
                            try:
                                part = DocumentPart.objects.filter(
                                    document=self.document,
                                    original_filename=zipedfh.name
                                )[0]
                            except IndexError:
                                part = DocumentPart(
                                    document=self.document,
                                    original_filename=zipedfh.name
                                )
                            part.image.save(zipedfh.name, ContentFile(zipedfh.read()))
                            part.save()

                        # xml
                        elif file_extension in XML_EXTENSIONS:
                            parser = make_parser(self.document, zipedfh,
                                                 name=self.name, report=self.report)

                            for part in parser.parse(override=override):
                                yield part
                    except IndexError:
                        # no file extension!?
                        pass
                    except ParseError as e:
                        # we let go to try other documents
                        msg = _("Parse error in {filename}: {error}, skipping it.").format(
                            filename=self.file.name, error=e.args[0]
                        )
                        logger.warning(msg)
                        if self.report:
                            self.report.append(msg)
                        if user:
                            user.notify(msg, id="import:warning", level="warning")


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
                self.report.append("Document Schema %s is not in the accepted escriptiium list. Valid schemas are: %s, %s" %
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

    def make_transcription(self, line, lineTag, content, user=None):
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
            lt.save()

    def parse(self, start_at=0, override=False, user=None):
        for pageTag in self.get_pages():
            # find the filename to match with existing images
            filename = self.get_filename(pageTag)
            try:
                part = DocumentPart.objects.filter(
                    document=self.document, original_filename=filename
                )[0]
            except IndexError:
                # TODO: check for the image in the zip
                if self.report:
                    self.report.append(
                        _("No match found for file {} with filename \"{}\".").format(
                            self.file.name, filename
                        )
                    )
            else:
                # if something fails, revert everything for this document part
                with transaction.atomic():
                    if override:
                        part.lines.all().delete()
                        part.blocks.all().delete()

                    for block_id, blockTag in self.get_blocks(pageTag):
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
                                    if self.report:
                                        self.report.append(
                                            "Block in '{filen}' line N°{line} was skipped because: {error}".format(
                                                filen=self.file.name, line=blockTag.sourceline, error=e))
                                else:
                                    block.save()
                        else:
                            block = None

                        for line_id, lineTag in self.get_lines(blockTag):
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
                                if self.report:
                                    self.report.append("Line in '{filen}' line N°{line} was skipped because: {error}".format(
                                        filen=self.file.name, line=blockTag.sourceline, error=e))
                            else:
                                line.save()

                            # needs to be done after line is created!
                            tc = self.get_transcription_content(lineTag)
                            if tc:
                                self.make_transcription(line, lineTag, tc, user=user)

                # TODO: store glyphs too
                logger.info("Uncompressed and parsed %s" % self.file.name)
                part.calculate_progress()
                yield part


class AltoParser(XMLParser):
    DEFAULT_NAME = _("Default Alto Import")
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
        except (IndexError, AttributeError) as e:
            raise ParseError("""
The alto file should contain a Description/sourceImageInformation/fileName tag for matching.
            """)
        else:
            return filename

    def get_pages(self):
        return self.root.findall("Layout/Page", self.root.nsmap)

    def get_blocks(self, pageTag):
        return [
            (b.get("ID"), b)
            for b in pageTag.findall("PrintSpace/TextBlock", self.root.nsmap)
        ]

    def get_lines(self, blockTag):
        return [(l.get("ID"), l) for l in blockTag.findall("TextLine", self.root.nsmap)]

    def update_block(self, block, blockTag):
        polygon = blockTag.find("Shape/Polygon", self.root.nsmap)
        if polygon is not None:
            try:
                coords = tuple(map(float, polygon.get("POINTS").split(" ")))
                block.box = tuple(zip(coords[::2], coords[1::2]))
            except ValueError:
                logger.warning("Invalid polygon %s" % polygon)
        else:
            x = int(blockTag.get("HPOS"))
            y = int(blockTag.get("VPOS"))
            w = int(blockTag.get("WIDTH"))
            h = int(blockTag.get("HEIGHT"))
            block.box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

        try:
            tag = blockTag.get("TAGREFS").split(" ")[0]
            type_ = self.root.find("./Tags/*[@ID='"+tag+"']", self.root.nsmap).get("LABEL")
        except (IndexError, AttributeError):
            # Index to catch empty tagrefs, Attribute to catch no tagrefs or invalid
            type_ = None

        if type_:
            valid_types_mapping = {t.name: t for t in self.document.valid_block_types.all()}
            if type_ in valid_types_mapping.keys():
                block.typology = valid_types_mapping[type_]
            else:
                # raise warning discard type
                pass

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
                    coords = tuple(map(float, baseline.split(" ")))
                    line.baseline = tuple(zip(coords[::2], coords[1::2]))
                except ValueError:
                    msg = "Invalid baseline %s in {filen} line {linen}" % (baseline, self.file.name, lineTag.sourceline)
                    logger.warning(msg)
                    if self.report:
                        self.report.append(msg)
        else:
            # extract it from <String>s then
            strings = lineTag.findall("String", self.root.nsmap)
            last_segment = strings[-1]
            line.baseline = [(int(e.get('HPOS')), int(e.get('VPOS'))) for e in strings]
            line.baseline.append((int(last_segment.get('HPOS'))+int(last_segment.get('WIDTH')),
                                  int(last_segment.get('VPOS'))))

        polygon = lineTag.find("Shape/Polygon", self.root.nsmap)
        if polygon is not None:
            try:
                coords = tuple(map(float, polygon.get("POINTS").split(" ")))
                line.mask = tuple(zip(coords[::2], coords[1::2]))
            except ValueError:
                msg = "Invalid polygon %s in {filen} line {linen}" % (polygon, self.file.name, lineTag.sourceline)
                logger.warning(msg)
                if self.report:
                    self.report.append(msg)
        else:
            line.box = [
                int(lineTag.get("HPOS")),
                int(lineTag.get("VPOS")),
                int(lineTag.get("HPOS")) + int(lineTag.get("WIDTH")),
                int(lineTag.get("VPOS")) + int(lineTag.get("HEIGHT")),
            ]

        try:
            tag = lineTag.get("TAGREFS").split(" ")[0]
            type_ = self.root.find("./Tags/*[@ID='"+tag+"']", self.root.nsmap).get("LABEL")
        except (IndexError, AttributeError):
            type_ = None

        if type_:
            valid_types_mapping = {t.name: t for t in self.document.valid_line_types.all()}
            if type_ in valid_types_mapping.keys():
                line.typology = valid_types_mapping[type_]
            else:
                # raise warning discard type
                pass

    def get_transcription_content(self, lineTag):
        return " ".join(
            [e.get("CONTENT") for e in lineTag.findall("String", self.root.nsmap)]
        )


class PagexmlParser(XMLParser):
    DEFAULT_NAME = _("Default PageXML Import")
    ACCEPTED_SCHEMAS = (
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2016-07-15/pagecontent.xsd",
        "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd",
    )

    @property
    def total(self):
        # pagexml file can contain multiple parts
        if not self.root:
            self.root = etree.parse(self.file).getroot()
        return len(self.root.findall("Page", self.root.nsmap))

    def get_filename(self, pageTag):
        try:
            filename = pageTag.get("imageFilename")
        except (IndexError, AttributeError) as e:
            raise ParseError("""
The PageXml file should contain an attribute imageFilename in Page tag for matching.
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
        return [(l.get("id"), l) for l in blockTag.findall("TextLine", self.root.nsmap)]

    def update_block(self, block, blockTag):
        coords = blockTag.find("Coords", self.root.nsmap).get("points")
        #  for pagexml file a box is multiple points x1,y1 x2,y2 x3,y3 ...
        block.box = [list(map(lambda x: int(float(x)), pt.split(","))) for pt in coords.split(" ")]

        type_ = blockTag.get("type")
        if not type_:
            custom = blockTag.get("custom")
            if custom:
                match = re.search('structure\s?{.*?type:\s?(\w+);', custom)
                if match:
                    type_ = match.groups()[0]

        if type_:
            valid_types_mapping = {t.name: t for t in self.document.valid_block_types.all()}
            if type_ in valid_types_mapping.keys():
                block.typology = valid_types_mapping[type_]
            else:
                # raise warning discard type
                pass

    def update_line(self, line, lineTag):
        try:
            baseline = lineTag.find("Baseline", self.root.nsmap)
            line.baseline = self.clean_coords(baseline)
        except AttributeError:
            #  to check if the baseline is good
            line.baseline = None

        polygon = lineTag.find("Coords", self.root.nsmap)
        if polygon is not None:
            line.mask = self.clean_coords(polygon)

        type_ = lineTag.get("type")
        if not type_:
            custom = lineTag.get("custom")
            if custom:
                match = re.search('structure\s?{.*?type:\s?(\w+);', custom)
                if match:
                    type_ = match.groups()[0]

        if type_:
            valid_types_mapping = {t.name: t for t in self.document.valid_line_types.all()}
            if type_ in valid_types_mapping.keys():
                line.typology = valid_types_mapping[type_]
            else:
                # raise warning discard type
                pass

    def clean_coords(self, coordTag):
        return [
                list(map(int, pt.split(",")))
                for pt in coordTag.get("points").split(" ")
            ]

    def get_transcription_content(self, lineTag):
        words = lineTag.findall("Word", self.root.nsmap)
        # pagexml can have content for each word inside a word tag or the whole line in textline tag
        if len(words) > 0:
            return " ".join(
                [
                    e.text if e.text is not None else ""
                    for e in lineTag.findall("Word/TextEquiv/Unicode", self.root.nsmap)
                ]
            )
        else:
            return " ".join(
                [
                    e.text if e.text is not None else ""
                    for e in lineTag.findall("TextEquiv/Unicode", self.root.nsmap)
                ]
            )


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
            return 0

    def validate(self):
        if len(self.canvases) < 1:
            raise ParseError(_("Empty or invalid manifest, no images found."))

    @property
    def total(self):
        return len(self.canvases)

    def parse(self, start_at=0, override=False, user=None):
        try:
            for metadata in self.manifest["metadata"]:
                if metadata["value"]:
                    name = str(metadata["label"])[:128]
                    md, created = Metadata.objects.get_or_create(name=name)
                    DocumentMetadata.objects.get_or_create(
                        document=self.document, key=md, value=metadata["value"][:512]
                    )
        except KeyError:
            pass

        for i, canvas in enumerate(self.canvases):
            if i < start_at:
                continue
            try:
                resource = canvas["images"][0]["resource"]
                url = resource["@id"]
                uri_template = "{image}/{region}/{size}/{rotation}/{quality}.{format}"
                url = uri_template.format(
                    image=resource["service"]["@id"],
                    region="full",
                    size=getattr(settings, "IIIF_IMPORT_QUALITY", "full"),
                    rotation=0,
                    quality="default",
                    format="jpg",
                )  # we could gain some time by fetching png, but it's not implemented everywhere.
                r = requests.get(url, stream=True, verify=False)
                if r.status_code != 200:
                    raise ParseError("Invalid image url: %s" % url)
                part = DocumentPart(document=self.document, source=url)
                if "label" in resource:
                    part.name = resource["label"]
                # iiif file names are always default.jpg or close to
                name = "%d_%s_%s" % (i, uuid.uuid4().hex[:5], url.split("/")[-1])
                part.original_filename = name
                part.image.save(name, ContentFile(r.content), save=False)
                part.save()
                yield part
                time.sleep(0.1)  # avoid being throttled
            except (KeyError, IndexError) as e:
                if self.report:
                    self.report.append(_('Error while fetching {filename}: {error}').format(
                        filename=name, error=e))


class TranskribusPageXmlParser(PagexmlParser):
    """
    A Pagexml Parser for documents exported from Transkribus to handle data
    """

    # def validate(self):
    #     warnings.warn(
    #         "Validation is skipped for Transkribus Files but coordinates will be corrected",
    #         SyntaxWarning,
    #         2,
    #     )

    def clean_coords(self, coordTag):
        return [
                list(map(lambda x: 0 if float(x) < 0 else float(x), pt.split(",")))
                for pt in coordTag.get("points").split(" ")
            ]


def make_parser(document, file_handler, name=None, report=None):
    # TODO: not great to rely on file name extension
    ext = os.path.splitext(file_handler.name)[1][1:]
    if ext in XML_EXTENSIONS:
        try:
            root = etree.parse(file_handler).getroot()
        except etree.XMLSyntaxError as e:
            raise ParseError(e.msg)
        try:
            schema = root.nsmap[None]
        except KeyError:
            raise ParseError(
                "Couldn't determine xml schema, xmlns attribute missing on root element."
            )
        # if 'abbyy' in schema:  # Not super robust
        #     return AbbyyParser(root, name=name)
        if "alto" in schema:
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

        else:
            raise ParseError(
                "Couldn't determine xml schema, check the content of the root tag."
            )
    elif ext == "json":
        return IIIFManifestParser(document, file_handler, report)
    elif ext == "zip":
        return ZipParser(document, file_handler, report, transcription_name=name)
    elif ext == "pdf":
        return PdfParser(document, file_handler, report)
    else:
        raise ValueError(
            "Invalid extension for the file to be parsed %s." % file_handler.name
        )
