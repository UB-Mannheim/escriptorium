from django.urls import reverse
from django.test import TestCase

from users.models import User, Group
from core.tests.factory import CoreFactory


class DocumentShareTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.owner = User.objects.create(username='owner', email='o@test.com', password='test')
        self.target_user = User.objects.create(username='t1', email='t1@test.com', password='test')
        self.group = Group.objects.create(name='test group')
        self.target_group = User.objects.create(username='t2', email='t2@test.com', password='test')
        self.target_group.groups.add(self.group)
        self.owner.groups.add(self.group)
        self.doc = factory.make_document(owner=self.owner)
        
    def test_share_with_group(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_group)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)
        
        self.client.force_login(self.owner)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'shared_with_groups': self.group.pk
        })
        self.assertEqual(resp.status_code, 302)
        
        self.client.force_login(self.target_group)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    def test_share_with_known_user(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

        self.target_user.groups.add(self.group)
        self.owner.groups.add(self.group)
        self.client.force_login(self.owner)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'shared_with_users': [self.target_user.pk,]
        })
        self.assertEqual(resp.status_code, 302)

        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        
    def test_share_with_unknown_user(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.owner)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'username': self.target_user.username
        })
        self.assertEqual(resp.status_code, 302)

        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    def test_only_owner_can_share(self):
        self.client.force_login(self.target_user)
        self.assertEqual(self.doc.shared_with_groups.count(), 0)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'share_with_groups': self.group
        })
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.doc.shared_with_groups.count(), 0)
