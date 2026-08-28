import yaml
from django.test import TestCase
from django.urls import reverse

from core.models import (
    AnnotationComponent,
    AnnotationTaxonomy,
    AnnotationType,
    BlockType,
    DocumentPartType,
    LineType,
)
from core.ontology import CURRENT_VERSION
from core.tests.factory import CoreFactory


class DocumentTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.project = factory.make_project()
        self.doc = factory.make_document(project=self.project)
        self.user = self.project.owner
        self.other_user = factory.make_user()

    def test_get_ontology_anonymous(self):
        uri = reverse('document-ontology-export', kwargs={'pk': self.doc.pk})
        resp = self.client.get(uri)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('login') + f'?next={uri}')

    def test_get_ontology_document_not_found(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('document-ontology-export', kwargs={'pk': 10000000000}))
        self.assertEqual(resp.status_code, 403)

    def test_get_ontology_unauthorized(self):
        self.client.force_login(self.other_user)
        resp = self.client.get(reverse('document-ontology-export', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_get_ontology(self):
        # Add some data to export, owned by the document
        LineType.objects.create(name='Line', document=self.doc, color='#111111')
        BlockType.objects.create(name='Block', document=self.doc, color='#222222')
        DocumentPartType.objects.create(name='Part', document=self.doc)

        component_1 = AnnotationComponent.objects.create(document=self.doc, name='Component 1', allowed_values=['X', 'Y', 'Z'])
        component_2 = AnnotationComponent.objects.create(document=self.doc, name='Component 2', allowed_values=[])
        image_taxonomy = AnnotationTaxonomy.objects.create(
            document=self.doc,
            name='Image annotation',
            typology=AnnotationType.objects.create(name='legend'),
            has_comments=True,
            abbreviation='IA',
            marker_type=AnnotationTaxonomy.MARKER_TYPE_RECTANGLE,
            marker_detail='#FFFFFF',
        )
        image_taxonomy.components.set([component_1, component_2])
        AnnotationTaxonomy.objects.create(
            document=self.doc,
            name='Text annotation',
            typology=AnnotationType.objects.create(name='definition'),
            has_comments=False,
            abbreviation='TA',
            marker_type=AnnotationTaxonomy.MARKER_TYPE_BOLD,
            marker_detail='#BBBBBB',
        )

        # Export everything
        self.client.force_login(self.user)
        resp = self.client.get(reverse('document-ontology-export', kwargs={'pk': self.doc.pk}))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Disposition'], 'attachment; filename=ontology_export.yml')

        ontology_config = yaml.safe_load(resp.content)
        self.assertIsNotNone(ontology_config['created'])
        del ontology_config['created']

        self.assertEqual(ontology_config, {
            'version': CURRENT_VERSION,
            'line_types': [{'name': 'Line', 'color': '#111111'}],
            'region_types': [{'name': 'Block', 'color': '#222222'}],
            'part_types': [{'name': 'Part'}],
            'annotation_components': [
                {'name': 'Component 1', 'allowed_values': ['X', 'Y', 'Z']},
                {'name': 'Component 2', 'allowed_values': []}
            ],
            'taxonomy': [
                {
                    'name': 'Image annotation',
                    'typology': 'legend',
                    'has_comments': True,
                    'abbreviation': 'IA',
                    'marker_type': 1,
                    'marker_color': '#FFFFFF',
                    'components': [
                        'Component 1',
                        'Component 2'
                    ]
                },
                {
                    'name': 'Text annotation',
                    'typology': 'definition',
                    'has_comments': False,
                    'abbreviation': 'TA',
                    'marker_type': 5,
                    'marker_color': '#BBBBBB',
                    'components': []
                },
            ],
        })
