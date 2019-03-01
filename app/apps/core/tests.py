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
