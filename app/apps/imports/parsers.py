from lxml import etree
import logging
import os.path
import requests
import sys
import time
import uuid
import zipfile
import warnings

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.forms import ValidationError
from django.utils.translation import gettext as _
from django.utils.functional import cached_property

from core.models import *
from versioning.models import NoChangeException

logger = logging.getLogger(__name__)
XML_EXTENSIONS = ["xml", "alto"]  # , 'abbyy'


class ParseError(Exception):
    pass


class ParserDocument:
    """
    The base class for parsing files to populate a core.Document object
    or/and its ancestors.
    """

    DEFAULT_NAME = None

    def __init__(self, document, file_handler, transcription_name=None):
        self.file = file_handler
        self.document = document
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
                    parser = make_parser(self.document, zipedfh)
                    try:
                        for part in parser.parse(override=override):
                            yield part
                    except ParseError as e:
                        # we let go to try other documents
                        msg = _("Parse error in {filename}: {error}").format(
                            filename=self.file.name, error=e.args[0]
                        )
                        logger.warning(msg)
                        if user:
                            user.notify(msg, id="import:warning", level="warning")


class XMLParser(ParserDocument):
    def __init__(self, document, file_handler, transcription_name=None, xml_root=None):
        if xml_root is not None:
            self.root = xml_root
            try:

                self.schema_location = self.root.xpath(
                    "//*/@xsi:schemaLocation",
                    namespaces={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
                )[0]

            except (etree.XPathEvalError,IndexError) as e:
                raise ParseError("Cannot Find Schema location %s" % e.args[0])

        else:
            try:
                self.root = etree.parse(self.file).getroot()
            except (AttributeError, etree.XMLSyntaxError) as e:
                raise ParseError("Invalid XML. %s" % e.args[0])
        super().__init__(document, file_handler, transcription_name=transcription_name)

    def validate(self):

        file_schema = self.schema_location.split(" ")[-1]

        if file_schema in self.ACCEPTED_SCHEMAS:
            try:

                response = requests.get(self.schema)
                content = response.content
                schema_root = etree.XML(content)
            except requests.exceptions.RequestException as e:
                logger.exception(e)
                raise ParseError("Can't reach validation document %s." % self.schema)
            else:
                try:
                    xmlschema = etree.XMLSchema(schema_root)
                    xmlschema.assertValid(self.root)
                except (
                    AttributeError,
                    etree.DocumentInvalid,
                    etree.XMLSyntaxError,
                ) as e:
                    raise ParseError("Document didn't validate. %s" % e.args[0])
        else:
            raise ParseError("Document Schema not founded %s.")

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
                lt.new_version()  # save current content in history
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
                raise ParseError(
                    _("No match found for file {} with filename <{}>.").format(
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
                                if block_id.startswith("eSc_textblock_"):
                                    internal_id = int(block_id[len("eSc_textblock_") :])
                                    block = Block.objects.get(
                                        document_part=part, pk=internal_id
                                    )
                                else:
                                    block = Block.objects.get(
                                        document_part=part, external_id=block_id
                                    )
                            except Block.DoesNotExist:
                                block = None

                            if block is None:
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
                                    raise ParseError(e)
                                else:
                                    block.save()
                        else:
                            block = None

                        for line_id, lineTag in self.get_lines(blockTag):
                            if line_id:
                                try:
                                    if line_id.startswith("eSc_line_"):
                                        line = Line.objects.get(
                                            document_part=part,
                                            pk=int(line_id[len("eSc_line_") :]),
                                        )
                                    else:
                                        line = Line.objects.get(
                                            document_part=part, external_id=line_id
                                        )
                                except Line.DoesNotExist:
                                    line = None
                            else:
                                line = None

                            if line is None:
                                # not found, create it then
                                line = Line(
                                    document_part=part, block=block, external_id=line_id
                                )

                            self.update_line(line, lineTag)
                            try:
                                line.full_clean()
                            except ValidationError as e:
                                raise ParseError(e)
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
    ACCEPTED_SCHEMAS  = (
        "http://www.loc.gov/standards/alto/v4/alto.xsd",
        "http://www.loc.gov/standards/alto/v4/alto-4-0.xsd",
        "http://www.loc.gov/standards/alto/v4/alto-4-1.xsd",
    )

    def __init__(self, document, file_handler, transcription_name=None, xml_root=None):
        super().__init__(document, file_handler, transcription_name, xml_root)
        self.schema = "https://gitlab.inria.fr/scripta/escriptorium/-/raw/develop/app/escriptorium/static/alto-4-1-baselines.xsd"

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
            raise ParseError(
                "The alto file should contain a Description/sourceImageInformation/fileName tag for matching."
            )
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
        x = int(blockTag.get("HPOS"))
        y = int(blockTag.get("VPOS"))
        w = int(blockTag.get("WIDTH"))
        h = int(blockTag.get("HEIGHT"))
        block.box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

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
                    logger.warning("Invalid baseline %s" % baseline)

        polygon = lineTag.find("Shape/Polygon", self.root.nsmap)
        if polygon is not None:
            try:
                coords = tuple(map(float, polygon.get("POINTS").split(" ")))
                line.mask = tuple(zip(coords[::2], coords[1::2]))
            except ValueError:
                logger.warning("Invalid polygon %s" % polygon)
        else:
            line.box = [
                int(lineTag.get("HPOS")),
                int(lineTag.get("VPOS")),
                int(lineTag.get("HPOS")) + int(lineTag.get("WIDTH")),
                int(lineTag.get("VPOS")) + int(lineTag.get("HEIGHT")),
            ]

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

    def __init__(self, document, file_handler, transcription_name=None, xml_root=None):
        super().__init__(document, file_handler, transcription_name, xml_root)
        self.schema = self.schema_location.split(" ")[-1]

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
            raise ParseError(
                "The PageXml file should contain an attribute imageFilename in Page tag for matching."
            )
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

    def update_line(self, line, lineTag):
        try:
            baseline = lineTag.find("Baseline", self.root.nsmap)
            line.baseline = [
                list(map(lambda x: int(float(x)), pt.split(',')))
                for pt in baseline.get('points').split(' ')
            ]
        except AttributeError:
            #  to check if the baseline is good
            line.baseline = None

        polygon = lineTag.find("Coords", self.root.nsmap)
        if polygon is not None:
            line.mask = [
                list(map(lambda x: int(float(x)), pt.split(",")))
                for pt in polygon.get("points").split(" ")
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
        except (json.JSONDecodeError) as e:
            raise ParseError(e)

    @cached_property
    def canvases(self):
        try:
            return self.manifest["sequences"][0]["canvases"]
        except (KeyError, IndexError) as e:
            raise ParseError(e)

    def validate(self):
        if len(self.canvases) < 1:
            raise ParseError(_("Empty manifesto."))

    @property
    def total(self):
        return len(self.canvases)

    def parse(self, start_at=0, override=False, user=None):
        try:
            for metadata in self.manifest["metadata"]:
                if metadata["value"]:
                    md, created = Metadata.objects.get_or_create(name=metadata["label"])
                    DocumentMetadata.objects.get_or_create(
                        document=self.document, key=md, value=metadata["value"][:512]
                    )
        except KeyError as e:
            pass

        try:
            for i, canvas in enumerate(self.canvases):
                if i < start_at:
                    continue
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
            raise ParseError(e)


class TranskribusPageXmlParser(PagexmlParser):
    """
    A Pagexml Parser for documents exported from Transkribus to handle data
    """

    def validate(self):

        warnings.warn(
            "Validation is skipped for Transkribus Files but coordinates will be corrected",
            SyntaxWarning,
            2,
        )

    def update_line(self, line, lineTag):
        super().update_line(line, lineTag)
        line.baseline = self.clean_coords(line.baseline)
        line.mask = self.clean_coords(line.mask)

    def update_block(self, block, blockTag):
        super().update_block(block, blockTag)
        block.box = self.clean_coords(block.box)

    def clean_coords(self, points):
        coords = [
            list(map(lambda x: 0 if float(x) < 0 else int(float(x)), pt))
            for pt in points
        ]

        return coords


def make_parser(document, file_handler, name=None):
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
                document, file_handler, transcription_name=name, xml_root=root
            )
        elif "PAGE" in schema:
            if b"Transkribus" in etree.tostring(root):
                return TranskribusPageXmlParser(
                    document, file_handler, transcription_name=name, xml_root=root
                )
            else:
                return PagexmlParser(
                    document, file_handler, transcription_name=name, xml_root=root
                )

        else:
            raise ParseError(
                "Couldn't determine xml schema, check the content of the root tag."
            )
    elif ext == "json":
        return IIIFManifestParser(document, file_handler)
    elif ext == "zip":
        return ZipParser(document, file_handler, transcription_name=name)
    else:
        raise ValueError(
            "Invalid extension for the file to be parsed %s." % file_handler.name
        )
