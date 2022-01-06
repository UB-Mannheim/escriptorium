import os.path
# from ftplib import FTP

from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import Document, DocumentPart, Line, Transcription, LineTranscription


class Command(BaseCommand):
    help = 'Import the content of a ftp directory in the given Document.'

    def add_arguments(self, parser):
        parser.add_argument('host', type=str)
        parser.add_argument('document_id', type=int)
        parser.add_argument('-d', '--dir', type=str, default='/')
        parser.add_argument('-u', '--user', type=str)
        parser.add_argument('-p', '--password', type=str)
        parser.add_argument('-l', '--limit', type=int, default=0)
        parser.add_argument('-c', '--csv', type=str)
        
    def grab(self, ftp, filename):
        print('Fetching %s' % filename)
        fpath = 'documents/%d/%s' % (self.document.pk, filename)
        fullpath = os.path.join(settings.MEDIA_ROOT, fpath)
        if not os.path.exists(os.path.dirname(fullpath)):
            try:
                os.makedirs(os.path.dirname(fullpath))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
            
        with open(fullpath, 'wb+') as fh:
            ftp.retrbinary('RETR ' + filename, fh.write, 1024)

        part = DocumentPart.objects.create(image=fpath, image_file_size=os.path.getsize(fpath), document=self.document)
        return part
        
    def handle(self, *args, **options):
        self.document = Document.objects.get(pk=options['document_id'])
        # ftp://149.202.76.5/Latin_manuscripts/Bamberg78new/Msc.Class.78/
        # ftp = FTP(options['host'])
        # ftp.login(user=options['user'], passwd=options['password'])
        # ftp.cwd(options['dir'])
        
        if options['csv']:
            file_ = None
            trans, created = Transcription.objects.get_or_create(name='Import newBNF150zuckerguss_12275_97p2.mlmodel', document=self.document)
            trans_gt, created = Transcription.objects.get_or_create(name='Import GT', document=self.document)
            part = None
            with open(options['csv'], 'r') as fh:
                for line in fh.readlines()[1:]:
                    #order,page,realCol,GTcol,GTline,x1,y1,x2,y2,x3,y3,x4,y4,siftflowpoints,fn,linedistance,folioreference,sourcereference,manual_correction,comment = line.split('\t')
                    order,page,regionNumber,x1Region,y1Region,x2Region,y2Region,lineNumber,x1line,y1line,x2line,y2line,fn,AT,GT2  = line.split('\t')
                    if fn != file_:
                        # part = self.grab(ftp, fn.replace('.jpg', '.tif'))
                        part = DocumentPart.objects.get(image__contains=fn.split('__')[1], document=self.document)
                        part.lines.all().delete()
                        part.blocks.all().delete()
                        block = Block.objects.get_or_create(document_part=part,box=(x1Region,y1Region,x2Region,y2Region))
                    file_ = fn

                    l = Line.objects.create(document_part=part, block=block, box=(x1line, y1line, x2line, y2line))
                    LineTranscription.objects.create(line=l, transcription=trans, content=AT)
                    if GT2:
                        LineTranscription.objects.create(line=l, transcription=trans_gt, content=GT2)
        else:
            files = []
            def list_img(filename):
                if os.path.splitext(filename)[1] in ['.tif', '.jpg', '.jpeg', '.png']:
                    files.append(filename.split()[-1])
        
            ftp.dir(lambda a: list_img(a))
            
            for filename in files[:options['limit']]:
                self.grab(ftp, filename)  
        
        ftp.quit()
