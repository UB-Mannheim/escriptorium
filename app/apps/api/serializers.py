import json

from rest_framework import serializers

from core.models import *


class ImageField(serializers.ImageField):
    def to_representation(self, img):
        if img:
            return {
                'uri': img.url,
                'size': (img.width, img.height)
            }


class ThumbnailField(ImageField):
    def __init__(self, *args, alias=None, **kwargs):
        self.tb_alias = alias
        super().__init__(*args, **kwargs)
    
    def to_representation(self, img):
        thumbnailer = get_thumbnailer(img)[self.tb_alias]
        return super().to_representation(thumbnailer)


class PartMoveSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField()
    
    class Meta:
        model = DocumentPart
        fields = ('index',)
    
    def __init__(self, *args, part=None, **kwargs):
        self.part = part
        super().__init__(*args, **kwargs)
    
    def move(self):
        print(self.validated_data)
        self.part.to(self.validated_data['index'])


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('pk', 'name')


class PartSerializer(serializers.ModelSerializer):
    image = ImageField()
    bw_image = ImageField(required=False)
    thumbnail = ThumbnailField(source='image', alias='card', read_only=True)
    workflow = serializers.JSONField(read_only=True)
    transcription_progress = serializers.IntegerField(read_only=True)
    
    def create(self, data):
        data['document'] = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        return super().create(data)
    
    class Meta:
        model = DocumentPart
        fields = (
            'pk',
            'name',
            'title',
            'typology',
            'image',
            'bw_image',
            'thumbnail',
            'workflow',
            'transcription_progress'
        )


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ('pk', 'order', 'document_part', 'box')


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = ('pk', 'order', 'document_part', 'block', 'box')


class PartDetailSerializer(PartSerializer):
    blocks = BlockSerializer(many=True)
    lines = LineSerializer(many=True)
    
    class Meta(PartSerializer.Meta):
        fields = PartSerializer.Meta.fields + (
            'blocks',
            'lines'
        )
