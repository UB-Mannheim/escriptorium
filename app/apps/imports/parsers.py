from lxml import etree
import logging
import os.path
import requests
import time
import uuid
import zipfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext as _
from django.utils.functional import cached_property

from core.models import *
from versioning.models import NoChangeException

logger = logging.getLogger(__name__)
XML_EXTENSIONS = ['xml', 'alto']  # , 'abbyy'

class ParseError(Exception):
    pass


class ParserDocument():
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
            document=self.document,
            name=self.name)
        return transcription


class XMLParser:
    def validate(self):
        try:
            # response = requests.get(self.SCHEMA)
            # content = response.content
            from django.contrib.staticfiles.storage import staticfiles_storage
            content = staticfiles_storage.open(self.SCHEMA_FILE).read()
            schema_root = etree.XML(content)
        except:
            raise ParseError("Can't reach validation document %s." % self.SCHEMA)
        else:
            try:
                xmlschema = etree.XMLSchema(schema_root)
                xmlschema.assertValid(self.root)
            except (AttributeError, etree.DocumentInvalid, etree.XMLSyntaxError) as e:
                raise ParseError("Document didn't validate. %s" % e.args[0])


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
        except:
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
                    alto_parser = AltoParser(self.document, zipedfh)
                    try:
                        alto_parser.validate()
                        part = alto_parser.parse(override=override)
                    except ParseError as e:
                        # we let go to try other documents
                        msg = _("Parse error in {filename}: {error}").format(filename=self.file.name, error=e.args[0])
                        logger.warning(msg)
                        if user:
                            user.notify(msg, id="import:warning", level='warning')
                    else:
                        yield part


