from django.urls import reverse
from django.test import TestCase

from core.models import *
from users.models import User


class DocumentListTestCase(TestCase):
    def test_list(self):
        pass


class DocumentExportTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test', password='test')
        
        # TODO: factories
        self.doc = Document.objects.create(name='test doc', owner=self.user)
        self.trans = Transcription.objects.create(name='test trans', document=self.doc)
        for i in range(1, 3):
            part = DocumentPart.objects.create(name='part %d' % i, document=self.doc)
            for j in range(1, 4):
                l = Line.objects.create(document_part=part, box=(0,0,1,1))
                LineTranscription.objects.create(line=l, transcription=self.trans, content='line %d:%d' % (i,j))
    
    def test_simple(self):
        self.client.force_login(self.user)
        
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('document-export',
                                           kwargs={'pk': self.doc.pk,
                                                   'trans_pk': self.trans.pk}))
        self.assertEqual(resp.content.decode(), "\nline 1:1\nline 1:2\nline 1:3\n-\nline 2:1\nline 2:2\nline 2:3\n")


class DocumentShareTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create(username='owner', email='o@test.com', password='test')
        self.target_user = User.objects.create(username='t1', email='t1@test.com', password='test')
        self.group = Group.objects.create(name='test group')
        self.target_group = User.objects.create(username='t2', email='t2@test.com', password='test')
        self.target_group.groups.add(self.group)
        self.owner.groups.add(self.group)
        self.doc = Document.objects.create(name='test doc', owner=self.owner)
        
    def test_share_with_group(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_group)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 404)
        
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
        self.assertEqual(resp.status_code, 404)

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
        self.assertEqual(resp.status_code, 404)

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


class DocumentPartProcessTestCase(TestCase):
    pass

