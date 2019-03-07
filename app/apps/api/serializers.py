import json

from rest_framework import serializers

from core.models import *


class ImageField(serializers.ImageField):
    def __init__(self, *args, thumbnails=None, **kwargs):
        self.thumbnails = thumbnails
        super().__init__(*args, **kwargs)
    
    def to_representation(self, img):
        if img:
            data = {
                'uri': img.url,
                'size': (img.width, img.height),
            }
            if self.thumbnails:
                data['thumbnails'] = {alias: get_thumbnailer(img)[alias].url
                                      for alias in self.thumbnails}
            return data


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
    image = ImageField(thumbnails=['card', 'large'])
    bw_image = ImageField(thumbnails=['large'], required=False)
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
            'workflow',
            'transcription_progress'
        )


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ('pk', 'order', 'document_part', 'box')
    

class LineTranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineTranscription
        fields = ('pk', 'line', 'transcription', 'content', 'versions')


class LineSerializer(serializers.ModelSerializer):
    transcriptions = LineTranscriptionSerializer(many=True)
    
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
            'next'
        )

    def get_previous(self, instance):
        prev = DocumentPart.objects.filter(
            document=instance.document, order__lt=instance.order).order_by('-order').first()
        return prev and prev.pk or None

    def get_next(self, instance):
        nex = DocumentPart.objects.filter(
            document=instance.document, order__gt=instance.order).order_by('order').first()
        return nex and nex.pk or None
