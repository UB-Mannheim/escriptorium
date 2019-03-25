import os.path
from ftplib import FTP

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from core.models import Document, DocumentPart, Line, Transcription, LineTranscription, document_images_path


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

        part = DocumentPart.objects.create(image=fpath, document=self.document)
        return part
        
    def handle(self, *args, **options):
        self.document = Document.objects.get(pk=options['document_id'])
        # ftp://149.202.76.5/Latin_manuscripts/Bamberg78new/Msc.Class.78/
        ftp = FTP(options['host'])
        ftp.login(user=options['user'], passwd=options['password'])
        ftp.cwd(options['dir'])
        
        if options['csv']:
            file_ = None
            trans = Transcription.objects.create(name='CSV import', document=self.document)
            part = None
            with open(options['csv'], 'r') as fh:
                for line in fh.readlines()[1:]:
                    p,rc,gtc,gtl,x1,y1,x2,y2,x3,y3,x4,y4,sp,fn,ld,fr,sr,cor = line.split('\t')
                    if fn != file_:
                        part = self.grab(ftp, fn.replace('.jpg', '.tif'))
                    file_ = fn
                    l = Line.objects.create(document_part=part, box=(x1,y1,x2,y4))
                    LineTranscription.objects.create(line=l, transcription=trans, content=cor)
        else:
            files = []
            def list_img(filename):
                if os.path.splitext(filename)[1] in ['.tif', '.jpg', '.jpeg', '.png']:
                    files.append(filename.split()[-1])
        
            ftp.dir(lambda a: list_img(a))
            
            for filename in files[:options['limit']]:
                self.grab(ftp, filename)  
        
        ftp.quit()
