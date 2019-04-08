import bleach
import logging
import json

from django.conf import settings
from rest_framework import serializers
import easy_thumbnails

from core.models import *

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
                try:
                    if settings.THUMBNAIL_ENABLE and self.thumbnails:
                        data['thumbnails'] = {alias: get_thumbnailer(img)[alias].url
                                              for alias in self.thumbnails}
                except easy_thumbnails.exceptions.InvalidImageFormatError:
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


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('pk', 'name')


class PartSerializer(serializers.ModelSerializer):
    image = ImageField(thumbnails=['card', 'large'])
    bw_image = ImageField(thumbnails=['large'], required=False)
    workflow = serializers.JSONField(read_only=True)
    transcription_progress = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = DocumentPart
        fields = (
            'pk',
            'name',
            'title',
            'typology',
            'image',
            'bw_image',
            'workflow',
            'transcription_progress'
        )
    
    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        return super().create(data)


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ('pk', 'order', 'document_part', 'box')


class LineTranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineTranscription
        fields = ('pk', 'line', 'transcription', 'content', 'versions')
        
    def cleanup(self, data):
        return bleach.clean(data, tags=['em', 'strong', 's', 'u'], strip=True)
    
    def create(self, validated_data):
        validated_data['content'] = self.cleanup(validated_data['content'])
        instance = super().create(validated_data)
        instance.line.document_part.recalculate_ordering()
        return instance
    
    def update(self, instance, validated_data):
        validated_data['content'] = self.cleanup(validated_data['content'])
        instance.line.document_part.recalculate_ordering()
        return super().update(instance, validated_data)


class LineSerializer(serializers.ModelSerializer):
    transcriptions = LineTranscriptionSerializer(many=True, required=False)
    
    class Meta:
        model = Line
        fields = ('pk', 'order', 'document_part', 'block', 'box', 'transcriptions')


class PartDetailSerializer(PartSerializer):
    blocks = BlockSerializer(many=True)
    lines = LineSerializer(many=True)
    previous = serializers.SerializerMethodField(source='get_previous')
    next = serializers.SerializerMethodField(source='get_next')
    
    class Meta(PartSerializer.Meta):
        fields = PartSerializer.Meta.fields + (
            'blocks',
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
