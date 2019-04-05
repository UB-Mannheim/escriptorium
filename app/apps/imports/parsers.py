from django.db import transaction
from django.utils.translation import gettext as _

from bs4 import BeautifulSoup

from core.models import *


DEFAULT_NAME = getattr(settings, 'ALTO_IMPORT_NAME', _("ALTO Import"))

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
    
    def __init__(self, soup, name=DEFAULT_NAME):
        self.soup = soup
        self.name = name
        try:
            self.pages = self.soup.find_all(self.TAGS['page'])
        except AttributeError:
            raise ParseError
        
    def make_line(self, line_tag):
        pass

    def bbox(self, tag):
        pass

    def block_bbox(self, block_tag):
        return self.bbox(block_tag)

    def line_bbox(self, line_tag):
        return self.bbox(line_tag)

    def post_process(self, part):
        pass
    
    def parse(self, document, parts):
        """
        This is actually a generator that yields the parts
        """
        trans, created = Transcription.objects.get_or_create(
            document=document,
            name=self.name)
        
        try:
            for index, page in enumerate(self.pages):
                with transaction.atomic():
                    part = parts[index]
                    part.blocks.all().delete()
                    part.lines.all().delete()
                    for block in page.find_all(self.TAGS['block']):
                        b = Block.objects.create(
                            document_part=part,
                            box=self.block_bbox(block))
                        
                        for line in block.find_all(self.TAGS['line']):
                            l = Line.objects.create(
                                document_part=part,
                                block=b,
                                box=self.line_bbox(line))
                            content = self.make_line(line)
                            if content:
                                lt = LineTranscription.objects.create(
                                    transcription=trans,
                                    line=l,
                                    content=content)
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
    
    def bbox(self, tag):
        return (
            int(tag.attrs['HPOS']),
            int(tag.attrs['VPOS']),
            int(tag.attrs['HPOS']) + int(tag.attrs['WIDTH']),
            int(tag.attrs['VPOS']) + int(tag.attrs['HEIGHT']),
        )
    
    def make_line(self, line_tag):
        content = ''
        for string in line_tag.find_all('String'):
            content += (string.attrs.get('CONTENT') + ' ')
        return content


class AbbyyParser(XMLParser):
    BLOCK_MARGIN = 10

    def line_bbox(self, tag):
        return (
            int(tag.attrs['l']),
            int(tag.attrs['t']),
            int(tag.attrs['r']),
            int(tag.attrs['b'])
        )
    
    def block_bbox(self, tag):
        return (0,0,0,0)
    
    def make_line(self, line_tag):
        content = ''.join(map(lambda a: a.text, line_tag.find_all('charParams')))
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


def make_parser(file_handler):
    soup = BeautifulSoup(file_handler, 'xml')
    root = next(soup.descendants)
    schema = root.attrs['xmlns']
    if 'abbyy' in schema:  # Not super robust
        return AbbyyParser(soup)
    elif 'alto' in schema:
        return AltoParser(soup)
    else:
        raise ParseError("Couldn't determine xml schema, abbyy or alto, check the content of the root tag.")

