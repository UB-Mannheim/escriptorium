from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.tests.factory import CoreFactory
from users.models import User


class DocumentListTestCase(TestCase):
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
        with self.assertNumQueries(7):
            # Note: 1 query / document to fetch the first picture
            # can be improved
            resp = self.client.get(uri)
            self.assertEqual(resp.status_code, 200)

