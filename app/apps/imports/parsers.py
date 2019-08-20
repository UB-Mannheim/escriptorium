from lxml import etree
import os.path
import requests
import time
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext as _

from bs4 import BeautifulSoup

from core.models import *
from versioning.models import NoChangeException


XML_EXTENSIONS = ['xml', 'alto', 'abbyy']

class ParseError(Exception):
    pass


class XMLParser():
    TAGS = {
        'page': 'page',
        'block': 'block',
        'line': 'line'
    }
    SCHEMA_ABBYY = 'abbyy'
    SCHEMA_ALTO = 'alto'
    DEFAULT_NAME = _("XML Import")
    
    def __init__(self, root, name=None, override=True):
        self.root = root
        self.name = name or self.DEFAULT_NAME
        self.override = override
        self.namespace = self.root.nsmap[None]
        self.pages = self.find(self.root, self.TAGS['page'])

    def find(self, parent, tag):
        return parent.findall('.//{%s}%s' % (self.namespace, tag))
        
    def make_line(self, line_tag):
        pass
    
    def bbox(self, tag):
        pass
    
    def block_bbox(self, block_tag):
        return self.bbox(block_tag)
    
    def line_bbox(self, line_tag):
        return self.bbox(line_tag)
    
    def post_process(self, part):
        part.calculate_progress()
        part.save()
    
    @property
    def total(self):
        return len(self.pages)
    
    def validate(self):
        return True
    
    def parse(self, document, parts, start_at=0):
        """
        This is actually a generator that yields the parts
        """
        trans, created = Transcription.objects.get_or_create(
            document=document,
            name=self.name)
        try:
            for index, page in enumerate(self.pages):
                if index < start_at:
                    continue
                with transaction.atomic():
                    part = parts[index]
                    if self.override:
                        part.blocks.all().delete()
                        part.lines.all().delete()
                    for block in self.find(page, self.TAGS['block']):
                        # Note: don't use get_or_create to avoid a update query
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
                                block_ = Block(**attrs)
                            try:
                                block_.box = self.block_bbox(block)
                            except TypeError:  # probably a dummy block
                                block_ = None
                            else:
                                block_.save()
                        
                        for line in self.find(block, self.TAGS['line']):
                            id_ = line.get('ID')
                            
                            try:
                                assert id_ and id_.startswith('eSc_line_')
                                attrs = {'document_part': part,
                                         'pk': int(id_[len('eSc_line_'):])}
                            except (ValueError, AssertionError, TypeError):
                                attrs = {'document_part': part,
                                         'block': block_,
                                         'external_id': line.get('ID')}
                            try:
                                l = Line.objects.get(**attrs)
                            except Line.DoesNotExist:
                                l = Line(**attrs)
                            l.box = self.line_bbox(line)
                            l.save()
                            content = self.make_line(line)
                            if content:
                                attrs = {'transcription': trans, 'line':l}
                                try:
                                    lt = LineTranscription.objects.get(**attrs)
                                except LineTranscription.DoesNotExist:
                                    lt = LineTranscription(version_source='import',
                                                           version_author=self.name,
                                                           **attrs)
                                else:
                                    try:
                                        lt.new_version()  # save current content in history
                                    except NoChangeException:
                                        pass
                                lt.content = content
                                lt.save()
                            
                            # TODO: store glyphs too
                self.post_process(part)
                yield part
        except AttributeError as e:
            raise ParseError(e)


class AltoParser(XMLParser):
    TAGS = {
        'page': 'Page',
        'block': 'TextBlock',
        'line': 'TextLine'
    }
    DEFAULT_NAME = _("ALTO Import")
    SCHEMA = 'http://www.loc.gov/standards/alto/v4/alto-4-0.xsd'
    
    def bbox(self, tag):
        return (
            int(tag.get('HPOS')),
            int(tag.get('VPOS')),
            int(tag.get('HPOS')) + int(tag.get('WIDTH')),
            int(tag.get('VPOS')) + int(tag.get('HEIGHT')),
        )
    
    def make_line(self, line_tag):
        return ' '.join([e.get('CONTENT') for e in self.find(line_tag, 'String')])

    def validate(self):
        try:
            response = requests.get(self.SCHEMA)
        except:
            raise ParseError("Can't reach validation document %s." % self.SCHEMA)
        else:
            schema_root = etree.XML(response.content)
            xmlschema = etree.XMLSchema(schema_root)
            try:
                xmlschema.assertValid(self.root)
            except (AttributeError, etree.DocumentInvalid, etree.XMLSyntaxError) as e:
                raise ParseError("Document didn't validate. %s" % e.args[0])


class AbbyyParser(XMLParser):
    BLOCK_MARGIN = 10
    DEFAULT_NAME = _("ABBYY Import")
    SCHEMA = ''
    
    def line_bbox(self, tag):
        return (
            int(tag.get('l')),
            int(tag.get('t')),
            int(tag.get('r')),
            int(tag.get('b')))
    
    def block_bbox(self, tag):
        return (0,0,0,0)
    
    def make_line(self, line_tag):
        content = ''.join([e.text for e in self.find(line_tag, 'charParams')])
        return content

    def post_process(self, part):
        for block in part.blocks.all():
            f = block.line_set.first()
            l = block.line_set.last()
            block.box = (f.box[0]-self.BLOCK_MARGIN,
                         f.box[1]-self.BLOCK_MARGIN,
                         l.box[0]+self.BLOCK_MARGIN,
                         l.box[1]+self.BLOCK_MARGIN)
            block.save()

    def validate(self):
        pass


class IIIFManifesParser():
    def __init__(self, fh, quality=None):
        self.file = fh
        self.quality = quality or 'full'
        try:
            self.manifest = json.loads(self.file.read())
            self.canvases = self.manifest['sequences'][0]['canvases']
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ParseError(e)
    
    @property
    def total(self):
        return len(self.canvases)
    
    def parse(self, document, parts, start_at=0):
        try:
            for metadata in self.manifest['metadata']:
                if metadata['value']:
                    md, created = Metadata.objects.get_or_create(name=metadata['label'])
                    DocumentMetadata.objects.get_or_create(
                        document=document, key=md, value=metadata['value'][:512])
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
                    size=self.quality,
                    rotation=0,
                    quality='default',
                    format='jpg')  # we could gain some time by fetching png, but it's not implemented everywhere.
                r = requests.get(url, stream=True, verify=False)
                if r.status_code != 200:
                    raise ParseError('Invalid image url: %s' % url)
                part = DocumentPart(
                    document=document,
                    source=url
                )
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


def make_parser(file_handler, name=None, override=True):
    # TODO: not great to rely on extension
    ext = os.path.splitext(file_handler.name)[1][1:]
    if ext in XML_EXTENSIONS:
        try:
            root = etree.parse(file_handler).getroot()
        except etree.XMLSyntaxError as e:
            raise ParseError(e.msg)
        try:
            schema = root.nsmap[None]
        except KeyError:
            raise ParseError("Couldn't determine xml schema, xmlns attribute missing on root element.")
        if 'abbyy' in schema:  # Not super robust
            return AbbyyParser(root, name=name, override=override)
        elif 'alto' in schema:
            return AltoParser(root, name=name, override=override)
        else:
            raise ParseError("Couldn't determine xml schema, abbyy or alto, check the content of the root tag.")
    elif ext == 'json':
        return IIIFManifesParser(file_handler)
    else:
        raise ValueError("Invalid extension for the file to be parsed %s." % file_handler.name)
