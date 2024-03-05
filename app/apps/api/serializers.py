import html
import logging
import os.path

import bleach
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from easy_thumbnails.files import get_thumbnailer
from rest_framework import fields, serializers

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
    ProjectTag,
    Script,
    TextAnnotation,
    TextAnnotationComponentValue,
    TextualWitness,
    Transcription,
)
from core.tasks import segment, segtrain, train, transcribe
from imports.forms import FileImportError, clean_import_uri, clean_upload_file
from imports.models import DocumentImport
from imports.tasks import document_import
from reporting.models import TaskReport
from users.consumers import send_event
from users.models import Group, User

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


class UserSerializer(serializers.ModelSerializer):
    can_invite = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('pk', 'is_active',
                  'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login', 'is_staff', 'can_invite')
        read_only_fields = ('date_joined', 'last_login', 'is_staff', 'can_invite')

    def get_can_invite(self, user):
        return user.has_perms(['user.can_invite'])


class DetailedGroupSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True, source='user_set')
    owner = serializers.ReadOnlyField(source='groupowner.owner.pk')

    class Meta:
        model = Group
        fields = ('pk', 'name', 'users', 'owner')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('pk', 'name')


class ProjectTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTag
        fields = ("pk", "name", "color")

    def create(self, data):
        data['user'] = self.context['request'].user
        return super().create(data)


class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    slug = serializers.ReadOnlyField()
    documents_count = serializers.ReadOnlyField()
    shared_with_users = UserSerializer(many=True, read_only=True)
    shared_with_groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'

    def create(self, data):
        data['owner'] = self.context["view"].request.user
        obj = super().create(data)
        return obj

    def to_representation(self, instance):
        # only use ProjectTagSerializer on GET; otherwise, use pks
        repr = super().to_representation(instance)
        repr['tags'] = [ProjectTagSerializer(tag).data for tag in instance.tags.all()]
        return repr


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


class PartBulkMoveSerializer(serializers.ModelSerializer):
    index = serializers.IntegerField()

    class Meta:
        model = DocumentPart
        fields = ('index',)

    def __init__(self, *args, parts=None, **kwargs):
        self.parts = parts
        super().__init__(*args, **kwargs)

    def bulk_move(self):
        oq = self.parts.first().get_ordering_queryset()
        # construct full parts list without the selected parts, but maintain indices
        reordered = [None if part in self.parts else part for part in oq]
        idx = self.validated_data['index']
        if idx == -1:
            # index of -1 means move to the end
            idx = oq.count()
        # insert correctly-ordered selected parts at the new index
        reordered[idx:idx] = list(self.parts)
        # filter all the Nones out
        reordered = list(filter(lambda item: item is not None, reordered))
        # store the new orders
        for (idx, p) in enumerate(reordered):
            p.order = idx
        DocumentPart.objects.bulk_update(reordered, ["order"])


class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = ('pk', 'name', 'archived', 'avg_confidence', 'created_at', 'comments')

    def create(self, data):
        document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        data['document'] = document
        try:
            return super().create(data)
        except IntegrityError:
            return Transcription.objects.get(name=data['name'])


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


