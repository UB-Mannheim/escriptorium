from django.test import TestCase

from core.models import Block
from core.tests.factory import CoreFactory


class TasksTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.part = factory.make_part()

    def test_workflow(self):
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_CREATED)
        self.part.compress()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_COMPRESSED)
            
        self.part.binarize()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_BINARIZED)
    
        # self.part.segment()
        # self.assertEqual(self.part.workflow_state,
        #                  self.part.WORKFLOW_STATE_SEGMENTED)
        b = Block.objects.create(document_part=self.part,
                                 box=[0,0]+[self.part.image.width, self.part.image.height])
        self.part.blocks.add(b)
        self.part.segment()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_SEGMENTED)
        
        self.part.transcribe()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_TRANSCRIBING)
    
    def test_training(self):
        pass