class AltoParser(ParserDocument,XMLParser):
    DEFAULT_NAME = _("Default Alto Import")
    SCHEMA = 'http://www.loc.gov/standards/alto/v4/alto-4-1.xsd'
    SCHEMA_FILE = 'alto-4-1-baselines.xsd'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.root = etree.parse(self.file).getroot()
        except (AttributeError, etree.XMLSyntaxError) as e:
            raise ParseError("Invalid XML. %s" % e.args[0])

    @property
    def total(self):
        # An alto file always describes 1 'document part'
        return 1
    
    def parse(self, start_at=0, override=False, user=None):
        # find the filename to match with existing images
        try:
            filename = self.root.find('Description/sourceImageInformation/fileName', self.root.nsmap).text
        except (IndexError, AttributeError) as e:
            raise ParseError("The alto file should contain a Description/sourceImageInformation/fileName tag for matching.")
            
        try:
            part = DocumentPart.objects.filter(document=self.document, original_filename=filename)[0]
        except IndexError:
            raise ParseError(_("No match found for file {} with filename <{}>.").format(self.file.name, filename))
        else:            
            # if something fails, revert everything for this document part
            with transaction.atomic():
                if override:
                    part.lines.all().delete()
                    part.blocks.all().delete()

                block = None
                # pages = self.root.findall('Page', self.root.nsmap)
                # for page in pages:
                #     if page.get('ID') != 'dummy':
                #         block = Block.objects.create()

                for block in self.root.findall('Layout/Page/PrintSpace/TextBlock', self.root.nsmap):
                    id_ = block.get('ID')
                    if id_ and id_.startswith('eSc_dummyblock_'):
                        block_ = None
                    else:
                        try:
                            assert id_ and id_.startswith('eSc_textblock_')
                            attrs = {'pk': int(id_[len('eSc_textblock_'):])}
                        except (ValueError, AssertionError, TypeError):
                            attrs = {'document_part': part,
                                     'external_id': id_}
                        try:
                            block_ = Block.objects.get(**attrs)
                        except Block.DoesNotExist:
                            # not found, create it then
                            block_ = Block(**attrs)

                        try:
                            block_.box = [int(block.get('HPOS')),
                                          int(block.get('VPOS')),
                                          int(block.get('HPOS')) + int(block.get('WIDTH')),
                                          int(block.get('VPOS')) + int(block.get('HEIGHT'))]
                        except TypeError:
                            # probably a dummy block from another app
                            block_ = None
                        else:
                            block_.save()

                    for line in block.findall('TextLine', self.root.nsmap):
                        id_ = line.get('ID')
                        try:
                            assert id_ and id_.startswith('eSc_line_')
                            attrs = {'document_part': part,
                                     'pk': int(id_[len('eSc_line_'):])}
                        except (ValueError, AssertionError, TypeError):
                            attrs = {'document_part': part,
                                     'block': block_,
                                     'external_id': id_}
                        try:
                            line_ = Line.objects.get(**attrs)
                        except Line.DoesNotExist:
                            # not found, create it then
                            line_ = Line(**attrs)
                        baseline = line.get('BASELINE')
                        if baseline is not None:
                            try:
                                line_.baseline = [list(map(int, pt.split(',')))
                                                  for pt in baseline.split(' ')]
                            except ValueError:
                                logger.warning('Invalid baseline %s' % baseline)
                        
                        polygon = line.find('Shape/Polygon', self.root.nsmap)
                        if polygon is not None:
                            try:
                                line_.mask = [list(map(int, pt.split(',')))
                                              for pt in polygon.get('POINTS').split(' ')]
                            except ValueError:
                                logger.warning('Invalid polygon %s' % polygon)
                        else:
                            line_.box = [int(line.get('HPOS')),
                                         int(line.get('VPOS')),
                                         int(line.get('HPOS')) + int(line.get('WIDTH')),
                                         int(line.get('VPOS')) + int(line.get('HEIGHT'))]
                        line_.save()
                        content = ' '.join([e.get('CONTENT')
                                            for e in line.findall('String', self.root.nsmap)])
                        try:
                            # lazily creates the Transcription on the fly if need be cf transcription() property
                            lt = LineTranscription.objects.get(transcription=self.transcription, line=line_)
                        except LineTranscription.DoesNotExist:
                            lt = LineTranscription(version_source='import',
                                                   version_author=user and user.username or '',
                                                   transcription=self.transcription,
                                                   line=line_)
                        else:
                            try:
                                lt.new_version()  # save current content in history
                            except NoChangeException:
                                pass
                        finally:
                            lt.content = content
                            lt.save()
                            
            # TODO: store glyphs too        
            logger.info('Uncompressed and parsed %s' % self.file.name)
            part.calculate_progress()
            return [part]


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
            return self.manifest['sequences'][0]['canvases']
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
            for metadata in self.manifest['metadata']:
                if metadata['value']:
                    md, created = Metadata.objects.get_or_create(name=metadata['label'])
                    DocumentMetadata.objects.get_or_create(
                        document=self.document,
                        key=md,
                        value=metadata['value'][:512])
        except KeyError as e:
            pass
        
        try:
            for i, canvas in enumerate(self.canvases):
                if i < start_at:
                    continue
                resource = canvas['images'][0]['resource']
                url = resource['@id']
                uri_template =  '{image}/{region}/{size}/{rotation}/{quality}.{format}'
                url = uri_template.format(
                    image=resource['service']['@id'],
                    region='full',
                    size=getattr(settings, 'IIIF_IMPORT_QUALITY', 'full'),
                    rotation=0,
                    quality='default',
                    format='jpg')  # we could gain some time by fetching png, but it's not implemented everywhere.
                r = requests.get(url, stream=True, verify=False)
                if r.status_code != 200:
                    raise ParseError('Invalid image url: %s' % url)
                part = DocumentPart(
                    document=self.document,
                    source=url)
                if 'label' in resource:
                    part.name = resource['label']
                # iiif file names are always default.jpg or close to
                name = '%d_%s_%s' % (i, uuid.uuid4().hex[:5], url.split('/')[-1])
                part.original_filename = name
                part.image.save(name, ContentFile(r.content), save=False)
                part.save()
                yield part
                time.sleep(0.1)  # avoid being throttled
        except (KeyError, IndexError) as e:
            raise ParseError(e)


