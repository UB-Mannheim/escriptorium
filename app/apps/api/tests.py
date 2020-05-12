"""
The goal here is not to test drf internals 
but only our own layer on top of it.
So no need to test the content unless there is some magic in the serializer.
"""
import os.path
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import *
from core.tests.factory import CoreFactoryTestCase
from users.models import User


class DocumentViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.doc = self.factory.make_document()
        self.doc2 = self.factory.make_document(owner=self.doc.owner)
    
    def test_list(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        with self.assertNumQueries(5):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    def test_detail(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-detail',
                      kwargs={'pk': self.doc.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    # not used
    #def test_update
    #def test_create


class PartViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.part2 = self.factory.make_part(document=self.part.document)  # scaling test
        self.user = self.part.document.owner  # shortcut
    
    @override_settings(THUMBNAIL_ENABLE=False)
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    @override_settings(THUMBNAIL_ENABLE=False)
    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(7):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
    
    @override_settings(THUMBNAIL_ENABLE=False)
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        with self.assertNumQueries(27):
            img = self.factory.make_image_file()
            resp = self.client.post(uri, {
                'image': SimpleUploadedFile(
                    'test.png', img.read())})
            self.assertEqual(resp.status_code, 201)
    
    @override_settings(THUMBNAIL_ENABLE=False)
    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.patch(
                uri, {'transcription_progress': 50},
                content_type='application/json')
            self.assertEqual(resp.status_code, 200)
    
    def test_move(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-move',
                      kwargs={'document_pk': self.part2.document.pk,
                              'pk': self.part2.pk})
        with self.assertNumQueries(7):
            resp = self.client.post(uri, {'index': 0})
            self.assertEqual(resp.status_code, 200)

        self.part2.refresh_from_db()
        self.assertEqual(self.part2.order, 0)


class BlockViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        for i in range(2):
            b = Block.objects.create(
                box=[10+50*i,10,50+50*i,50],
                document_part=self.part)
        self.block = b
    
    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(3):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        
    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            # 1-2: auth
            # 3 select document_part
            # 4 select max block order
            # 5 insert
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'box': '[[10,10], [50,50]]'
            })
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(4):
            resp = self.client.patch(uri, {
                'box': '[[100,100], [150,150]]'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)


class LineViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.block = Block.objects.create(
                box=[10,10,200, 200],
                document_part=self.part)
        for i in range(2):
            l = Line.objects.create(
                box=[10+50*i, 10, 50+50*i, 50],
                document_part=self.part,
                block=self.block)
        self.line = l
        self.line2 = Line.objects.create(
                box=[90, 10, 70, 50],
                document_part=self.part,
                script= "script",
                block=self.block)
        self.orphan = Line.objects.create(
            box=[0, 0, 10, 10],
            document_part=self.part,
            block=None)
    
    # not used
    #def test_detail(self):
    #def test_list(self):
    
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(7):
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'baseline': '[[10, 10], [50, 50]]'
            })
            self.assertEqual(resp.status_code, 201)
        self.assertEqual(self.part.lines.count(), 4)  # 3 + 1 new
        
    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.line.pk})
        with self.assertNumQueries(5):
            resp = self.client.patch(uri, {
                'baseline': '[[100,100], [150,150]]'
            }, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
        self.line.refresh_from_db()
        self.assertEqual(self.line.baseline, '[[100,100], [150,150]]')

    def test_bulk_delete(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-bulk-delete',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(6):
            resp = self.client.post(uri, {'lines': [self.line.pk,]},
                                    content_type='application/json')
            self.assertEqual(Line.objects.count(), 2)
            self.assertEqual(resp.status_code, 204)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(8):
            resp = self.client.post(uri, {'lines': [
                {'pk':self.line.pk,'mask':'[[60, 40], [60, 50], [90, 50], [90, 40]]'},
                {'pk':self.line2.pk,'mask':'[[50, 40], [50, 30], [70, 30], [70, 40]]'},
            ]},content_type='application/json')
            self.line.refresh_from_db()
            self.line2.refresh_from_db()
            self.assertEqual(self.line.mask,'[[60, 40], [60, 50], [90, 50], [90, 40]]')
            self.assertEqual(self.line2.mask,'[[50, 40], [50, 30], [70, 30], [70, 40]]')
            self.assertEqual(resp.status_code, 200)


class LineTranscriptionViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.line = Line.objects.create(
            box=[10,10,50,50],
            document_part=self.part)
        self.line2 = Line.objects.create(
            box=[10,60,50,100],
            document_part=self.part)
        self.transcription = Transcription.objects.create(
            document=self.part.document,
            name='test')
        self.transcription2 = Transcription.objects.create(
            document=self.part.document,
            name='tr2')
        self.lt = LineTranscription.objects.create(
            transcription=self.transcription,
            line=self.line,
            content='test')
        self.lt2 = LineTranscription.objects.create(
            transcription=self.transcription2,
            line=self.line2,
            content='test2')

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.lt.pk})
        with self.assertNumQueries(5):
            resp = self.client.patch(uri, {
                'content': 'update'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
    
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        
        with self.assertNumQueries(12):
            resp = self.client.post(uri, {
                'line': self.line2.pk,
                'transcription': self.transcription.pk,
                'content': 'new'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    def test_new_version(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-new-version',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.lt.pk})
        
        with self.assertNumQueries(4):
            resp = self.client.post(uri, {}, content_type='application/json')
            self.assertEqual(resp.status_code, 201)

    def test_bulk_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-create',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        ll = Line.objects.create(
            box=[10, 10, 50, 50],
            document_part=self.part)
        with self.assertNumQueries(10):
            resp = self.client.post(uri,
                                    {'lines':[
                                        {'line':ll.pk,'transcription': self.transcription.pk, 'content':'new transcription'},
                                        {'line':ll.pk,'transcription': self.transcription2.pk, 'content':'new transcription 2'},
                                    ]}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})

        with self.assertNumQueries(15):
            resp = self.client.put(uri, {'lines': [
                {'pk': self.lt.pk, 'content': 'test1 new','transcription' :self.transcription.pk,'line':self.line.pk},
                {'pk': self.lt2.pk,'content':'test2 new','transcription' :self.transcription.pk,'line':self.line2.pk},
            ]}, content_type='application/json')
            self.lt.refresh_from_db()
            self.lt2.refresh_from_db()
            self.assertEqual(self.lt.content, "test1 new")
            self.assertEqual(self.lt2.content, "test2 new")
            self.assertEqual(self.lt2.transcription, self.transcription)
            self.assertEqual(resp.status_code, 200)

    def test_bulk_delete(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-delete',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {'lines': [ self.lt.pk, self.lt2.pk,]}, content_type='application/json')
            lines = LineTranscription.objects.all()
            self.assertEqual(lines[0].content,"")
            self.assertEqual(lines[1].content,"")
            self.assertEqual(resp.status_code, 204)

