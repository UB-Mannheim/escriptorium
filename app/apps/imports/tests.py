import os.path
from unittest import mock

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from imports.models import DocumentImport
from imports.parsers import ParseError
from core.models import *
from core.tests.factory import CoreFactoryTestCase 
    

class XmlImportTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.document = self.factory.make_document()
        self.part1 = self.factory.make_part(name='part 1',
                                            document=self.document,
                                            original_filename='test1.png')
        self.part2 = self.factory.make_part(name='part 2',
                                            document=self.document,
                                            original_filename='test2.png')
        self.client.force_login(self.document.owner)

    def test_alto_single_no_match(self):
        self.part1.original_filename = 'temp'
        self.part1.save()

        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(12):
                #with self.assertRaises(ParseError):  # doesn't work?!
                response = self.client.post(uri, {
                    'upload_file': SimpleUploadedFile(filename, fh.read())
                })
                # Note: the ParseError is raised by the processing of the import, not the validation!
                # the error is sent via websocket so no need to catch it here
                self.assertEqual(response.status_code, 200)

        # failed, didn't create anythng
        self.assertEqual(self.part1.blocks.count(), 0)
        self.assertEqual(self.part1.lines.count(), 0)

        # import was created since the form validated
        imp = DocumentImport.objects.first()
        self.assertTrue(imp.error_message, 'No match found')
        
        self.part1.original_filename = 'test1.png'
        self.part1.save()
        
    def test_alto_invalid_xml(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_invalid_alto.xml'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(5):
                response = self.client.post(uri, {
                    'upload_file': SimpleUploadedFile(filename, fh.read())
                })
                self.assertEqual(response.status_code, 400)
    
    def test_alto_single_bbox(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(39):
                response = self.client.post(uri, {
                    'upload_file': SimpleUploadedFile(filename, fh.read())
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'{"status":"ok"}')
                
        self.assertEqual(DocumentImport.objects.count(), 1)
        imp = DocumentImport.objects.first()
        self.assertEqual(imp.error_message, None)
        self.assertEqual(imp.workflow_state, DocumentImport.WORKFLOW_STATE_DONE) 
        self.assertEqual(self.part1.blocks.count(), 1)
        self.assertEqual(self.part1.blocks.first().box, [0, 0, 850, 1083])
        self.assertEqual(self.part1.lines.count(), 3)
        self.assertEqual(self.part1.lines.first().box, [160, 771, 220, 799])
        self.assertEqual(self.part1.lines.first().transcriptions.first().content, 'This is a test')
        self.assertEqual(self.part2.blocks.count(), 0)
        self.assertEqual(self.part2.lines.count(), 0)

    def test_alto_single_baseline(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test_single_baselines.alto'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(29):
                response = self.client.post(uri, {
                    'upload_file': SimpleUploadedFile(filename, fh.read())
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'{"status":"ok"}')
                
        self.assertEqual(DocumentImport.objects.count(), 1)
        imp = DocumentImport.objects.first()
        self.assertEqual(imp.error_message, None)
        self.assertEqual(imp.workflow_state, DocumentImport.WORKFLOW_STATE_DONE) 
        self.assertEqual(self.part1.blocks.count(), 1)
        self.assertEqual(self.part1.blocks.first().box, [0, 0, 850, 1083])
        self.assertEqual(self.part1.lines.count(), 1)
        line = self.part1.lines.first()
        self.assertEqual(line.baseline, [[160,771], [170,772], [190,782], [220,772]])
        self.assertEqual(line.mask, [[158,770], [225,770], [225,750], [158,750]])
        self.assertEqual(line.transcriptions.first().content, 'This is a test')
    
    def test_alto_multi(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test.zip'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            with self.assertNumQueries(54):
                response = self.client.post(uri, {
                    'upload_file': SimpleUploadedFile(filename, fh.read())
                })
                self.assertEqual(response.content, b'{"status":"ok"}')
                self.assertEqual(response.status_code, 200)

        self.assertEqual(DocumentImport.objects.count(), 1)
        self.assertEqual(DocumentImport.objects.first().workflow_state, DocumentImport.WORKFLOW_STATE_DONE)
        self.assertEqual(self.part1.blocks.count(), 1)
        self.assertEqual(self.part1.lines.count(), 3)
        self.assertEqual(self.part2.blocks.count(), 1)
        self.assertEqual(self.part2.lines.count(), 1)

    def test_resume(self):
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        filename = 'test.zip'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            imp = DocumentImport.objects.create(
                document=self.document,
                import_file=ContentFile(
                    fh.read(),
                    name=os.path.join(
                        settings.MEDIA_ROOT,
                        DocumentImport.import_file.field.upload_to +
                        os.path.basename(fh.name))),
                workflow_state=DocumentImport.WORKFLOW_STATE_ERROR,
                processed=0)

        response = self.client.post(uri, {'resume_import': True})
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
                'upload_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.document.transcriptions.count(), 2)  # manual and 'test import'
            self.assertEqual(self.part1.lines.count(), 3)

            fh.seek(0)
            response = self.client.post(uri, {
                'upload_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            # we created a new transcription
            self.assertEqual(self.document.transcriptions.count(), 3)
            # still the same number of lines
            self.assertEqual(self.part1.lines.count(), 3)

    def test_override(self):
        trans = Transcription.objects.create(name="Alto Import", document=self.document)
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
                'upload_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.part1.lines.count(), 4)  # 3 from import + 1 existing
            lt.refresh_from_db()
            
            self.assertEqual(len(lt.history), 1)
            self.assertEqual(lt.history[0].content, 'test history')
            
            fh.seek(0)
            response = self.client.post(uri, {
                'override': True,
                'upload_file': SimpleUploadedFile(filename, fh.read())
            })
            self.assertEqual(response.content, b'{"status":"ok"}')
            self.assertEqual(response.status_code, 200)
            # this time we erased the existing line
            self.assertEqual(self.part1.lines.count(), 3)
    
    def test_iiif(self):
        filename = 'iiif.json'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        uri = reverse('api:document-imports', kwargs={'pk': self.document.pk})
        with open(mock_path, 'rb') as fh:
            imp = DocumentImport(
                document=self.document,
                name='test',
                started_by = self.document.owner
            )
            imp.import_file.save(
                'iiif_manifest.json',
                ContentFile(fh.read()))

            # we don't go through the form but we want to test json validation
            imp.parser.validate()
            imp.save()
        
        # mock images grabbing
        filename = 'test.png'
        mock_path = os.path.join(os.path.dirname(__file__), 'mocks', filename)
        with open(mock_path, 'rb') as fh:
            # mock the image grabbing
            mock_resp = mock.Mock(content=fh.read(), status_code=200)
            with mock.patch('requests.get', return_value=mock_resp):
                for part in imp.process():  # exaust the generator
                    pass
        
        self.assertEqual(imp.workflow_state, imp.WORKFLOW_STATE_DONE)
        self.assertEqual(imp.processed, 5)
        self.assertEqual(self.document.parts.count(), 7)  # +2 from factory
    
    def test_cancel(self):
        # Note: not actually testing celery's revoke
        imp = DocumentImport.objects.create(
                document=self.document,
                import_file=ContentFile('', name='doesntmatter.xml'),
                workflow_state=DocumentImport.WORKFLOW_STATE_STARTED,
                processed=0)
        uri = reverse('api:document-cancel-import', kwargs={'pk': self.document.pk})
        response = self.client.post(uri)
        self.assertEqual(response.status_code, 200)
        
        # already canceled
        response = self.client.post(uri)
        self.assertEqual(response.status_code, 400)
        

class DocumentExportTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()

        self.trans = self.factory.make_transcription()
        self.user = self.trans.document.owner  # shortcut
        self.parts = []
        for i in range(1, 3):
            part = self.factory.make_part(name='part %d' % i,
                                     document=self.trans.document)
            self.parts.append(part)
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
            response = self.client.post(reverse('api:document-export',
                                            kwargs={'pk': self.trans.document.pk}),
                                    {'transcription': self.trans.pk,
                                     'file_format': 'text',
                                     'parts': json.dumps([str(p.pk) for p in self.parts])})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(''.join([c.decode() for c in response.streaming_content]),
                         "line 1:1\nline 1:2\nline 1:3\nline 2:1\nline 2:2\nline 2:3\n")
    
    def test_alto(self):
        self.client.force_login(self.user)
        with self.assertNumQueries(10):  # should be 8 + 4*part
            response = self.client.post(reverse('api:document-export',
                                                kwargs={'pk': self.trans.document.pk,}),
                                        {'transcription': self.trans.pk,
                                         'file_format':'alto',
                                         'parts': json.dumps([str(p.pk) for p in self.parts])})

        self.assertEqual(response.status_code, 200)
        #self.assertEqual(response.content, '')
    
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
        #with self.assertNumQueries(80):
        response = self.client.post(reverse('api:document-export',
                                            kwargs={'pk': self.trans.document.pk,}),
                                    {'transcription': self.trans.pk,
                                     'file_format': 'text',
                                     'parts': json.dumps([str(p.pk) for p in self.parts])})
        self.assertEqual(response.status_code, 200)
    
    def test_invalid(self):
        self.client.force_login(self.user)
        # invalid file format
        response = self.client.post(reverse('api:document-export',
                                       kwargs={'pk': self.trans.document.pk}),
                                        {'transcription': self.trans.pk,
                                         'file_format':'pouet',
                                         'parts': json.dumps([str(p.pk) for p in self.parts])})
        self.assertEqual(response.status_code, 400)

        # invalid pk
        response = self.client.post(reverse('api:document-export',
                                            kwargs={'pk': self.trans.document.pk}),
                                    {'transcription': self.trans.pk,
                                     'file_format':'text',
                                     'parts': json.dumps(['a', 'b'])})
        self.assertEqual(response.status_code, 400)

        # no img
        response = self.client.post(reverse('api:document-export',
                                            kwargs={'pk': self.trans.document.pk,}),
                                    {'transcription': self.trans.pk,
                                     'file_format': 'text',
                                     'parts': json.dumps([])})
        self.assertEqual(response.status_code, 400)
        
