import json

from django.urls import reverse
from django.test import TestCase, override_settings

from core.models import *
from core.tests.factory import CoreFactoryTestCase


class TasksTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.factory.make_part(document=self.part.document)
        self.factory.make_part(document=self.part.document)

    def test_workflow(self):
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_CREATED)
        self.part.compress()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_COMPRESSED)
            
        self.part.binarize()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_BINARIZED)
    
        b = Block.objects.create(document_part=self.part,
                                 box=[0,0]+[self.part.image.width, self.part.image.height])
        self.part.blocks.add(b)
        self.part.segment()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_SEGMENTED)
        
        self.part.transcribe()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_TRANSCRIBING)

    def test_post(self):
        self.client.force_login(self.part.document.owner)
        uri = reverse('document-parts-process', kwargs={
            'pk': self.part.document.pk})
        parts = self.part.document.parts.all()
        for part in parts:
            redis_.get('process-%d' % part.pk)
            part.workflow_state = part.WORKFLOW_STATE_COMPRESSED
            part.save()
        
        response = self.client.post(uri, {
            'document': self.part.document.pk,
            'parts': json.dumps([part.pk for part in parts]),
            'task': 'transcribe'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        self.assertEqual(part.workflow_state, part.WORKFLOW_STATE_TRANSCRIBING)
    
    def test_training(self):
        pass
