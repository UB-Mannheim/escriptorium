from PIL import Image, ImageDraw
from io import BytesIO
import uuid

from django.conf import settings
from django.db.utils import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import *
from users.models import User


class CoreFactory():
    """
    A model Factory to help create data for tests.
    """
    def make_user(self):
        name = 'test-%s' % str(uuid.uuid1())
        return User.objects.create(
            username=name,
            email='%s@test.com' % name
        )
    
    def make_document(self, **kwargs):
        attrs = kwargs.copy()
        attrs['owner'] = attrs.get('owner') or self.make_user()
        attrs.setdefault('name', 'test doc')
        return Document.objects.create(**attrs)
    
    def make_part(self, **kwargs):
        attrs = kwargs.copy()
        attrs['document'] = attrs.get('document') or self.make_document()
        img = self.make_image_file()
        attrs.setdefault('image', SimpleUploadedFile(
            name=img.name,
            content=img.read(),
            content_type='image/png'))
        
        return DocumentPart.objects.create(**attrs)
    
    def make_transcription(self, **kwargs):
        attrs = kwargs.copy()
        attrs['document'] = attrs.get('document') or self.make_document()
        attrs.setdefault('name', 'test trans')
        return Transcription.objects.create(**attrs)
    
    def make_image_file(self):
        file = BytesIO()
        file.name = 'test.png'
        image = Image.new('RGB', size=(50, 50), color=(155, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle([20,20,30,30], fill=(0,0,155))
        draw.polygon([(20,20),(20,30), (25,15)], fill=(0,155,0))
        image.save(file, 'png')
        file.seek(0)
        return file
