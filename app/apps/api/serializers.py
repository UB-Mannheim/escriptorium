import html
import logging

import bleach
from django.conf import settings
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from easy_thumbnails.files import get_thumbnailer
from rest_framework import serializers

from api.fields import DisplayChoiceField
from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    Block,
    BlockType,
    Document,
    DocumentMetadata,
    DocumentPart,
    DocumentPartMetadata,
    DocumentPartType,
    DocumentTag,
    ImageAnnotation,
    ImageAnnotationComponentValue,
    Line,
    LineTranscription,
    LineType,
    Metadata,
    OcrModel,
    OcrModelDocument,
    Project,
    Script,
    TextAnnotation,
    TextAnnotationComponentValue,
    Transcription,
)
from core.tasks import segment, segtrain, train, transcribe
from reporting.models import TaskReport
from users.models import User

logger = logging.getLogger(__name__)


class ImageField(serializers.ImageField):
    def __init__(self, *args, thumbnails=None, **kwargs):
        self.thumbnails = thumbnails
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        if data.content_type == 'application/pdf':
            raise serializers.ValidationError(_("PDF is not a valid image, please use the dedicated Import function."))

        return super().to_internal_value(data)

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


class ScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Script
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    slug = serializers.ReadOnlyField()

    class Meta:
        model = Project
        fields = '__all__'

    def create(self, data):
        data['owner'] = self.context["view"].request.user
        obj = super().create(data)
        return obj


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
        fields = ('pk', 'name', 'archived', 'avg_confidence')

    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        try:
            return super().create(data)
        except IntegrityError:
            return Transcription.objects.get(name=data['name'])


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('pk', 'is_active',
                  'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login',
                  'onboarding')
        read_only_fields = ('date_joined', 'last_login')


class BlockTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockType
        fields = ('pk', 'name')


class LineTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineType
        fields = ('pk', 'name')


class DocumentPartTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentPartType
        fields = ('pk', 'name')


class AnnotationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnotationType
        fields = ('pk', 'name')


class AnnotationComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnotationComponent
        fields = ('pk', 'name', 'allowed_values')

    def create(self, data):
        data['document_id'] = self.context['view'].kwargs['document_pk']
        return super().create(data)


class AnnotationTaxonomySerializer(serializers.ModelSerializer):
    typology = AnnotationTypeSerializer(required=False)
    components = AnnotationComponentSerializer(many=True, required=False)
    marker_type = DisplayChoiceField(AnnotationTaxonomy.MARKER_TYPE_CHOICES, required=True)

    class Meta:
        model = AnnotationTaxonomy
        fields = ('pk', 'name', 'abbreviation',
                  'marker_type', 'marker_detail', 'has_comments',
                  'typology', 'components')

    def create(self, data):
        try:
            components_data = data.pop('components')
        except KeyError:
            components_data = []
        try:
            typo_data = data.pop('typology')
        except KeyError:
            typo_data = None
        if typo_data:
            typo, created = AnnotationType.objects.get_or_create(name=typo_data['name'])
        else:
            typo = None
        data['document_id'] = self.context['view'].kwargs['document_pk']
        taxo = AnnotationTaxonomy.objects.create(
            typology=typo, **data)
        for compo in components_data:
            taxo.components.add(compo)
        return taxo


class ImageAnnotationComponentSerializer(serializers.ModelSerializer):
    value = serializers.CharField(allow_null=True)

    class Meta:
        model = ImageAnnotationComponentValue
        fields = ('pk', 'component', 'value')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['component'] = AnnotationComponentSerializer(instance.component).data
        return representation


class TextAnnotationComponentSerializer(serializers.ModelSerializer):
    value = serializers.CharField(allow_null=True)

    class Meta:
        model = TextAnnotationComponentValue
        fields = ('pk', 'component', 'value')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['component'] = AnnotationComponentSerializer(instance.component).data
        return representation


class ImageAnnotationSerializer(serializers.ModelSerializer):
    components = ImageAnnotationComponentSerializer(many=True)
    as_w3c = serializers.ReadOnlyField()

    class Meta:
        model = ImageAnnotation
        fields = ('pk', 'part', 'comments',
                  'taxonomy', 'components',
                  'coordinates',
                  'as_w3c')

    def create(self, data):
        components_data = data.pop('components')
        anno = ImageAnnotation.objects.create(**data)
        for component in components_data:
            ImageAnnotationComponentValue.objects.create(annotation=anno,
                                                         **component)
        return anno

    def update(self, instance, data):
        components_data = data.pop('components')
        anno = super().update(instance, data)
        for component_value in components_data:
            # for some reason this is an instance of AnnotationComponent
            component, created = ImageAnnotationComponentValue.objects.get_or_create(
                component=component_value['component'],
                annotation=anno)
            component.value = component_value['value']
            component.save()
        return anno


