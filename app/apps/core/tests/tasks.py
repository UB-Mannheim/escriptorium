from unittest.mock import patch

from django.tests import TestCase


class ProcessTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.part = factory.make_part()

    def test_compress(self):
        self.assertEqual(self.part.workflow_state,
                         self.part.WORFLOW_STATE_CREATED)
        self.part.compress()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORFLOW_STATE_CREATED)
    
    def test_binarization(self):
        pass
    
    def test_segmentation(self):
        pass
    
    def test_transcription(self):
        pass
    
    def test_training(self):
        pass
