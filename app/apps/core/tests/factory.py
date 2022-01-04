from PIL import Image, ImageDraw
from io import BytesIO
import uuid
import os.path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from django_redis import get_redis_connection
from kraken.lib import vgsl

from core.models import (Block,
                         Document,
                         DocumentPart,
                         Transcription,
                         Line,
                         LineTranscription,
                         OcrModel,
                         Project)
from users.models import User


redis_ = get_redis_connection()


class CoreFactory():
    """
    A model Factory to help create data for tests.
    """
    def __init__(self):
        redis_.flushall()
        self.cleanup_registry = []

    def cleanup(self):
        for obj in self.cleanup_registry:
            obj.delete()

    def make_user(self):
        name = 'test-%s' % str(uuid.uuid1())
        return User.objects.create(
            username=name,
            email='%s@test.com' % name
        )

    def make_project(self, **kwargs):
        project, _ = Project.objects.get_or_create(
            slug="test",
            defaults={
                "owner": kwargs.get('owner') or self.make_user(),
                "name": kwargs.get('name') or "Unit test"
            }
        )
        return project

    def make_document(self, **kwargs):
        attrs = kwargs.copy()
        attrs['owner'] = attrs.get('owner') or self.make_user()
        attrs['project'] = attrs.get('project') or self.make_project(owner=attrs['owner'])
        attrs['name'] =  attrs.get('name') or 'test doc'
        return Document.objects.create(**attrs)

    def make_part(self, **kwargs):
        if 'image_asset' in kwargs:
            img = self.make_asset_file(asset_name=kwargs.pop('image_asset'))
        else:
            img = self.make_asset_file()
        attrs = kwargs.copy()
        attrs['document'] = attrs.get('document') or self.make_document()

        attrs.setdefault('image', SimpleUploadedFile(
            name=img.name,
            content=img.read(),
            content_type='image/png'))
        attrs.setdefault('image_file_size', os.path.getsize(img.name))

        part = DocumentPart.objects.create(**attrs)
        self.cleanup_registry.append(part)
        return part

    def make_transcription(self, **kwargs):
        attrs = kwargs.copy()
        attrs['document'] = attrs.get('document') or self.make_document()
        attrs.setdefault('name', 'test trans')
        tr = Transcription.objects.create(**attrs)
        return tr

    def make_image_file(self, name='test.png'):
        file = BytesIO()
        file.name = name
        image = Image.new('RGB', size=(60, 60), color=(155, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle([20, 20, 30, 30], fill=(0, 0, 155))
        draw.polygon([(20, 20), (20, 30), (25, 15)], fill=(0, 155, 0))
        image.save(file, 'png')
        file.seek(0)
        return file

    def make_asset_file(self, name='test.png', asset_name='segmentation/default.png'):
        fp = os.path.join(os.path.dirname(__file__), 'assets', asset_name)
        return open(fp, 'rb')

    def make_model(self, document, job=OcrModel.MODEL_JOB_RECOGNIZE):
        spec = '[1,48,0,1 Lbx100 Do O1c10]'
        nn = vgsl.TorchVGSLModel(spec)
        model_name = 'test.mlmodel'
        model = OcrModel.objects.create(name=model_name,
                                        owner=document.owner,
                                        job=job,
                                        file_size=0)

        document.ocr_models.add(model)
        modeldir = os.path.join(settings.MEDIA_ROOT, os.path.split(
            model.file.field.upload_to(model, 'test.mlmodel'))[0])
        if not os.path.exists(modeldir):
            os.makedirs(modeldir)
        modelpath = os.path.join(modeldir, model_name)
        nn.save_model(path=modelpath)
        model.file = modelpath
        model.file_size = model.file.size
        model.save()
        return model

    def make_content(self, part, amount=30, transcription=None):
        line_height = 30
        line_width = 50
        line_margin = 10

        if transcription is None:
            transcription = self.make_transcription(document=part.document)
        for i in range(amount):
            block = Block.objects.create(document_part=part, box=[
                line_margin, i*line_height-line_margin,
                line_margin+line_width, i*line_height-line_margin
            ])
            line = Line.objects.create(document_part=part,
                                       baseline=[
                                           [line_margin, i*line_height],
                                           [line_margin+line_width, i*line_height]],
                                       mask=[
                                           [line_margin, i*line_height+line_margin],
                                           [line_margin+line_width, i*line_height+line_margin],
                                           [line_margin+line_width, i*line_height-line_margin],
                                           [line_margin, i*line_height-line_margin],
                                       ],
                                       block=block)
            LineTranscription.objects.create(transcription=transcription,
                                             line=line,
                                             content='test %d' % i)


class CoreFactoryTestCase(TestCase):
    def setUp(self):
        self.factory = CoreFactory()

    def tearDown(self):
        self.factory.cleanup()