class TextAnnotationSerializer(serializers.ModelSerializer):
    components = TextAnnotationComponentSerializer(many=True)
    as_w3c = serializers.ReadOnlyField()

    class Meta:
        model = TextAnnotation
        fields = ('pk', 'part', 'comments',
                  'taxonomy', 'components',
                  'transcription',
                  'start_line', 'start_offset', 'end_line', 'end_offset',
                  'as_w3c')

    def create(self, data):
        components_data = data.pop('components')
        anno = TextAnnotation.objects.create(**data)
        for component in components_data:
            TextAnnotationComponentValue.objects.create(annotation=anno,
                                                        **component)
        return anno

    def update(self, instance, data):
        components_data = data.pop('components')
        anno = super().update(instance, data)
        for component_value in components_data:
            # for some reason this is an instance of AnnotationComponent
            component, created = TextAnnotationComponentValue.objects.get_or_create(
                component=component_value['component'],
                annotation=anno)
            component.value = component_value['value']
            component.save()
        return anno


class TagDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTag
        fields = ("pk", "name", "color")


class DocumentSerializer(serializers.ModelSerializer):
    main_script = serializers.SlugRelatedField(slug_field='name',
                                               queryset=Script.objects.all())
    transcriptions = TranscriptionSerializer(many=True, read_only=True)
    valid_block_types = BlockTypeSerializer(many=True, read_only=True)
    valid_line_types = LineTypeSerializer(many=True, read_only=True)
    valid_part_types = DocumentPartTypeSerializer(many=True, read_only=True)
    parts_count = serializers.SerializerMethodField()
    project = serializers.SlugRelatedField(slug_field='slug',
                                           queryset=Project.objects.all())

    class Meta:
        model = Document
        fields = ('pk', 'name', 'project', 'transcriptions',
                  'main_script', 'read_direction', 'line_offset', 'show_confidence_viz',
                  'valid_block_types', 'valid_line_types', 'valid_part_types',
                  'parts_count', 'tags', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.for_user_write(self.context['user'])

    def get_parts_count(self, document):
        return document.parts.count()

    def validate_main_script(self, value):
        try:
            return Script.objects.get(name=value)
        except Script.DoesNotExist:
            raise serializers.ValidationError('This script does not exists in the database.')


class DocumentTasksSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    tasks_stats = serializers.SerializerMethodField()
    last_started_task = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ('pk', 'name', 'owner', 'tasks_stats', 'last_started_task')

    def get_owner(self, document):
        return document.owner.username if document.owner else None

    def get_tasks_stats(self, document):
        stats = {state: 0 for state, _ in TaskReport.WORKFLOW_STATE_CHOICES}
        stats.update(dict(document.reports.values('workflow_state').annotate(c=Count('pk')).values_list('workflow_state', 'c')))
        stats = {str(TaskReport.WORKFLOW_STATE_CHOICES[state][1]): count for state, count in stats.items()}
        return stats

    def get_last_started_task(self, document):
        try:
            last_task = document.reports.filter(started_at__isnull=False).latest('started_at')
        except TaskReport.DoesNotExist:
            return None

        return last_task.started_at


class MetadataSerializer(serializers.ModelSerializer):
    name = serializers.CharField(validators=[])

    class Meta:
        model = Metadata
        fields = ('name', 'cidoc_id')

    def create(self, validated_data):
        instance, _ = Metadata.objects.get_or_create(**validated_data)
        return instance


class DocumentMetadataSerializer(serializers.ModelSerializer):
    key = MetadataSerializer()

    class Meta:
        model = DocumentMetadata
        fields = ('pk', 'key', 'value')

    def create(self, validated_data):
        key_data = validated_data.pop('key')
        md, _created = Metadata.objects.get_or_create(**key_data)
        dmd = DocumentMetadata.objects.create(document=self.context['document'],
                                              key=md,
                                              **validated_data)
        return dmd


class DocumentPartMetadataSerializer(serializers.ModelSerializer):
    key = MetadataSerializer()

    class Meta:
        model = DocumentPartMetadata
        fields = ('pk', 'key', 'value')

    def create(self, validated_data):
        key = validated_data.pop('key')
        mdkey = self.fields['key'].create(key)
        pmd = DocumentPartMetadata.objects.create(
            part=self.context['part'],
            key=mdkey,
            **validated_data)
        return pmd

    def update(self, instance, validated_data):
        instance.value = validated_data.get('value', instance.value)
        instance.save()

        if "key" in validated_data:
            new_key = validated_data.get('key')
            nested_serializer = self.fields['key']
            nested_instance = instance.key
            nested_serializer.update(nested_instance, new_key)

        return instance


class PartSerializer(serializers.ModelSerializer):
    image = ImageField(required=False, thumbnails=['card', 'large'])
    image_file_size = serializers.IntegerField(required=False)
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
            'image_file_size',
            'bw_image',
            'workflow',
            'order',
            'recoverable',
            'transcription_progress',
            'source',
            'max_avg_confidence',
            'comments'
        )

    def validate(self, data):
        # If quotas are enforced, assert that the user still has free disk storage
        if not settings.DISABLE_QUOTAS and not self.context['request'].user.has_free_disk_storage():
            raise serializers.ValidationError(_("You don't have any disk storage left."))
        return data

    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        data['original_filename'] = data['image'].name
        data['image_file_size'] = data['image'].size
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
        fields = ('pk', 'document_part', 'external_id', 'order', 'box', 'typology')


class LineTranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineTranscription
        fields = ('pk', 'line', 'transcription', 'content', 'graphs', 'avg_confidence',
                  'versions', 'version_author', 'version_source', 'version_updated_at')

    def cleanup(self, data):
        cleaned_data = bleach.clean(data, tags=['em', 'strong', 's', 'u'], strip=True)
        cleaned_data = html.unescape(cleaned_data)
        return cleaned_data

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
        fields = ('pk', 'document_part', 'external_id', 'order', 'region', 'baseline', 'mask', 'typology')
        extra_kwargs = {
            'order': {'read_only': False, 'required': False}
        }
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
    metadata = DocumentPartMetadataSerializer(many=True)
    previous = serializers.SerializerMethodField(source='get_previous')
    next = serializers.SerializerMethodField(source='get_next')

    class Meta(PartSerializer.Meta):
        fields = PartSerializer.Meta.fields + (
            'regions',
            'lines',
            'previous',
            'metadata',
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
    file_size = serializers.IntegerField(required=False)

    class Meta:
        model = OcrModel
        fields = ('pk', 'name', 'file', 'file_size', 'job',
                  'owner', 'training', 'versions')

    def create(self, data):
        # If quotas are enforced, assert that the user still has free disk storage
        if not settings.DISABLE_QUOTAS and not self.context['request'].user.has_free_disk_storage():
            raise serializers.ValidationError(_("You don't have any disk storage left."))

        data['owner'] = self.context["view"].request.user
        data['file_size'] = data['file'].size
        obj = super().create(data)
        return obj


class ProcessSerializerMixin():
    CHECK_GPU_QUOTA = False
    CHECK_DISK_QUOTA = False

    def __init__(self, document, user, *args, **kwargs):
        self.document = document
        self.user = user
        super().__init__(*args, **kwargs)

    def validate(self, data):
        data = super().validate(data)
        # If quotas are enforced, assert that the user still has free CPU minutes, GPU minutes and disk storage
        if not settings.DISABLE_QUOTAS:
            if not self.user.has_free_cpu_minutes():
                raise serializers.ValidationError(_("You don't have any CPU minutes left."))
            if self.CHECK_GPU_QUOTA and not self.user.has_free_gpu_minutes():
                raise serializers.ValidationError(_("You don't have any GPU minutes left."))
            if self.CHECK_DISK_QUOTA and not self.user.has_free_disk_storage():
                raise serializers.ValidationError(_("You don't have any disk storage left."))
        return data


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
    override = serializers.BooleanField(required=False, default=False)
    text_direction = serializers.ChoiceField(default='horizontal-lr',
                                             required=False,
                                             choices=TEXT_DIRECTION_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['model'].queryset = OcrModel.objects.filter(job=OcrModel.MODEL_JOB_SEGMENT)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def process(self):
        model = self.validated_data.get('model')
        parts = self.validated_data.get('parts')

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'executed_on': timezone.now()}
        )
        if not created:
            ocr_model_document.executed_on = timezone.now()
            ocr_model_document.save()

        for part in parts:
            part.chain_tasks(
                segment.si(instance_pk=part.pk,
                           user_pk=self.user.pk,
                           model_pk=model.pk,
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
    override = serializers.BooleanField(required=False, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['model'].queryset = OcrModel.objects.filter(
            job=OcrModel.MODEL_JOB_SEGMENT
        ).filter(
            Q(public=True) | Q(owner=self.user)
        )
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

        model = data.get('model')
        if not data.get('model_name') and model.owner != self.user and data.get('override'):
            raise serializers.ValidationError(
                "You can't overwrite the existing file of a public model you don't own."
            )

        return data

    def process(self):
        model = self.validated_data.get('model')
        override = self.validated_data.get('override')

        if self.validated_data.get('model_name'):
            file_ = model and model.file or None
            model = OcrModel.objects.create(
                owner=self.user,
                name=self.validated_data['model_name'],
                job=OcrModel.MODEL_JOB_RECOGNIZE,
                file=file_,
                file_size=file_.size if file_ else 0
            )
        elif not override:
            model = model.clone_for_training(self.user, name=self.validated_data['model_name'])

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'trained_on': timezone.now()}
        )
        if not created:
            ocr_model_document.trained_on = timezone.now()
            ocr_model_document.save()

        segtrain.delay(model.pk if model else None,
                       [part.pk for part in self.validated_data.get('parts')],
                       document_pk=self.document.pk,
                       user_pk=self.user.pk)


class TrainSerializer(ProcessSerializerMixin, serializers.Serializer):
    CHECK_GPU_QUOTA = True
    CHECK_DISK_QUOTA = True

    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all())
    model = serializers.PrimaryKeyRelatedField(required=False,
                                               queryset=OcrModel.objects.all())
    model_name = serializers.CharField(required=False)
    transcription = serializers.PrimaryKeyRelatedField(queryset=Transcription.objects.all())
    override = serializers.BooleanField(required=False, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)
        self.fields['model'].queryset = OcrModel.objects.filter(
            job=OcrModel.MODEL_JOB_RECOGNIZE
        ).filter(
            Q(public=True) | Q(owner=self.user)
        )
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def validate(self, data):
        data = super().validate(data)

        if not data.get('model') and not data.get('model_name'):
            raise serializers.ValidationError(
                _("Either use model_name to create a new model, or add a model pk to retrain an existing one."))

        model = data.get('model')
        if not data.get('model_name') and model.owner != self.user and data.get('override'):
            raise serializers.ValidationError(
                "You can't overwrite the existing file of a model you don't own."
            )

        return data

    def process(self):
        model = self.validated_data.get('model')
        override = self.validated_data.get('override')

        if self.validated_data.get('model_name'):
            file_ = model and model.file or None
            model = OcrModel.objects.create(
                owner=self.user,
                name=self.validated_data['model_name'],
                job=OcrModel.MODEL_JOB_RECOGNIZE,
                file=file_,
                file_size=file_.size if file_ else 0
            )
        elif not override:
            model = model.clone_for_training(self.user, name=self.validated_data['model_name'])

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'trained_on': timezone.now()}
        )
        if not created:
            ocr_model_document.trained_on = timezone.now()
            ocr_model_document.save()

        train.delay(self.validated_data['transcription'].pk,
                    model.pk if model else None,
                    part_pks=[part.pk for part in self.validated_data.get('parts')],
                    user_pk=self.user.pk)


class TranscribeSerializer(ProcessSerializerMixin, serializers.Serializer):
    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all())
    model = serializers.PrimaryKeyRelatedField(queryset=OcrModel.objects.all())
    # transcription = serializers.PrimaryKeyRelatedField(queryset=Transcription.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)
        self.fields['model'].queryset = OcrModel.objects.filter(job=OcrModel.MODEL_JOB_RECOGNIZE)
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def process(self):
        model = self.validated_data.get('model')

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'executed_on': timezone.now()}
        )
        if not created:
            ocr_model_document.executed_on = timezone.now()
            ocr_model_document.save()

        for part in self.validated_data.get('parts'):
            part.chain_tasks(
                transcribe.si(instance_pk=part.pk,
                              model_pk=model.pk,
                              user_pk=self.user.pk)
            )
