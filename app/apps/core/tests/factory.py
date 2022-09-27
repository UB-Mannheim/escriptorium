import os.path
import uuid
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django_redis import get_redis_connection
from kraken.lib import vgsl
from PIL import Image, ImageDraw

from core.models import (
    Block,
    BlockType,
    Document,
    DocumentPart,
    Line,
    LineTranscription,
    Metadata,
    OcrModel,
    Project,
    TextualWitness,
    Transcription,
)
from users.models import Group, User

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

    def make_user(self, group_name=None):
        name = 'test-%s' % str(uuid.uuid1())
        return User.objects.create(
            username=name,
            email='%s@test.com' % name
        )

    def make_group(self, users=None):
        name = 'group-%s' % str(uuid.uuid1())
        group = Group.objects.create(name=name)
        if users:
            for user in users:
                user.groups.add(group)
        return group

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
        attrs['name'] = attrs.get('name') or 'test doc'
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

    def make_part_metadata(self, part, **kwargs):
        attrs = kwargs.copy()
        if 'name' not in kwargs:
            attrs['name'] = 'testmd'
        key = Metadata.objects.create(**attrs)
        return part.metadata.create(key=key, value='testmdvalue')

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

        # Lines of randomized garbage text to use for transcription content
        f = open(os.path.join(os.path.dirname(__file__), "assets", "lines.txt"), "r")
        lines = f.readlines()

        if transcription is None:
            transcription = self.make_transcription(document=part.document)
        block_type = BlockType.objects.create(name="blocktype", public=True, default=True)
        part.document.valid_block_types.add(block_type)
        for i in range(amount):
            block = Block.objects.create(
                document_part=part,
                typology=block_type,
                box=[
                    line_margin, i * line_height - line_margin,
                    line_margin + line_width, i * line_height - line_margin
                ],
            )
            line = Line.objects.create(document_part=part,
                                       baseline=[
                                           [line_margin, i * line_height],
                                           [line_margin + line_width, i * line_height]],
                                       mask=[
                                           [line_margin, i * line_height + line_margin],
                                           [line_margin + line_width, i * line_height + line_margin],
                                           [line_margin + line_width, i * line_height - line_margin],
                                           [line_margin, i * line_height - line_margin],
                                       ],
                                       block=block)

            LineTranscription.objects.create(transcription=transcription,
                                             line=line,
                                             content=lines[i])

    def make_witness(self, **kwargs):
        """Generate a textual witness (reference text) for use in alignment"""
        # text of transcription with random minor changes
        f = open(os.path.join(os.path.dirname(__file__), "assets", "alignment/witness.txt"), "rb")
        attrs = kwargs.copy()
        attrs["owner"] = attrs.get("owner") or self.make_user()
        attrs["name"] = attrs.get("name") or "fake_textual_witness"
        return TextualWitness.objects.create(
            file=SimpleUploadedFile(
                name="witness.txt",
                content=f.read(),
                content_type="text/plain",
            ),
            **attrs,
        )


class CoreFactoryTestCase(TransactionTestCase):
    def setUp(self):
        self.factory = CoreFactory()

    def tearDown(self):
        self.factory.cleanup()
