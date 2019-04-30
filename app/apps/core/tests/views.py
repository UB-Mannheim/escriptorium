from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import Document
from core.tests.factory import CoreFactory
from users.models import User


class DocumentTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        doc = factory.make_document()
        factory.make_document(owner=doc.owner)
        
        self.user = doc.owner
        group = Group.objects.create(name='test group')
        self.user.groups.add(group)
        
        doc = factory.make_document()  # another owner
        doc.shared_with_users.add(doc.owner)
        
        doc = factory.make_document()
        doc.shared_with_groups.add(group)
    
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('documents-list')
        with self.assertNumQueries(9):
            # Note: 1 query / document to fetch the first picture
            # can be improved
            resp = self.client.get(uri)
            self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('document-create')
        with self.assertNumQueries(19):
            resp = self.client.post(uri, {
                'name':"Test+metadatas",
                'typology': '',
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
        self.assertEqual(Document.objects.count(), 5)  # 4 created in setup
        
