import unittest
import os

from django.urls import reverse
from django.test import TestCase, override_settings

from core.models import *
from core.tests.factory import CoreFactoryTestCase

# DO NOT REMOVE THIS IMPORT, it will break a lot of tests
# It is used to trigger Celery signals when running tests
from reporting.tasks import end_task_reporting, start_task_reporting


class TasksTestCase(CoreFactoryTestCase):
    def makeTranscriptionContent(self):
        self.part = self.factory.make_part()
        self.factory.make_part(document=self.part.document)
        self.factory.make_part(document=self.part.document)
        self.transcription = self.factory.make_transcription(document=self.part.document)
        self.factory.make_content(self.part, transcription=self.transcription)

    # This test fails on various lines...
    # self.part.convert(): ALWAYS_CONVERT settings is False, part.convert stops directly
    # self.part.transcribe(): No model is given to transcribe the DocumentPart
    @unittest.expectedFailure
    def test_workflow(self):
        self.part = self.factory.make_part()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_CREATED)
        self.part.convert()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_CONVERTED)
        self.part.compress()
        # b = Block.objects.create(document_part=self.part,
        #                          box=[0,0]+[self.part.image.width, self.part.image.height])
        # self.part.blocks.add(b)
        self.part.segment()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_SEGMENTED)

        self.part.transcribe()
        self.assertEqual(self.part.workflow_state,
                         self.part.WORKFLOW_STATE_TRANSCRIBING)

    # This test fails with an error because there isn't any default model for
    # transcription and none is given
    @unittest.expectedFailure
    def test_process_transcribe(self):
        self.makeTranscriptionContent()
        self.client.force_login(self.part.document.owner)
        uri = reverse('document-parts-process', kwargs={
            'pk': self.part.document.pk})
        parts = self.part.document.parts.all()
        for part in parts:
            part.workflow_state = part.WORKFLOW_STATE_CONVERTED
            part.save()

        response = self.client.post(uri, {
            'document': self.part.document.pk,
            'parts': [str(part.pk) for part in parts],
            'task': 'transcribe'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        self.assertEqual(part.workflow_state, part.WORKFLOW_STATE_TRANSCRIBING)

    @unittest.expectedFailure
    def test_train_new_transcription_model(self):
        self.makeTranscriptionContent()
        self.client.force_login(self.part.document.owner)
        uri = reverse('document-parts-process', kwargs={'pk': self.part.document.pk})
        with self.assertNumQueries(27):
            response = self.client.post(uri, {
                'document': self.part.document.pk,
                'transcription': self.transcription.pk,
                'parts': [str(part.pk) for part in self.part.document.parts.all()],
                'task': 'train',
                'model_name': 'new_test_model'})
            self.assertEqual(response.status_code, 200, response.content)

    @unittest.expectedFailure
    def test_train_existing_transcription_model(self):
        self.makeTranscriptionContent()
        model = self.factory.make_model(self.part.document)
        self.client.force_login(self.part.document.owner)
        uri = reverse('document-parts-process', kwargs={'pk': self.part.document.pk})
        with self.assertNumQueries(27):
            response = self.client.post(uri, {
                'document': self.part.document.pk,
                'transcription': self.transcription.pk,
                'parts': [str(part.pk) for part in self.part.document.parts.all()],
                'task': 'train',
                'train_model': model.pk})
        self.assertEqual(response.status_code, 200)

    @unittest.expectedFailure
    def test_process_segment(self):
        self.part = self.factory.make_part(image_asset='segmentation/cbad1.png')
        self.client.force_login(self.part.document.owner)
        uri = reverse('document-parts-process', kwargs={'pk': self.part.document.pk})
        with self.assertNumQueries(77):
            response = self.client.post(uri, {
                'document': self.part.document.pk,
                'parts': [str(self.part.pk)],
                'task': 'segment'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.part.lines.count(), 19)

    @unittest.skip
    def test_train_new_segmentation_model(self):
        self.part = self.factory.make_part(image_asset='segmentation/default.png')
        baselines = [[[13,31],[848,37]], [[99,93],[850,106]], [[15,157],[837,165]]]
        for baseline in baselines:
            l = Line.objects.create(document_part=self.part, baseline=baseline)
        self.part2 = self.factory.make_part(image_asset='segmentation/default2.png', document=self.part.document)
        baselines = [[[24,33],[225,42],[376,40],[524,46], [657,43],[731,56]],
                     [[52,81],[701,91]],
                     [[51,120],[233,123],[360,119],[673,127],[722,136]],
                     [[5,158],[155,165],[305,165],[540,170],[554,165],[689,177],[733,196]]]
        for baseline in baselines:
            l = Line.objects.create(document_part=self.part2, baseline=baseline)

        self.client.force_login(self.part.document.owner)
        uri = reverse('document-parts-process', kwargs={'pk': self.part.document.pk})
        with self.assertNumQueries(14):
            response = self.client.post(uri, {
                'document': self.part.document.pk,
                'parts': [str(self.part.pk), str(self.part2.pk)],
                'task': 'segtrain',
                'model_name': 'new_seg_model'
            })
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(self.part.lines.count(), 3)

    def test_train_existing_segmentation_model(self):
        pass
