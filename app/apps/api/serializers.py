import bleach
import logging
import html
import json

from django.conf import settings
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404

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
                         LineType,
                         OcrModel,
                         AlreadyProcessingException)

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
    class Meta:
        model = OcrModel
        fields = ('pk', 'name','file','job','owner','training','training_epoch',
                  'training_accuracy','training_total','training_errors','document','script',)


class DocumentProcessSerializer(serializers.Serializer):

    TASK_BINARIZE = 'binarize'
    TASK_SEGMENT = 'segment'
    TASK_TRAIN = 'train'
    TASK_SEGTRAIN = 'segtrain'
    TASK_TRANSCRIBE = 'transcribe'

    parts = serializers.ListField(
            child=serializers.IntegerField()
    )

    task = serializers.ChoiceField(required=True,
        choices = (
            (TASK_BINARIZE, TASK_BINARIZE),
            (TASK_SEGMENT, TASK_BINARIZE),
            (TASK_TRAIN, TASK_BINARIZE),
            (TASK_TRANSCRIBE, TASK_BINARIZE),
            (TASK_SEGTRAIN, TASK_BINARIZE),
        )
    )

    # binarization
    bw_image = serializers.ImageField(required=False)
    BINARIZER_CHOICES = (('kraken', _("Kraken")),)
    binarizer = serializers.ChoiceField(required=False,
                                  choices=BINARIZER_CHOICES,
                                  initial='kraken')
    threshold = serializers.FloatField(
        required=False, initial=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(1)],
        help_text=_('Increase it for low contrast documents, if the letters are not visible enough.'),
    )
    # segment
    SEG_STEPS_CHOICES = (
        ('both', _('Lines and regions')),
        ('lines', _('Lines Baselines and Masks')),
        ('masks', _('Only lines Masks')),
        ('regions', _('Regions')),
    )

    seg_steps = serializers.ChoiceField(choices=SEG_STEPS_CHOICES,
                                           initial='both', required=False)
    seg_model = serializers.IntegerField(required=False)

    override = serializers.BooleanField(required=False, initial=True,
                                  help_text=_(
                                      "If checked, deletes existing segmentation <b>and bound transcriptions</b> first!"))
    TEXT_DIRECTION_CHOICES = (('horizontal-lr', _("Horizontal l2r")),
                              ('horizontal-rl', _("Horizontal r2l")),
                              ('vertical-lr', _("Vertical l2r")),
                              ('vertical-rl', _("Vertical r2l")))
    text_direction = serializers.ChoiceField(initial='horizontal-lr', required=False,
                                       choices=TEXT_DIRECTION_CHOICES)
    # transcribe
    upload_model = serializers.FileField(required=False,
                                   validators=[FileExtensionValidator(
                                       allowed_extensions=['mlmodel', 'pronn', 'clstm'])])

    ocr_model = serializers.IntegerField(required=False)

    # train
    new_model = serializers.CharField(required=False, label=_('Model name'))
    train_model = OcrModelSerializer(required=False)
    transcription = serializers.PrimaryKeyRelatedField(many=False,read_only=True)

    # segtrain
    segtrain_model = serializers.IntegerField(required=False)

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        self.document_parts = []
        if self.document.read_direction == self.document.READ_DIRECTION_RTL:
            self.initial['text_direction'] = 'horizontal-rl'
        super().__init__(*args, **kwargs)

    def validate_bw_image(self,img):
        if not img:
            return
        if len(self.document_parts) != 1:
            raise serializers.ValidationError({'bw_image':_("Uploaded image with more than one selected image.")})
        # Beware: don't close the file here !
        fh = Image.open(img)
        if fh.mode not in ['1', 'L']:
            raise serializers.ValidationError({'bw_image':_("Uploaded image should be black and white.")})
        isize = (self.document_parts[0].image.width, self.document_parts[0].image.height)
        if fh.size != isize:
            raise serializers.ValidationError({'bw_image':_("Uploaded image should be the same size as original image {size}.").format(size=isize)})
        return img

    def validate_train_model(self,train_model):

        if train_model and train_model.training:
            raise AlreadyProcessingException
        return train_model

    def validate_seg_model(self, value):
        model = get_object_or_404(OcrModel, pk=value)
        return model

    def validate_ocr_model(self, value):
        model = get_object_or_404(OcrModel, pk=value)
        return model

    def validate_segtrain_model(self, value):
        model = get_object_or_404(OcrModel, pk=value)
        return model

    def validate(self, data):

        task = data['task']
        parts = data['parts']

        self.document_parts = DocumentPart.objects.filter(
            document=self.document, pk__in=parts)

        if task == self.TASK_SEGMENT:
            model_job = OcrModel.MODEL_JOB_SEGMENT
        elif task == self.TASK_SEGTRAIN:
            model_job = OcrModel.MODEL_JOB_SEGMENT
            if task == self.TASK_SEGTRAIN and len(parts) < 2:
                raise serializers.ValidationError("Segmentation training requires at least 2 images.")
        else:
            model_job = OcrModel.MODEL_JOB_RECOGNIZE

        if task == self.TASK_TRAIN and data.get('train_model'):
            model = data.get('train_model')
        elif task == self.TASK_SEGTRAIN and data.get('segtrain_model'):
            model = data.get('segtrain_model')
        elif data.get('upload_model'):
            model = OcrModel.objects.create(
                document=self.document_parts[0].document,
                owner=self.user,
                name=data['upload_model'].name.rsplit('.', 1)[0],
                job=model_job)
            # Note: needs to save the file in a second step because the path needs the db PK
            model.file = data['upload_model']
            model.save()

        elif data.get('new_model'):
            # file will be created by the training process
            model = OcrModel.objects.create(
                document=self.document_parts[0].document,
                owner=self.user,
                name=data['new_model'],
                job=model_job)
        elif data.get('ocr_model'):
            model = data.get('ocr_model')
        elif data.get('seg_model'):
            model = data.get('seg_model')
        else:
            if task in (self.TASK_TRAIN, self.TASK_SEGTRAIN):
                raise serializers.ValidationError(
                    _("Either select a name for your new model or an existing one."))
            else:
                model = None

        data['model'] = model
        return data

    def process(self):

        task = self.validated_data.get('task')

        model = self.validated_data.get('model')
        if task == self.TASK_BINARIZE:
            if len(self.document_parts) == 1 and self.validated_data.get('bw_image'):
                self.document_parts[0].bw_image = self.validated_data['bw_image']
                self.document_parts[0].save()
            else:
                for part in self.document_parts:
                    part.task('binarize',
                              user_pk=self.user.pk,
                              threshold=self.validated_data.get('threshold'))

        elif task == self.TASK_SEGMENT:
            for part in self.document_parts:
                part.task('segment',
                          user_pk=self.user.pk,
                          steps=self.validated_data.get('seg_steps'),
                          text_direction=self.validated_data.get('text_direction'),
                          model_pk=model and model.pk or None,
                          override=self.validated_data.get('override'))

        elif task == self.TASK_TRANSCRIBE:
            for part in self.document_parts:
                part.task('transcribe',
                          user_pk=self.user.pk,
                          model_pk=model and model.pk or None)

        elif task == self.TASK_TRAIN:
            model.train(self.document_parts,
                        self.validated_data['transcription'],
                        user=self.user)

        elif task == self.TASK_SEGTRAIN:
            model.segtrain(self.document,
                           self.document_parts,
                           user=self.user)