import os.path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from imports.models import Import
from core.models import *
from core.tests.factory import CoreFactoryTestCase 
    

class XmlImportTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.document = self.factory.make_document()
        self.part1 = self.factory.make_part(name='part 1', document=self.document)
        self.part2 = self.factory.make_part(name='part 2', document=self.document)
        self.client.force_login(self.document.owner)
    
    def test_alto_single(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(36):
                response = self.client.post(uri, {
                    'parts': str([self.part1.pk]),
                    'xml_file': SimpleUploadedFile(filename, fh.read())
                })
                self.assertEqual(response.content, b'{"status":"ok"}')
                self.assertEqual(response.status_code, 200)
                
        self.assertEqual(Import.objects.count(), 1)
        imp = Import.objects.first()
        self.assertEqual(imp.error_message, None)
        self.assertEqual(imp.workflow_state, Import.WORKFLOW_STATE_DONE) 
        self.assertEqual(self.part1.blocks.count(), 1)
        self.assertEqual(self.part1.blocks.first().box, [0, 0, 850, 1083])
        self.assertEqual(self.part1.lines.count(), 3)
        self.assertEqual(self.part1.lines.first().box, [160, 771, 220, 799])
        self.assertEqual(self.part1.lines.first().transcriptions.first().content, 'This is a test')
        self.assertEqual(self.part2.blocks.count(), 0)
        self.assertEqual(self.part2.lines.count(), 0)
    
    def test_alto_multi(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_multi.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(46):
                response = self.client.post(uri, {
                    'parts': str([self.part1.pk, self.part2.pk]),
                    'xml_file': SimpleUploadedFile(filename, fh.read())
                })
                self.assertEqual(response.content, b'{"status":"ok"}')
                self.assertEqual(response.status_code, 200)

        self.assertEqual(Import.objects.count(), 1)
        self.assertEqual(Import.objects.first().workflow_state, Import.WORKFLOW_STATE_DONE)
        self.assertEqual(self.part1.blocks.count(), 1)
        self.assertEqual(self.part1.lines.count(), 1)
        self.assertEqual(self.part2.blocks.count(), 2)
        self.assertEqual(self.part2.lines.count(), 2)
    
    def test_invalid_count(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            response = self.client.post(uri, {
                # trying to import on 2 parts when there is only one page in the xml
                'parts': str([self.part1.pk, self.part2.pk]),
                'xml_file': SimpleUploadedFile(filename, fh.read())
            }, follow=True)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_abbyy(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test.abbyy'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            response = self.client.post(uri, {
                'parts': str([self.part1.pk]),
                'xml_file': SimpleUploadedFile(filename, fh.read())
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'{"status":"ok"}')
        self.assertEqual(Import.objects.count(), 1)
        imp = Import.objects.first()
        self.assertEqual(imp.error_message, None)
        self.assertEqual(imp.workflow_state, Import.WORKFLOW_STATE_DONE)
        self.assertEqual(self.part1.blocks.count(), 1)
        self.assertEqual(self.part1.lines.count(), 1)
        self.assertEqual(self.part2.blocks.count(), 0)
        self.assertEqual(self.part2.lines.count(), 0)

        # abbyy's blocks have to be calculated
        self.assertEqual(self.part1.blocks.all()[0].box, [150, 761, 170, 781])

    def test_resume(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_multi.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:

            imp = Import.objects.create(
                document=self.document,
                parts=[self.part1.pk, self.part2.pk],
                import_file=ContentFile(
                    fh.read(),
                    name=os.path.join(
                        settings.MEDIA_ROOT,
                        Import.import_file.field.upload_to +
                        os.path.basename(fh.name))),
                workflow_state=Import.WORKFLOW_STATE_ERROR,
                processed=0)
        response = self.client.post(uri, {
            'resume_import': True
        })
        self.assertEqual(response.status_code, 200)
        imp.refresh_from_db()
        self.assertEqual(imp.workflow_state, imp.WORKFLOW_STATE_DONE)

    def test_name(self):
        trans = Transcription.objects.create(name="test import", document=self.document)
        b = Block.objects.create(document_part=self.part1, external_id="textblock_0", box=[0, 0, 100, 100])
        l = Line.objects.create(document_part=self.part1, block=b, external_id="line_0", box=[10,10,50,20])
        lt = LineTranscription.objects.create(transcription=trans, line=l)

        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            response = self.client.post(uri, {
                'name': "test import",
                'parts': str([self.part1.pk]),
                'xml_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.document.transcriptions.count(), 2)  # manual and 'test import'
            self.assertEqual(self.part1.lines.count(), 3)

            fh.seek(0)
            response = self.client.post(uri, {
                'parts': str([self.part1.pk]),
                'xml_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            # we created a new transcription
            self.assertEqual(self.document.transcriptions.count(), 3)
            # still the same number of lines
            self.assertEqual(self.part1.lines.count(), 3)

    def test_override(self):
        trans = Transcription.objects.create(name="ALTO Import", document=self.document)
        b = Block.objects.create(document_part=self.part1, external_id="textblock_0", box=[0, 0, 100, 100])
        l = Line.objects.create(document_part=self.part1, block=b, external_id="line_0", box=[10,10,50,20])
        lt = LineTranscription.objects.create(transcription=trans, line=l, content="test history")

        # historic line without external_id
        b2 = Block.objects.create(document_part=self.part1, box=[0, 0, 100, 100])
        l2 = Line.objects.create(document_part=self.part1, block=b2, box=[10,10,50,20])
        lt2 = LineTranscription.objects.create(transcription=trans, line=l2, content="test dummy")

        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            response = self.client.post(uri, {
                'override': False,
                'parts': str([self.part1.pk]),
                'xml_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.part1.lines.count(), 4)  # 3 from import + 1 existing
            lt.refresh_from_db()
            self.assertEqual(lt.history[0].content, 'test history')
            
            fh.seek(0)
            response = self.client.post(uri, {
                'override': True,
                'parts': str([self.part1.pk]),
                'xml_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            # this time we erased the existing line
            self.assertEqual(self.part1.lines.count(), 3)

    def test_error(self):
        pass
