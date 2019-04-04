from django.db import transaction
from django.utils.translation import gettext as _

from bs4 import BeautifulSoup

from core.models import *


DEFAULT_NAME = getattr(settings, 'ALTO_IMPORT_NAME', _("ALTO Import"))

class ParseError(Exception):
    pass


class AltoParser():
    def __init__(self, file_handler, name=DEFAULT_NAME):
        self.soup = BeautifulSoup(file_handler, 'xml')
        self.name = name
        try:
            self.pages = self.soup.alto.Layout.find_all('Page')
        except AttributeError:
            raise ParseError
    
    def parse(self, document, parts):
        """
        This is actually a generator that yields the parts
        """
        def bbox(tag):
            return (
                int(tag.attrs['HPOS']),
                int(tag.attrs['VPOS']),
                int(tag.attrs['HPOS']) + int(tag.attrs['WIDTH']),
                int(tag.attrs['VPOS']) + int(tag.attrs['HEIGHT']),
            )
        trans, created = Transcription.objects.get_or_create(
            document=document,
            name=self.name)
        
        try:
            lines = []
            for index, page in enumerate(self.pages):
                with transaction.atomic():
                    part = parts[index]
                    part.blocks.all().delete()
                    part.lines.all().delete()
                    for block in page.find_all('TextBlock'):
                        b = Block.objects.create(
                            document_part=part, box=bbox(block))
                        for line in block.find_all('TextLine'):
                            content = ''
                            for string in line.find_all('String'):
                                content += string.attrs['CONTENT']
                            l = Line.objects.create(
                                document_part=part,
                                block=b,
                                box=bbox(line))
                            lines.append(l)
                            if content:
                                lt = LineTranscription.objects.create(
                                    transcription=trans,
                                    line=l,
                                    content=content)
                            # TODO: store glyphs too
                    part.workflow_state = part.WORKFLOW_STATE_TRANSCRIBING
                    part.save()
                yield part
        except AttributeError as e:
            raise ParseError(e)
