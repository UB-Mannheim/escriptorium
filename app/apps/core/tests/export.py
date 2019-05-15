from django.urls import reverse
from django.test import TestCase

from core.models import Line, LineTranscription, Block
from core.tests.factory import CoreFactory


class DocumentExportTestCase(TestCase):
    def setUp(self):
        self.factory = CoreFactory()
        self.trans = self.factory.make_transcription()
        self.user = self.trans.document.owner  # shortcut
        for i in range(1, 3):
            part = self.factory.make_part(name='part %d' % i,
                                     document=self.trans.document)
            for j in range(1, 4):
                l = Line.objects.create(document_part=part,
                                        box=(0,0,1,1))
                LineTranscription.objects.create(
                    line=l,
                    transcription=self.trans,
                    content='line %d:%d' % (i,j))
    
    def test_simple(self):
        self.client.force_login(self.user)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-export',
                                           kwargs={'pk': self.trans.document.pk})
                                   + '?transcription=' + str(self.trans.pk))

        self.assertEqual(''.join([c.decode() for c in resp.streaming_content]),
                         "line 1:1\nline 1:2\nline 1:3\nline 2:1\nline 2:2\nline 2:3\n")
    
    def test_alto(self):
        self.client.force_login(self.user)
        with self.assertNumQueries(16):  # should be 8 + 4*part
            resp = self.client.get(reverse('api:document-export',
                                           kwargs={'pk': self.trans.document.pk,})
                                   + '?transcription=%d&as=alto' % self.trans.pk)
        content = list(resp.streaming_content)
        self.assertEqual(len(content), 4)  # start + 2 part + end
    
    def test_alto_qs_scaling(self):
        for i in range(4, 20):
            part = self.factory.make_part(name='part %d' % i,
                                          document=self.trans.document)
            block = Block.objects.create(document_part=part, box=(0,0,1,1))
            for j in range(1, 4):
                l = Line.objects.create(document_part=part,
                                        block=block,
                                        box=(0,0,1,1))
                LineTranscription.objects.create(
                    line=l,
                    transcription=self.trans,
                    content='line %d:%d' % (i,j))
        self.client.force_login(self.user)
        with self.assertNumQueries(80):
            resp = self.client.get(reverse('api:document-export',
                                           kwargs={'pk': self.trans.document.pk,})
                                   + '?transcription=%d&as=alto' % self.trans.pk)
            self.assertEqual(resp.status_code, 200)
        
    def test_invalid(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('api:document-export',
                                       kwargs={'pk': self.trans.document.pk}))
        self.assertEqual(resp.status_code, 400)
