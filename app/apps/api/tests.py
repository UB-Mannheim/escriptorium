"""
The goal here is not to test drf internals 
but only our own layer on top of it.
So no need to test the content unless there is some magic in the serializer.
"""
import os.path
from io import BytesIO

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from core.models import *
from users.models import User

class DocumentViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test')
        self.doc = Document.objects.create(
            owner=self.user,
            name='test1')
        Document.objects.create(
            owner=self.user,
            name='test2')
        
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:document-list')
        with self.assertNumQueries(5):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:document-detail',
                      kwargs={'pk': self.doc.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    # not used
    #def test_update
    #def test_create


class PartViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test')
        self.doc = Document.objects.create(
            owner=self.user,
            name='testdoc')
        with open(os.path.join(settings.MEDIA_ROOT, 'test.png'), 'rb') as fh:
            for i in range(2):  # test queries number scaling
                p = DocumentPart.objects.create(
                    document=self.doc,
                    image=fh.name)
        self.part = p
    
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.doc.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(7):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.doc.pk})
        with self.assertNumQueries(19):
            # 1&2 session & user
            # 3 document
            # 4 ordering
            # 5 insert
            # 6-19 thumbnail stuff
            with open(os.path.join(settings.MEDIA_ROOT, 'test.png'), 'rb') as fh:
                resp = self.client.post(uri, {'image': fh})
        self.assertEqual(resp.status_code, 201)
    
    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(4):
            resp = self.client.patch(
                uri, {'transcription_progress': 50},
                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
    
    def test_move(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-move',
                      kwargs={'document_pk': self.doc.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(6):
            resp = self.client.post(uri, {'index': 0})
        self.assertEqual(resp.status_code, 200)
        # refresh
        part = DocumentPart.objects.get(pk=self.part.pk)
        self.assertEqual(part.order, 0)


class BlockViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test')
        self.doc = Document.objects.create(
            owner=self.user,
            name='testdoc')
        with open(os.path.join(settings.MEDIA_ROOT, 'test.png'), 'rb') as fh:
            self.part = DocumentPart.objects.create(
                document=self.doc,
                image=fh.name)
        for i in range(2):
            b = Block.objects.create(
                box=[10+50*i,10,50+50*i,50],
                document_part=self.part)
        self.block = b
    
    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(3):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'box': [10,10,50,50]
            })
        self.assertEqual(resp.status_code, 201)        

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(4):
            resp = self.client.patch(uri, {
                'box': [100,100,150,150]
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)


class LineViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test')
        self.doc = Document.objects.create(
            owner=self.user,
            name='testdoc')
        with open(os.path.join(settings.MEDIA_ROOT, 'test.png'), 'rb') as fh:
            self.part = DocumentPart.objects.create(
                document=self.doc,
                image=fh.name)
        self.block = Block.objects.create(
                box=[10,10,200, 200],
                document_part=self.part)
        for i in range(2):
            l = Line.objects.create(
                box=[10+50*i,10,50+50*i,50],
                document_part=self.part,
                block=self.block)
        self.line = l
        self.orphan = Line.objects.create(
            box=[0,0,10,10],
            document_part=self.part)

    # not used
    #def test_detail(self):
    #def test_list(self):
    
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-list',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(6):
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'box': [10,10,50,50]
            })
        self.assertEqual(resp.status_code, 201)        
        
    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(4):
            resp = self.client.patch(uri, {
                'box': [100,100,150,150]
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)


class LineTranscriptionViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test')
        self.doc = Document.objects.create(
            owner=self.user,
            name='testdoc')
        with open(os.path.join(settings.MEDIA_ROOT, 'test.png'), 'rb') as fh:
            self.part = DocumentPart.objects.create(
                document=self.doc,
                image=fh.name)
        self.block = Block.objects.create(
                box=[10,10,200, 200],
                document_part=self.part)
        self.line = Line.objects.create(
            box=[10,10,50,50],
            document_part=self.part,
            block=self.block)
        self.transcription = Transcription.objects.create(
            document=self.doc,
            name='test')
        self.lt = LineTranscription.objects.create(
            transcription=self.transcription,
            line=self.line,
            content='test')
        
    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:transcription-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(4):
            resp = self.client.patch(uri, {
                'content': 'testset'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
    
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:transcription-list',
                      kwargs={'document_pk': self.doc.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(4):
            resp = self.client.post(uri, {
                'line': self.line.pk,
                'transcription': self.transcription.pk
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