class PagexmlParser(ParserDocument, XMLParser):
    DEFAULT_NAME = _("Default PageXML Import")
    SCHEMA = 'https://www.primaresearch.org/schema/PAGE/gts/pagecontent/2019-07-15/pagecontent.xsd'
    SCHEMA_FILE = 'pagexml-schema.xsd'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.root = etree.parse(self.file).getroot()
            #  Transkribus file vaidate it with Transkribus schema
            if b'/pagecontent/2013' in etree.tostring(self.root):
                self.SCHEMA_FILE = 'pagexml-schema-2013.xsd'
        except (AttributeError, etree.XMLSyntaxError) as e:
            raise ParseError("Invalid XML. %s" % e.args[0])

    @property
    def total(self):
        if not self.root:
            self.root = etree.parse(self.file).getroot()
        return len(self.root.findall('Page', self.root.nsmap))

    def parse(self, start_at=0, override=False, user=None):
        parts = []
        if not self.root:
            self.root = etree.parse(self.file).getroot()
        # find the filename to
        for page in self.root.findall('Page', self.root.nsmap):

            try:
                filename = page.get('imageFilename')
            except (IndexError, AttributeError) as e:
                raise ParseError("The PageXml file should contain an attribute imageFilename in Page tag for matching.")

            try:
                part = DocumentPart.objects.filter(document=self.document, original_filename=filename)[0]
            except IndexError:
                raise ParseError("No match found for file %s with filename %s." % (self.file.name, filename))
            else:
                # if something fails, revert everything for this document part
                with transaction.atomic():
                    if override:
                        part.lines.all().delete()
                        part.blocks.all().delete()

                    block = None

                    for block in page.findall('TextRegion', self.root.nsmap):
                        id_ = block.get('id')
                        if id_ and id_.startswith('eSc_dummyblock_'):
                            block_ = None
                        else:
                            try:
                                assert id_ and id_.startswith('eSc_textblock_')
                                attrs = {'pk': int(id_[len('eSc_textblock_'):])}
                            except (ValueError, AssertionError, TypeError):
                                attrs = {'document_part': part,
                                         'external_id': id_}
                            try:
                                block_ = Block.objects.get(**attrs)
                            except Block.DoesNotExist:
                                # not found, create it then
                                block_ = Block(**attrs)

                            try:

                                coords = block.find('Coords', self.root.nsmap).get('points')
                                start = coords.split(' ')[0]
                                end = coords.split(' ')[2]
                                block_.box = [list(map(int, pt.split(',')))
                                              for pt in coords.split(' ')]
                            except TypeError:
                                # probably a dummy block from another app
                                block_ = None
                            else:
                                block_.save()

                        for line in block.findall('TextLine', self.root.nsmap):
                            id_ = line.get('id')
                            try:
                                assert id_ and id_.startswith('eSc_line_')
                                attrs = {'document_part': part,
                                         'pk': int(id_[len('eSc_line_'):])}
                            except (ValueError, AssertionError, TypeError):
                                attrs = {'document_part': part,
                                         'block': block_,
                                         'external_id': id_}
                            try:
                                line_ = Line.objects.get(**attrs)
                            except Line.DoesNotExist:
                                # not found, create it then
                                line_ = Line(**attrs)
                            try :
                                baseline = line.find('Baseline', self.root.nsmap)
                                line_.baseline = [list(map(int, pt.split(',')))
                                                  for pt in baseline.get('points').split(' ')]

                            except AttributeError:
                                #  to check if the baseline is good
                                line_.baseline = None
                            # i didn't find any polygon
                            #  polygon == TextLine/Coords
                            polygon = line.find('Coords', self.root.nsmap)
                            if polygon is not None:
                                line_.mask = [list(map(int, pt.split(',')))
                                              for pt in polygon.get('points').split(' ')]
                            # else:
                            #     line_.box = [int(line.get('HPOS')),
                            #                  int(line.get('VPOS')),
                            #                  int(line.get('HPOS')) + int(line.get('WIDTH')),
                            #                  int(line.get('VPOS')) + int(line.get('HEIGHT'))]
                            line_.save()
                            words = line.findall('Word', self.root.nsmap)
                            if len(words) > 0:
                                content = ' '.join([e.text for e in line.findall('Word/TextEquiv/Unicode', self.root.nsmap)])
                            else:
                                content = ' '.join([e.text for e in line.findall('TextEquiv/Unicode', self.root.nsmap)])
                            try:

                                # lazily creates the Transcription on the fly if need be cf transcription() property
                                lt = LineTranscription.objects.get(transcription=self.transcription, line=line_)
                            except LineTranscription.DoesNotExist:
                                lt = LineTranscription(version_source='import',
                                                       version_author=self.name,
                                                       transcription=self.transcription,
                                                       line=line_)
                            else:
                                try:
                                    lt.new_version()  # save current content in history
                                except NoChangeException:
                                    pass
                            finally:
                                lt.content = content
                                lt.save()

                # TODO: store glyphs too
                logger.info('Uncompressed and parsed %s' % self.file.name)
                part.calculate_progress()
                parts.append(part)
        return parts


def make_parser(document, file_handler, name=None):
    # TODO: not great to rely on file name extension
    ext = os.path.splitext(file_handler.name)[1][1:]
    if ext in XML_EXTENSIONS:
        try:
            root = etree.parse(file_handler).getroot()
            file_handler.seek(0)  # not ideal but validation needs to read it again.
        except etree.XMLSyntaxError as e:
            raise ParseError(e.msg)
        try:
            schema = root.nsmap[None]
        except KeyError:
            raise ParseError("Couldn't determine xml schema, xmlns attribute missing on root element.")
        # if 'abbyy' in schema:  # Not super robust
        #     return AbbyyParser(root, name=name)
        if 'alto' in schema:
            return AltoParser(document, file_handler, transcription_name=name)
        elif 'PAGE' in schema:
            return PagexmlParser(document, file_handler, transcription_name=name)
        else:
            raise ParseError("Couldn't determine xml schema, check the content of the root tag.")
    elif ext == 'json':
        return IIIFManifestParser(document, file_handler)
    elif ext == 'zip':
        return ZipParser(document, file_handler, transcription_name=name)
    else:
        raise ValueError("Invalid extension for the file to be parsed %s." % file_handler.name)
