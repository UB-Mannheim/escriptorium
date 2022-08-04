from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import Document
from core.tests.factory import CoreFactory


class DocumentTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.project = factory.make_project()
        doc = factory.make_document(project=self.project)
        factory.make_document(owner=self.project.owner, project=self.project)

        self.user = self.project.owner
        group = Group.objects.create(name='test group')
        self.user.groups.add(group)

        doc = factory.make_document(project=self.project)  # another owner
        doc.shared_with_users.add(doc.owner)

        doc = factory.make_document(project=self.project)
        doc.shared_with_groups.add(group)

    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('documents-list', kwargs={'slug': self.project.slug})
        with self.assertNumQueries(21):
            resp = self.client.get(uri)
            self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self.assertEqual(Document.objects.count(), 4)  # 4 created in setup
        self.client.force_login(self.user)
        uri = reverse('document-create', kwargs={'slug': self.project.slug})
        with self.assertNumQueries(24):
            resp = self.client.post(uri, {
                'project': str(self.project.id),
                'name': "Test+metadatas",
                'main_script': '',
                'read_direction': 'rtl',
                'line_offset': 0,
                # 'typology': '',
                'documentmetadata_set-TOTAL_FORMS': 3,
                'documentmetadata_set-INITIAL_FORMS': 0,
                'documentmetadata_set-MIN_NUM_FORMS': 0,
                'documentmetadata_set-MAX_NUM_FORMS': 1000,
                'documentmetadata_set-0-id': '',
                'documentmetadata_set-0-document': '',
                'documentmetadata_set-0-key': "Found+Place",
                'documentmetadata_set-0-value': "test",
                'documentmetadata_set-0-DELETE': '',
                'documentmetadata_set-1-id': '',
                'documentmetadata_set-1-document': '',
                'documentmetadata_set-1-key': "another+one",
                'documentmetadata_set-1-value': "test2",
                'documentmetadata_set-1-DELETE': '',
                'documentmetadata_set-2-id': '',
                'documentmetadata_set-2-document': '',
                'documentmetadata_set-2-key': '',
                'documentmetadata_set-2-value': '',
                'documentmetadata_set-2-DELETE': ''
            })
            self.assertEqual(resp.status_code, 302)
        self.assertEqual(Document.objects.count(), 5)
