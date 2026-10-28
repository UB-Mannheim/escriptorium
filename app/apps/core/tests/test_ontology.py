from unittest.mock import patch

from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import serializers

from core.models import BlockType, get_or_create_doc_type
from core.ontology import (
    SUPPORTED_VERSIONS,
    OntologyConfigSerializer,
    apply_ontology_config,
    normalize,
    parse_ontology_file,
)
from core.tests.factory import CoreFactory


class GetOrCreateDocTypeTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.document = factory.make_document()

    def test_returns_existing_row_when_insert_loses_the_race(self):
        # Simulate another process having already inserted the row between
        # our SELECT and INSERT: get_or_create_doc_type must not raise, and
        # must return the row that's actually there.
        existing = BlockType.objects.create(name='MainZone', document=self.document)

        with patch('core.models.BlockType.objects.get_or_create', side_effect=IntegrityError):
            typo, created = get_or_create_doc_type(self.document, BlockType, 'MainZone')

        self.assertEqual(typo.pk, existing.pk)
        self.assertFalse(created)

    def test_no_duplicate_on_repeated_calls(self):
        get_or_create_doc_type(self.document, BlockType, 'MainZone')
        get_or_create_doc_type(self.document, BlockType, 'MainZone')
        self.assertEqual(BlockType.objects.filter(document=self.document, name='MainZone').count(), 1)


class OntologyConfigParsingTestCase(TestCase):
    def test_v1_json_is_accepted_and_normalized(self):
        f = ContentFile(b'{"version": 1, "region_types": ["MainZone"], "line_types": ["DefaultLine"]}')
        config = parse_ontology_file(f)
        config = normalize(config)
        self.assertEqual(config['region_types'], [{'name': 'MainZone', 'color': None}])
        self.assertEqual(config['version'], 2)

    def test_v2_yaml_with_colors_round_trips_through_import_and_export(self):
        factory = CoreFactory()
        document = factory.make_document()

        yaml_bytes = (
            b'version: 2\n'
            b'region_types:\n'
            b'  - {name: MainZone, color: "#0000ff"}\n'
            b'line_types:\n'
            b'  - {name: DefaultLine, color: "#9a56ff"}\n'
        )
        config = parse_ontology_file(ContentFile(yaml_bytes))
        config = normalize(config)
        serializer = OntologyConfigSerializer(data=config)
        serializer.is_valid(raise_exception=True)
        apply_ontology_config(document, serializer.validated_data)

        block_type = document.block_types.get(name='MainZone')
        line_type = document.line_types.get(name='DefaultLine')
        self.assertEqual(block_type.color, '#0000ff')
        self.assertEqual(line_type.color, '#9a56ff')

    def test_bad_version_is_rejected(self):
        f = ContentFile(b'{"version": -1}')
        with self.assertRaises(serializers.ValidationError):
            parse_ontology_file(f)

    def test_supported_versions_includes_v1_and_v2(self):
        self.assertEqual(SUPPORTED_VERSIONS, (1, 2))

    def test_existing_taxonomy_name_produces_a_warning(self):
        factory = CoreFactory()
        document = factory.make_document()

        config = {
            'region_types': [], 'line_types': [], 'part_types': [],
            'annotation_components': [],
            'taxonomy': [{'name': 'Illumination', 'marker_type': 1, 'components': []}],
        }
        serializer = OntologyConfigSerializer(data=normalize(config))
        serializer.is_valid(raise_exception=True)

        warnings = apply_ontology_config(document, serializer.validated_data)
        self.assertEqual(warnings, [])

        warnings = apply_ontology_config(document, serializer.validated_data)
        self.assertEqual(len(warnings), 1)
        self.assertIn('Illumination', warnings[0])


class ProjectOntologyConfigSeedTestCase(TestCase):
    def test_new_document_uses_project_ontology_config_over_defaults(self):
        factory = CoreFactory()
        project = factory.make_project()
        project.ontology_config = normalize({
            'region_types': ['CustomRegion'],
            'line_types': [],
            'part_types': [],
            'annotation_components': [],
            'taxonomy': [],
        })
        project.save()

        document = factory.make_document(project=project)

        self.assertTrue(document.block_types.filter(name='CustomRegion').exists())
