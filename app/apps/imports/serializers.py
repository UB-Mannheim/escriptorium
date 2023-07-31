from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    BlockType,
    Document,
    DocumentPartType,
    LineType,
)


class CreatableSlugRelatedField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        try:
            # Using get_or_create to create the related object if missing instead of raising
            object, _ = self.get_queryset().get_or_create(**{self.slug_field: data})
            return object
        except (TypeError, ValueError):
            self.fail('invalid')


class AnnotationComponentExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnotationComponent
        fields = ('name', 'allowed_values')


class AnnotationTaxonomyExportSerializer(serializers.ModelSerializer):
    typology = CreatableSlugRelatedField(queryset=AnnotationType.objects.all(), slug_field='name', allow_null=True)
    marker_color = serializers.CharField(source='marker_detail')
    components = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = AnnotationTaxonomy
        fields = ('name', 'typology', 'has_comments', 'abbreviation',
                  'marker_type', 'marker_color', 'components')


class TypologyCreatableSlugRelatedField(CreatableSlugRelatedField):
    def get_queryset(self):
        return super().get_queryset().filter(Q(public=True) | Q(valid_in=self.root.instance)).distinct()


class OntologyExportSerializer(serializers.ModelSerializer):
    VERSION = 1

    version = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    region_types = TypologyCreatableSlugRelatedField(
        source='valid_block_types',
        many=True,
        queryset=BlockType.objects.all(),
        slug_field='name'
    )
    line_types = TypologyCreatableSlugRelatedField(
        source='valid_line_types',
        many=True,
        queryset=LineType.objects.all(),
        slug_field='name'
    )
    part_types = TypologyCreatableSlugRelatedField(
        source='valid_part_types',
        many=True,
        queryset=DocumentPartType.objects.all(),
        slug_field='name'
    )
    annotation_components = AnnotationComponentExportSerializer(
        many=True,
        source='annotationcomponent_set')
    taxonomy = AnnotationTaxonomyExportSerializer(
        many=True,
        source='annotationtaxonomy_set')

    class Meta:
        model = Document
        fields = ('version', 'created', 'line_types', 'region_types', 'part_types', 'annotation_components', 'taxonomy')

    def get_version(self, obj):
        return self.VERSION

    def get_created(self, obj):
        return timezone.now().strftime('%Y-%m-%dT%H:%M:%S')


class OntologyImportSerializer(OntologyExportSerializer):
    def __init__(self, *args, **kwargs):
        self.updated_with_warnings = False
        self.raw_data = kwargs.get('data', {})
        self.report = kwargs.pop('report')
        super().__init__(*args, **kwargs)

    def update(self, instance, validated_data):
        # Save typologies
        region_types = validated_data.get('valid_block_types', [])
        if region_types:
            instance.valid_block_types.add(*region_types)
            names = ', '.join(type.name for type in region_types)
            self.report.append(f'[INFO] Created/activated {len(region_types)} region type(s) named "{names}" on the document')

        line_types = validated_data.get('valid_line_types', [])
        if line_types:
            instance.valid_line_types.add(*line_types)
            names = ', '.join(type.name for type in line_types)
            self.report.append(f'[INFO] Created/activated {len(line_types)} line type(s) named "{names}" on the document')

        part_types = validated_data.get('valid_part_types', [])
        if part_types:
            instance.valid_part_types.add(*part_types)
            names = ', '.join(type.name for type in part_types)
            self.report.append(f'[INFO] Created/activated {len(part_types)} part type(s) named "{names}" on the document')

        # Save annotation components
        existing_components = {
            component['name']: component['allowed_values']
            for component in instance.annotationcomponent_set.values('name', 'allowed_values')
        }
        annotation_components = validated_data.get('annotationcomponent_set', [])
        for component in annotation_components:
            name = component['name']
            if name not in existing_components:
                AnnotationComponent.objects.create(**component, document=instance)
                self.report.append(f'[INFO] Created a new component named "{name}" on the document')
                continue

            if component['allowed_values'] == existing_components[name]:
                self.report.append(f'[INFO] An identical annotation component named "{name}" already exists on the document')
                continue

            self.report.append(f'[WARNING] A differing annotation component named "{name}" already exists on the document, it does not have the same allowed values as the one to import, skipping its import')
            self.updated_with_warnings = True

        # Save taxonomies
        existing_taxonomies = instance.annotationtaxonomy_set.values_list('name', flat=True)
        taxonomies = validated_data.get('annotationtaxonomy_set', [])
        for taxonomy in taxonomies:
            name = taxonomy['name']
            if name not in existing_taxonomies:
                # Creating the taxonomy
                created_taxonomy = AnnotationTaxonomy.objects.create(**taxonomy, document=instance)

                # Linking the annotation components
                components = []
                for raw_taxonomy in self.raw_data.get('taxonomy', []):
                    if raw_taxonomy['name'] == name:
                        components = raw_taxonomy.get('components', [])
                created_taxonomy.components.set(instance.annotationcomponent_set.filter(name__in=components))

                self.report.append(f'[INFO] Created a new taxonomy named "{name}" on the document and linked it to {len(components)} existing annotation components')
                continue

            self.report.append(f'[WARNING] A taxonomy named "{name}" already exists on the document, skipping the one to import')
            self.updated_with_warnings = True

        instance.save()
        return instance
