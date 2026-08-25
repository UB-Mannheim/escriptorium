import yaml
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    BlockType,
    DocumentPartType,
    LineType,
    get_or_create_doc_type,
)

SUPPORTED_VERSIONS = (1, 2)
CURRENT_VERSION = 2

# (config key, target model) for the simple name/color type lists.
TYPE_KEYS = (
    ('region_types', BlockType),
    ('line_types', LineType),
    ('part_types', DocumentPartType),
)


def parse_ontology_file(django_file):
    """Parse an uploaded ontology file (v2 YAML, or legacy v1 JSON - YAML is
    a JSON superset so a single yaml.safe_load handles both) into a dict."""
    try:
        config = yaml.safe_load(django_file.read())
    except yaml.YAMLError as e:
        raise serializers.ValidationError(f'Could not parse ontology file: {e}')

    if not isinstance(config, dict):
        raise serializers.ValidationError('Ontology file must contain a mapping at the top level.')

    if config.get('version') not in SUPPORTED_VERSIONS:
        raise serializers.ValidationError(
            f'Unsupported ontology version {config.get("version")!r}, '
            f'supported versions are {SUPPORTED_VERSIONS}.'
        )

    return config


def normalize(config):
    """Turn a parsed config (v1 JSON, or v2 YAML with bare-string leniency)
    into the canonical v2 shape: type lists of {name, color} dicts."""
    config = dict(config)
    for key, _model in TYPE_KEYS:
        entries = config.get(key) or []
        config[key] = [
            {'name': entry.get('name'), 'color': entry.get('color')}
            if isinstance(entry, dict)
            else {'name': entry, 'color': None}
            for entry in entries
        ]
    config['annotation_components'] = config.get('annotation_components') or []
    config['taxonomy'] = config.get('taxonomy') or []
    config['version'] = CURRENT_VERSION
    return config


class TypeEntrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    color = serializers.RegexField(r'^#[0-9a-fA-F]{6}$', required=False, allow_null=True)


class AnnotationComponentEntrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    allowed_values = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )


class TaxonomyEntrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64)
    typology = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    has_comments = serializers.BooleanField(required=False, default=False)
    abbreviation = serializers.CharField(max_length=3, required=False, allow_null=True, allow_blank=True)
    marker_type = serializers.ChoiceField(
        choices=[c[0] for c in AnnotationTaxonomy.MARKER_TYPE_CHOICES]
    )
    marker_color = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    components = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class OntologyConfigSerializer(serializers.Serializer):
    version = serializers.IntegerField()
    created = serializers.CharField(required=False, allow_null=True)
    region_types = TypeEntrySerializer(many=True, required=False, default=list)
    line_types = TypeEntrySerializer(many=True, required=False, default=list)
    part_types = TypeEntrySerializer(many=True, required=False, default=list)
    annotation_components = AnnotationComponentEntrySerializer(many=True, required=False, default=list)
    taxonomy = TaxonomyEntrySerializer(many=True, required=False, default=list)


def _get_or_create_annotation_type(name):
    try:
        with transaction.atomic():
            typology, _created = AnnotationType.objects.get_or_create(name=name)
    except IntegrityError:
        typology = AnnotationType.objects.get(name=name)
    return typology


def apply_ontology_config(document, config):
    """Apply a validated, normalized (v2) config to a document. Returns a
    list of warnings for entries that could not be applied as-is."""
    warnings = []

    for key, model in TYPE_KEYS:
        has_color = hasattr(model, 'color')
        for entry in config.get(key) or []:
            color = entry.get('color') if has_color else None
            typo, created = get_or_create_doc_type(document, model, entry['name'], color=color)
            if not created and color and not typo.color:
                typo.color = color
                typo.save(update_fields=['color'])

    existing_components = {
        c.name: c.allowed_values for c in document.annotationcomponent_set.all()
    }
    for entry in config.get('annotation_components') or []:
        name = entry['name']
        allowed_values = entry.get('allowed_values')
        if name not in existing_components:
            AnnotationComponent.objects.create(name=name, allowed_values=allowed_values, document=document)
            existing_components[name] = allowed_values
        elif existing_components[name] != allowed_values:
            warnings.append(
                f'A differing annotation component named "{name}" already exists on the '
                f'document, it does not have the same allowed values as the one to import, '
                f'skipping its import.'
            )

    existing_taxonomy_names = set(document.annotationtaxonomy_set.values_list('name', flat=True))
    for entry in config.get('taxonomy') or []:
        name = entry['name']
        if name in existing_taxonomy_names:
            warnings.append(f'A taxonomy named "{name}" already exists on the document, skipping the one to import.')
            continue

        typology = _get_or_create_annotation_type(entry['typology']) if entry.get('typology') else None
        taxonomy = AnnotationTaxonomy.objects.create(
            document=document,
            name=name,
            typology=typology,
            has_comments=entry.get('has_comments', False),
            abbreviation=entry.get('abbreviation'),
            marker_type=entry['marker_type'],
            marker_detail=entry.get('marker_color'),
        )
        component_names = entry.get('components') or []
        taxonomy.components.set(
            AnnotationComponent.objects.filter(document=document, name__in=component_names)
        )
        existing_taxonomy_names.add(name)

    return warnings


def export_ontology_config(document):
    return {
        'version': CURRENT_VERSION,
        'created': timezone.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'region_types': [{'name': t.name, 'color': t.color} for t in document.block_types.all()],
        'line_types': [{'name': t.name, 'color': t.color} for t in document.line_types.all()],
        'part_types': [{'name': t.name} for t in document.part_types.all()],
        'annotation_components': [
            {'name': c.name, 'allowed_values': c.allowed_values}
            for c in document.annotationcomponent_set.all()
        ],
        'taxonomy': [
            {
                'name': t.name,
                'typology': t.typology.name if t.typology else None,
                'has_comments': t.has_comments,
                'abbreviation': t.abbreviation,
                'marker_type': t.marker_type,
                'marker_color': t.marker_detail,
                'components': list(t.components.values_list('name', flat=True)),
            }
            for t in document.annotationtaxonomy_set.all()
        ],
    }


def dump_yaml(config):
    return yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