class DocumentTagSerializer(serializers.ModelSerializer):
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
    parts_count = serializers.ReadOnlyField()
    project = serializers.SlugRelatedField(slug_field='slug',
                                           queryset=Project.objects.all())
    project_name = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ('pk', 'name', 'project', 'transcriptions',
                  'main_script', 'read_direction', 'line_offset', 'show_confidence_viz',
                  'valid_block_types', 'valid_line_types', 'valid_part_types',
                  'parts_count', 'tags', 'created_at', 'updated_at', 'project_name', 'project_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.for_user_write(self.context['user'])

    def validate_main_script(self, value):
        try:
            return Script.objects.get(name=value)
        except Script.DoesNotExist:
            raise serializers.ValidationError('This script does not exists in the database.')

    def get_project_name(self, document):
        return document.project.name

    def get_project_id(self, document):
        return document.project.id

    def to_representation(self, instance):
        # only use DocumentTagSerializer on GET; otherwise, use pks
        repr = super().to_representation(instance)
        repr['tags'] = [DocumentTagSerializer(tag).data for tag in instance.tags.all()]
        return repr


class ImportSerializer(serializers.Serializer):
    MODE_CHOICES = (
        ('pdf', 'Import a pdf file.'),
        ('iiif', 'Import from a iiif manifest.'),
        ('mets', 'Import a mets file.'),
        ('xml', 'Import from a xml file.')
    )
    mode = serializers.ChoiceField(choices=MODE_CHOICES)

    transcription = serializers.PrimaryKeyRelatedField(
        queryset=Transcription.objects.all(),
        required=False)
    name = serializers.CharField(required=False)
    override = serializers.BooleanField(required=False)
    upload_file = serializers.FileField(required=False)

    iiif_uri = serializers.URLField(required=False)

    METS_TYPE_CHOICES = (
        ('local', _('Upload local file')),
        ('url', _('download file from url')),
    )
    mets_type = serializers.ChoiceField(choices=METS_TYPE_CHOICES, required=False)
    mets_uri = serializers.URLField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = self.context["view"].request.user
        self.document = Document.objects.get(pk=self.context["view"].kwargs["document_pk"])
        self.mets_base_uri = None
        self.fields['transcription'].queryset = Transcription.objects.filter(document=self.document)

    def validate_iiif_uri(self, uri):
        try:
            content, total = clean_import_uri(uri, self.document, 'tmp.json')
            self.file = ContentFile(content, name='iiif_manifest.json')
            self.total = total
        except FileImportError as e:
            raise serializers.ValidationError(repr(e))

    def validate_mets_uri(self, uri):
        try:
            self.mets_base_uri = os.path.dirname(uri)
            content, total = clean_import_uri(uri, self.document, 'tmp.xml',
                                              is_mets=True, mets_base_uri=self.mets_base_uri)
            self.file = ContentFile(content, name='mets.xml')
            self.total = total
        except FileImportError as e:
            raise serializers.ValidationError(repr(e))

    def validate_upload_file(self, upload_file):
        try:
            parser = clean_upload_file(upload_file, self.document, self.user)
            self.file = parser.file
            self.total = parser.total
        except FileImportError as e:
            raise serializers.ValidationError(repr(e))

    def validate(self, data):
        data = super().validate(data)

        # validate different modes
        mode = data.get('mode')
        if mode == 'iiif':
            if 'iiif_uri' not in data:
                raise serializers.ValidationError("'iiif_uri' is mandatory with mode 'iiif'.")

        elif mode == 'mets':
            if 'mets_type' not in data:
                raise serializers.ValidationError("'mets_type' is mandatory with mode 'mets'.")
            else:
                if data.get('mets_type') == 'url':
                    if 'mets_uri' not in data:
                        raise serializers.ValidationError("'mets_uri' is mandatory with mode 'mets'. and type 'url'")
                elif 'upload_file' not in data:
                    raise serializers.ValidationError("'upload_file' is mandatory with mode 'mets'. and type 'local'")

        elif mode == 'pdf':
            if 'upload_file' not in data:
                raise serializers.ValidationError("'upload_file' is mandatory with mode 'pdf'.")

        elif mode == 'xml':
            if 'upload_file' not in data:
                raise serializers.ValidationError("'upload_file' is mandatory with mode 'xml'.")

        if not settings.DISABLE_QUOTAS:
            if not self.user.has_free_cpu_minutes():
                raise serializers.ValidationError(_("You don't have any CPU minutes left."))

        return data

    def create(self, validated_data):
        if 'name' in validated_data:
            name = validated_data.get("name")
        elif 'transcription' in validated_data:
            name = validated_data.get('transcription').name
        else:
            name = ''
        imp = DocumentImport(
            document=self.document,
            name=name,
            override=validated_data.get('override') or False,
            import_file=self.file,
            total=self.total,
            started_by=self.user,
            with_mets=validated_data.get('mode') == 'mets',
            mets_base_uri=self.mets_base_uri
        )
        imp.save()

        document_import.delay(
            import_pk=imp.pk,
            user_pk=self.user.pk,
            report_label=_('Import in %(document_name)s') % {'document_name': self.document.name}
        )

        return imp


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


class TaskReportSerializer(serializers.ModelSerializer):
    document_part = serializers.SerializerMethodField()

    class Meta:
        model = TaskReport
        fields = ('pk', 'document', 'document_part', 'workflow_state', 'label', 'messages',
                  'queued_at', 'started_at', 'done_at', 'method', 'user')

    def get_document_part(self, task_report):
        return str(task_report.document_part) if task_report.document_part else None


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

    def update(self, instance, validated_data):
        instance.value = validated_data.get('value', instance.value)
        instance.save()

        if "key" in validated_data:
            new_key = validated_data.get('key')
            nested_serializer = self.fields['key']
            nested_instance = instance.key
            nested_serializer.update(nested_instance, new_key)

        return instance


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
            'original_filename',
            'bw_image',
            'workflow',
            'order',
            'recoverable',
            'transcription_progress',
            'source',
            'max_avg_confidence',
            'comments',
            'updated_at',
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

        try:
            # check if the image already exists
            part = DocumentPart.objects.filter(document=document,
                                               original_filename=data['image'].name)[0]
            data['id'] = part.id
            part = super().update(part, data)
        except IndexError:
            # it's new
            # Can't use DoesNotExist because of legacy documents with duplicate image names
            part = super().create(data)

        # generate card thumbnail right away since we need it
        get_thumbnailer(part.image).get_thumbnail(settings.THUMBNAIL_ALIASES['']['card'],
                                                  generate=True)

        send_event("document", part.document.pk, "part:new", {"id": part.pk})
        part.task(
            "convert",
            user_pk=part.document.owner and part.document.owner.pk or None)

        return part


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
        lines.sort(key=lambda line: line[1]['order'])
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
    rights = serializers.SerializerMethodField(source='get_rights')
    script = serializers.ReadOnlyField(source='script.name')
    parent = serializers.ReadOnlyField(source='parent.name')
    can_share = serializers.SerializerMethodField(source='get_can_share')

    class Meta:
        model = OcrModel
        fields = ('pk', 'name', 'file', 'file_size', 'job',
                  'owner', 'training', 'versions', 'documents',
                  'accuracy_percent', 'rights', 'script', 'parent', 'can_share')

    def create(self, data):
        # If quotas are enforced, assert that the user still has free disk storage
        if not settings.DISABLE_QUOTAS and not self.context['request'].user.has_free_disk_storage():
            raise serializers.ValidationError(_("You don't have any disk storage left."))

        data['owner'] = self.context["view"].request.user
        data['file_size'] = data['file'].size
        obj = super().create(data)
        return obj

    def get_rights(self, instance):
        # get the requesting user's permissions for the model
        user = self.context["view"].request.user
        if instance.owner == user:
            return "owner"
        elif instance.public:
            return "public"
        else:
            return "user"

    def get_can_share(self, instance):
        user = self.context["view"].request.user
        return instance.owner == user and not instance.public


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
                                               queryset=DocumentPart.objects.all(),
                                               required=False)
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
        parts = self.validated_data.get('parts') or self.document.parts.all()

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
            # Note: Only an owner should be able to train on top of an existing model
            # if the model is public, the user can only clone it (override=False)
            Q(public=True)
            | Q(owner=self.user)
            | Q(ocr_model_rights__user=self.user)
            | Q(ocr_model_rights__group__user=self.user)
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
            model = model.clone_for_training(self.user, name=None)

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'trained_on': timezone.now()}
        )
        if not created:
            ocr_model_document.trained_on = timezone.now()
            ocr_model_document.save()

        segtrain.delay(model_pk=model.pk if model else None,
                       part_pks=[part.pk for part in self.validated_data.get('parts')],
                       document_pk=self.document.pk,
                       user_pk=self.user.pk)


class TextualWitnessSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = TextualWitness
        fields = ('name', 'pk', 'file', 'owner')


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
            # Note: Only an owner should be able to train on top of an existing model
            # if the model is public, the user can only clone it (override=False)
            Q(public=True)
            | Q(owner=self.user)
            | Q(ocr_model_rights__user=self.user)
            | Q(ocr_model_rights__group__user=self.user)
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
            model = model.clone_for_training(self.user, name=None)

        ocr_model_document, created = OcrModelDocument.objects.get_or_create(
            document=self.document,
            ocr_model=model,
            defaults={'trained_on': timezone.now()}
        )
        if not created:
            ocr_model_document.trained_on = timezone.now()
            ocr_model_document.save()

        train.delay(transcription_pk=self.validated_data['transcription'].pk,
                    model_pk=model.pk if model else None,
                    part_pks=[part.pk for part in self.validated_data.get('parts')],
                    user_pk=self.user.pk)


class TranscribeSerializer(ProcessSerializerMixin, serializers.Serializer):
    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all(),
                                               required=False)
    model = serializers.PrimaryKeyRelatedField(
        queryset=OcrModel.objects.all())
    transcription = serializers.PrimaryKeyRelatedField(
        queryset=Transcription.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = Transcription.objects.filter(
            document=self.document)
        self.fields['model'].queryset = OcrModel.objects.filter(
            job=OcrModel.MODEL_JOB_RECOGNIZE)
        self.fields['parts'].queryset = DocumentPart.objects.filter(
            document=self.document)

    def process(self):
        model = self.validated_data.get('model')
        transcription = self.validated_data.get('transcription')
        parts = self.validated_data.get('parts') or self.document.parts.all()

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
                transcribe.si(
                    transcription_pk=transcription.pk,
                    instance_pk=part.pk,
                    model_pk=model.pk,
                    user_pk=self.user.pk)
            )


