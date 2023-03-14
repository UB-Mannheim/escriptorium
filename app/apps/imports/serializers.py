from django.utils import timezone
from rest_framework import serializers

from core.models import AnnotationComponent, AnnotationTaxonomy, Document


class AnnotationComponentExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnotationComponent
        fields = ('name', 'allowed_values')


class AnnotationTaxonomyExportSerializer(serializers.ModelSerializer):
    typology = serializers.SlugRelatedField(read_only=True, slug_field='name')
    marker_color = serializers.CharField(source='marker_detail')
    components = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = AnnotationTaxonomy
        fields = ('name', 'typology', 'has_comments', 'abbreviation',
                  'marker_type', 'marker_color', 'components')


class OntologyExportSerializer(serializers.ModelSerializer):
    VERSION = 1

    version = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    region_types = serializers.SlugRelatedField(
        source='valid_block_types',
        many=True,
        read_only=True,
        slug_field='name'
    )
    line_types = serializers.SlugRelatedField(
        source='valid_line_types',
        many=True,
        read_only=True,
        slug_field='name'
    )
    part_types = serializers.SlugRelatedField(
        source='valid_part_types',
        many=True,
        read_only=True,
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
