from bs4 import BeautifulSoup

from core.models import *


class ParseError(Exception):
    pass


class AltoParser():
    def __init__(self, file_handler):
        self.soup = BeautifulSoup(file_handler, 'xml')
        try:
            self.pages = self.soup.alto.Layout.find_all('Page')
        except AttributeError:
            raise ParseError
    
    def parse(self, parts):
        def bbox(tag):
            return (
                int(tag.attrs['HPOS']),
                int(tag.attrs['VPOS']),
                int(tag.attrs['HPOS']) + int(tag.attrs['WIDTH']),
                int(tag.attrs['VPOS']) + int(tag.attrs['HEIGHT']),
            )
        trans, created = Transcription.objects.get_or_create(
            document=parts[0].document,
            name='ALTO Import')
        
        try:
            for index, page in enumerate(self.pages):
                part = parts[index]
                part.blocks.all().delete()
                part.lines.all().delete()
                for block in page.find_all('TextBlock'):
                    b = Block.objects.create(document_part=part, box=bbox(block))
                    for line in block.find_all('TextLine'):
                        content = ''
                        for string in line.find_all('String'):
                            content += string.attrs['CONTENT']
                        
                        l = Line.objects.create(
                            document_part=part,
                            block=b,
                            box=bbox(line))
                        lt = LineTranscription.objects.create(
                            transcription=trans,
                            line=l,
                            content=content)
                        # TODO: store glyphs too
                part.workflow_state = part.WORKFLOW_STATE_TRANSCRIBING
                part.save()
        except AttributeError as e:
            raise ParseError(e)