class EditableMultipleChoiceField(serializers.MultipleChoiceField):
    """Make choices a property, so it can be modified reliably.
    Adapted from https://github.com/encode/django-rest-framework/issues/3383"""
    _choices = dict()

    def _set_choices(self, choices):
        self.grouped_choices = fields.to_choices_dict(self._choices)
        self._choices = fields.flatten_choices_dict(choices)
        self.choice_strings_to_values = {
            str(key): key for key in self._choices.keys()
        }

    def _get_choices(self):
        return self._choices

    choices = property(_get_choices, _set_choices)


class AlignSerializer(ProcessSerializerMixin, serializers.Serializer):
    parts = serializers.PrimaryKeyRelatedField(many=True,
                                               queryset=DocumentPart.objects.all(),
                                               required=False)

    transcription = serializers.PrimaryKeyRelatedField(
        queryset=Transcription.objects.filter(archived=False),
        required=True,
        help_text=_("The transcription on which to perform alignment."),
    )
    witness_file = serializers.FileField(
        # validators=[FileExtensionValidator(allowed_extensions=["txt"])],
        required=False,
        help_text=_("The reference text for alignment; must be a .txt file."),
    )
    existing_witness = serializers.PrimaryKeyRelatedField(
        queryset=TextualWitness.objects.all(),
        required=False,
        help_text=_("Reuse a previously-uploaded reference text."),
    )
    n_gram = serializers.IntegerField(
        label=_("N-gram"),
        required=True,
        min_value=2,
        max_value=25,
        initial=25,
        help_text=_("Length (2–25) of token sequences to compare; 25 should work well for at least moderately clean OCR. For very poor OCR, lower to 3 or 4."),
    )
    max_offset = serializers.IntegerField(
        label=_("Max offset"),
        help_text=_("Enables max-offset and disables beam search. Maximum number of characters (20–80) difference between the aligned witness text and the original transcription."),
        required=False,
        min_value=0,
        max_value=80,
    )
    beam_size = serializers.IntegerField(
        label=_("Beam size"),
        help_text=_("Enables beam search; if this and max offset are left unset, beam search will be on and beam size set to 20. Higher beam size (1-100) will result in slower computation but more accurate results."),
        required=False,
        min_value=0,
        max_value=100,
    )
    gap = serializers.IntegerField(
        label=_("Gap"),
        required=True,
        min_value=1,
        max_value=1000000,
        initial=600,
        help_text=_("The distance between matching unique n-grams; 600 should work well for clean OCR or texts where passages align to different portions of the witness text. To force end-to-end alignment of two documents, increase to 1,000,000.")
    )
    merge = serializers.BooleanField(
        label=_("Merge aligned text with existing transcription"),
        required=False,
        initial=False,
        help_text=_("If checked, the aligner will reuse the text of the original transcription when alignment could not be performed; if unchecked, those lines will be blank."),
    )
    full_doc = serializers.BooleanField(
        label=_("Use full transcribed document"),
        required=False,
        initial=True,
        help_text=_("If checked, the aligner will use all transcribed pages of the document to find matches. If unchecked, it will compare each page to the text separately."),
    )
    threshold = serializers.FloatField(
        label=_("Line length match threshold"),
        help_text=_("Minimum proportion (0.0–1.0) of aligned line length to original transcription, below which matches are ignored. At 0.0, all matches are accepted."),
        required=True,
        initial=0.8,
        min_value=0.0,
        max_value=1.0,
    )
    region_types = EditableMultipleChoiceField(
        required=True,
        choices={'Undefined': '(Undefined region type)', 'Orphan': '(Orphan lines)'},
        help_text=_("Region types to include in the alignment."),
    )
    layer_name = serializers.CharField(
        required=True,
        label=_("Layer name"),
        help_text=_("Name for the new transcription layer produced by this alignment. If you reuse an existing layer name, the layer will be overwritten; use caution."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['transcription'].queryset = self.document.transcriptions.filter(archived=False)
        self.fields['existing_witness'].queryset = TextualWitness.objects.filter(owner=self.user)
        self.fields['region_types'].choices = {
            **self.fields['region_types'].choices,
            **{
                str(rt.id): rt.name
                for rt in self.document.valid_block_types.all()
            },
        }
        self.fields['parts'].queryset = DocumentPart.objects.filter(document=self.document)

    def validate(self, data):
        data = super().validate(data)

        if 'witness_file' not in data and 'existing_witness' not in data:
            raise serializers.ValidationError(
                _("You must supply a textual witness (reference text).")
            )
        elif 'witness_file' in data and 'existing_witness' in data:
            raise serializers.ValidationError(
                _("You may only supply one witness text (file upload or existing text).")
            )

        if data.get("layer_name") == data.get("transcription"):
            raise serializers.ValidationError(
                _("Alignment layer name cannot be the same as the transcription you are trying to align.")
            )

        # ensure max offset and beam size not both set
        max_offset = data.get("max_offset")
        beam_size = data.get("beam_size")
        if max_offset and int(max_offset) != 0 and beam_size and int(beam_size) != 0:
            raise serializers.ValidationError(_("Max offset and beam size cannot both be non-zero."))

        # If quotas are enforced, assert that the user still has free CPU minutes
        if not settings.DISABLE_QUOTAS and not self.user.has_free_cpu_minutes():
            raise serializers.ValidationError(_("You don't have any CPU minutes left."))

        return data

    def process(self):
        """Instantiate or set the witness to use, then enqueue the task(s)"""
        transcription = self.validated_data.get("transcription")
        witness_file = self.validated_data.get("witness_file")
        existing_witness = self.validated_data.get("existing_witness")
        max_offset = self.validated_data.get("max_offset", 0)
        beam_size = self.validated_data.get("beam_size", 20)
        n_gram = self.validated_data.get("n_gram", 25)
        gap = self.validated_data.get("gap", 600)
        merge = self.validated_data.get("merge")
        full_doc = self.validated_data.get("full_doc", True)
        threshold = self.validated_data.get("threshold", 0.8)
        region_types = self.validated_data.get("region_types", ["Orphan", "Undefined"])
        parts = self.validated_data.get("parts") or self.document.parts.all()
        layer_name = self.validated_data.get("layer_name")

        if existing_witness:
            witness = existing_witness
        else:
            witness = TextualWitness(
                file=witness_file,
                name=os.path.splitext(witness_file.name)[0],
                owner=self.user,
            )
            witness.save()

        self.document.queue_alignment(
            parts=parts,
            user_pk=self.user.pk,
            transcription_pk=transcription.pk,
            witness_pk=witness.pk,
            # handle empty strings, NoneType; allow some values that could be false
            n_gram=int(n_gram if n_gram else 25),
            max_offset=int(max_offset if (max_offset is not None and max_offset != '') else 0),
            merge=bool(merge),
            full_doc=bool(full_doc if (full_doc is not None and full_doc != '') else True),
            threshold=float(threshold if (threshold is not None and threshold != '') else 0.8),
            region_types=list(region_types),
            layer_name=layer_name,
            beam_size=int(beam_size if (beam_size is not None and beam_size != '') else 20),
            gap=int(gap if gap else 600),
        )
