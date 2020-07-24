import bleach
import logging

from django.conf import settings
from django.db.utils import IntegrityError

from rest_framework import serializers
from easy_thumbnails.files import get_thumbnailer

from users.models import User
from core.models import (Document,
                         DocumentPart,
                         Block,
                         Line,
                         Transcription,
                         LineTranscription,
                         BlockType,
                         LineType)

logger = logging.getLogger(__name__)


class ImageField(serializers.ImageField):
    def __init__(self, *args, thumbnails=None, **kwargs):
        self.thumbnails = thumbnails
        super().__init__(*args, **kwargs)

    def to_representation(self, img):
        if img:
            data = {'uri': img.url}
            try:
                data['size'] = (img.width, img.height)
            except FileNotFoundError:
                logger.warning('File not found: %s' % img.path)
                data['size'] = None
            else:
                if self.thumbnails:
                    data['thumbnails'] = {}
                    thbn = get_thumbnailer(img)
                    for alias in self.thumbnails:
                        try:
                            data['thumbnails'][alias] = thbn.get_thumbnail(
                                settings.THUMBNAIL_ALIASES[''][alias], generate=False).url
                        except AttributeError:
                            pass
            return data


class PartMoveSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField()

    class Meta:
        model = DocumentPart
        fields = ('index',)

    def __init__(self, *args, part=None, **kwargs):
        self.part = part
        super().__init__(*args, **kwargs)

    def move(self):
        self.part.to(self.validated_data['index'])


class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = ('pk', 'name')

    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        try:
            return super().create(data)
        except IntegrityError:
            return Transcription.objects.get(name=data['name'])


class UserOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('onboarding',)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def complete(self):
        self.user.onboarding = self.validated_data['onboarding']
        self.user.save()


class BlockTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockType
        fields = ('pk', 'name')


class LineTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineType
        fields = ('pk', 'name')


class DocumentSerializer(serializers.ModelSerializer):
    transcriptions = TranscriptionSerializer(many=True, read_only=True)
    valid_block_types = BlockTypeSerializer(many=True, read_only=True)
    valid_line_types = LineTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ('pk', 'name', 'transcriptions',
                  'valid_block_types', 'valid_line_types')


class PartSerializer(serializers.ModelSerializer):
    image = ImageField(thumbnails=['card', 'large'])
    filename = serializers.CharField(read_only=True)
    bw_image = ImageField(thumbnails=['large'], required=False)
    workflow = serializers.JSONField(read_only=True)
    transcription_progress = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocumentPart
        fields = (
            'pk',
            'name',
            'filename',
            'title',
            'typology',
            'image',
            'bw_image',
            'workflow',
            'recoverable',
            'transcription_progress'
        )

    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        data['original_filename'] = data['image'].name
        obj = super().create(data)
        # generate card thumbnail right away since we need it
        get_thumbnailer(obj.image).get_thumbnail(settings.THUMBNAIL_ALIASES['']['card'])
        return obj


class BlockSerializer(serializers.ModelSerializer):
    typology = serializers.PrimaryKeyRelatedField(
        queryset=BlockType.objects.all(),
        allow_null=True,
        required=False)

    class Meta:
        model = Block
        fields = ('pk', 'document_part', 'order', 'box', 'typology')


class LineTranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineTranscription
        fields = ('pk', 'line', 'transcription', 'content',
                  'versions', 'version_author', 'version_source', 'version_updated_at')

    def cleanup(self, data):
        return bleach.clean(data, tags=['em', 'strong', 's', 'u'], strip=True)

    def validate_content(self, content):
        return self.cleanup(content)


class LineListSerializer(serializers.ListSerializer):
    def update(self, qs, validated_data):
        # Maps for id->instance and id->data item.
        line_mapping = {line.pk: line for line in qs}
        data_mapping = {item['pk']: item for item in validated_data}

        # Perform updates.
        ret = []
        for line_id, data in data_mapping.items():
            line = line_mapping.get(line_id, None)
            ret.append(self.child.update(line, data))
        return ret


class LineSerializer(serializers.ModelSerializer):
    pk = serializers.IntegerField(required=False)
    region = serializers.PrimaryKeyRelatedField(
        queryset=Block.objects.all(),
        allow_null=True,
        required=False,
        source='block')
    typology = serializers.PrimaryKeyRelatedField(
        queryset=LineType.objects.all(),
        allow_null=True,
        required=False)

    class Meta:
        model = Line
        fields = ('pk', 'document_part', 'order', 'region', 'baseline', 'mask', 'typology')
        list_serializer_class = LineListSerializer


class LineMoveSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField()

    class Meta:
        model = Line
        fields = ('index',)

    def __init__(self, *args, line=None, **kwargs):
        self.line = line
        super().__init__(*args, **kwargs)

    def move(self):
        self.line.to(self.validated_data['index'])


class LineOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = ('pk', 'order')


class DetailedLineSerializer(LineSerializer):
    transcriptions = LineTranscriptionSerializer(many=True, required=False)

    class Meta(LineSerializer.Meta):
        fields = LineSerializer.Meta.fields + ('transcriptions',)


class PartDetailSerializer(PartSerializer):
    regions = BlockSerializer(many=True, source='blocks')
    lines = LineSerializer(many=True)
    previous = serializers.SerializerMethodField(source='get_previous')
    next = serializers.SerializerMethodField(source='get_next')

    class Meta(PartSerializer.Meta):
        fields = PartSerializer.Meta.fields + (
            'regions',
            'lines',
            'previous',
            'next')

    def get_previous(self, instance):
        prev = DocumentPart.objects.filter(
            document=instance.document, order__lt=instance.order).order_by('-order').first()
        return prev and prev.pk or None

    def get_next(self, instance):
        nex = DocumentPart.objects.filter(
            document=instance.document, order__gt=instance.order).order_by('order').first()
        return nex and nex.pk or None
