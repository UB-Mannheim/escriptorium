import bleach
import logging
import html

from django.conf import settings
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from easy_thumbnails.files import get_thumbnailer

from api.fields import DisplayChoiceField
from users.models import User
from core.models import (Document,
                         DocumentPart,
                         Block,
                         Line,
                         Transcription,
                         LineTranscription,
                         BlockType,
                         LineType,
                         OcrModel)
from core.tasks import (segtrain, train, segment, transcribe)

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
    image = ImageField(required=False, thumbnails=['card', 'large'])
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
        nd = bleach.clean(data, tags=['em', 'strong', 's', 'u'], strip=True)
        nd = html.unescape(nd)
        return nd

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


class LineOrderListSerializer(serializers.ListSerializer):
    def update(self, qs, validated_data):
        # Maps for id->instance and id->data item.
        line_mapping = {line.pk: line for line in qs}
        data_mapping = {item['pk']: item for item in validated_data}

        # we can only go down or up (not both)
        first_ = qs[0]
        down = first_.order < data_mapping[first_.pk]['order']
        lines = list(data_mapping.items())
        lines.sort(key=lambda l: l[1]['order'])
        if down:
            # reverse to avoid pushing up already moved lines
            lines.reverse()

        for i, (line_id, data) in enumerate(lines):
            line = line_mapping.get(line_id, None)
            line.to(data['order'])

        line.document_part.enforce_line_order()
        # returns all new ordering for the whole page
        data = self.child.__class__(line.document_part.lines.all(), many=True).data
        return data


class LineOrderSerializer(serializers.ModelSerializer):
    pk = serializers.IntegerField()
    order = serializers.IntegerField()

    class Meta:
        model = Line
        fields = ('pk', 'order')
        list_serializer_class = LineOrderListSerializer


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


class OcrModelSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    job = DisplayChoiceField(choices=OcrModel.MODEL_JOB_CHOICES)
    training = serializers.ReadOnlyField()

    class Meta:
        model = OcrModel
        fields = ('pk', 'name', 'file', 'job',
                  'owner', 'training', 'versions')

    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        data['owner'] = self.context["view"].request.user
        obj = super().create(data)
        return obj


class ProcessSerializerMixin():
    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)


class SegmentSerializer(ProcessSerializerMixin, serializers.Serializer):
    STEPS_CHOICES = (
        ('both', _('Lines and regions')),
        ('lines', _('Lines Baselines and Masks')),
        ('masks', _('Only lines Masks')),
        ('regions', _('Regions')),
    )
    TEXT_DIRECTION_CHOICES = (
        ('horizontal-lr', _("Horizontal l2r")),
        ('horizontal-rl', _("Horizontal r2l")),
        ('vertical-lr', _("Vertical l2r")),
        ('vertical-rl', _("Vertical r2l"))
    )

    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all())
    steps = serializers.ChoiceField(choices=STEPS_CHOICES,
                                    required=False,
                                    default='both')
    model = serializers.PrimaryKeyRelatedField(required=False,
                                               allow_null=True,
                                               queryset=OcrModel.objects.all())
    override = serializers.BooleanField(required=False, default=True)
    text_direction = serializers.ChoiceField(default='horizontal-lr',
                                             required=False,
                                             choices=TEXT_DIRECTION_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['model'].queryset = OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT,
                                                                document=self.document)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def process(self):
        model = self.validated_data.get('model')
        parts = self.validated_data.get('parts')
        for part in parts:
            part.chain_tasks(
                segment.si(part.pk,
                           user_pk=self.user.pk,
                           model_pk=model,
                           steps=self.validated_data.get('steps'),
                           text_direction=self.validated_data.get('text_direction'),
                           override=self.validated_data.get('override'))
            )


class SegTrainSerializer(ProcessSerializerMixin, serializers.Serializer):
    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all())
    model = serializers.PrimaryKeyRelatedField(required=False,
                                               queryset=OcrModel.objects.all())
    model_name = serializers.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['model'].queryset = OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT,
                                                                document=self.document)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def validate_parts(self, data):
        if len(data) < 2:
            raise serializers.ValidationError("Segmentation training requires at least 2 images.")
        return data

    def validate(self, data):
        data = super().validate(data)
        if not data.get('model') and not data.get('model_name'):
            raise serializers.ValidationError(
                _("Either use model_name to create a new model, add a model pk to retrain an existing one, or both to create a new model from an existing one."))
        return data

    def process(self):
        model = self.validated_data.get('model')
        if self.validated_data.get('model_name'):
            file_ = model and model.file or None
            model = OcrModel.objects.create(
                document=self.document,
                owner=self.user,
                name=self.validated_data['model_name'],
                job=OcrModel.MODEL_JOB_RECOGNIZE,
                file=file_
            )

        segtrain.delay(model.pk if model else None,
                       [part.pk for part in self.validated_data.get('parts')],
                       user_pk=self.user.pk)


class TrainSerializer(ProcessSerializerMixin, serializers.Serializer):
    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all())
    model = serializers.PrimaryKeyRelatedField(required=False,
                                               queryset=OcrModel.objects.all())
    model_name = serializers.CharField(required=False)
    transcription = serializers.PrimaryKeyRelatedField(queryset=Transcription.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)
        self.fields['model'].queryset = OcrModel.objects.filter(job=OcrModel.MODEL_JOB_RECOGNIZE,
                                                                document=self.document)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def validate(self, data):
        data = super().validate(data)
        if not data.get('model') and not data.get('model_name'):
            raise serializers.ValidationError(
                    _("Either use model_name to create a new model, or add a model pk to retrain an existing one."))
        return data

    def process(self):
        model = self.validated_data.get('model')
        if self.validated_data.get('model_name'):
            file_ = model and model.file or None
            model = OcrModel.objects.create(
                document=self.document,
                owner=self.user,
                name=self.validated_data['model_name'],
                job=OcrModel.MODEL_JOB_RECOGNIZE,
                file=file_)

        train.delay([part.pk for part in self.validated_data.get('parts')],
                    self.validated_data['transcription'].pk,
                    model.pk if model else None,
                    self.user.pk)


class TranscribeSerializer(ProcessSerializerMixin, serializers.Serializer):
    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all())
    model = serializers.PrimaryKeyRelatedField(queryset=OcrModel.objects.all())
    # transcription = serializers.PrimaryKeyRelatedField(queryset=Transcription.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)
        self.fields['model'].queryset = OcrModel.objects.filter(job=OcrModel.MODEL_JOB_RECOGNIZE,
                                                                document=self.document)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def process(self):
        model = self.validated_data.get('model')
        for part in self.validated_data.get('parts'):
            part.chain_tasks(
                transcribe.si(part.pk,
                              model_pk=model.pk,
                              user_pk=self.user.pk)
            )
