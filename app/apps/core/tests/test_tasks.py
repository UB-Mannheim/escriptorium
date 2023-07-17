import unittest
from unittest.mock import patch

from django.urls import reverse

from core.models import Document, Line
from core.tasks import align
from core.tests.factory import CoreFactoryTestCase

# DO NOT REMOVE THIS IMPORT, it will break a lot of tests
# It is used to trigger Celery signals when running tests
from reporting.tasks import end_task_reporting  # noqa F401
from reporting.tasks import start_task_reporting  # noqa F401


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
            'task': 'transcribe',
            'transcription': None
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        part.refresh_from_db()
        self.assertEqual(part.workflow_state, part.WORKFLOW_STATE_TRANSCRIBING)

    @unittest.skip
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
        baselines = [[[13, 31], [848, 37]], [[99, 93], [850, 106]], [[15, 157], [837, 165]]]
        for baseline in baselines:
            Line.objects.create(document_part=self.part, baseline=baseline)
        self.part2 = self.factory.make_part(image_asset='segmentation/default2.png', document=self.part.document)
        baselines = [[[24, 33], [225, 42], [376, 40], [524, 46], [657, 43], [731, 56]],
                     [[52, 81], [701, 91]],
                     [[51, 120], [233, 123], [360, 119], [673, 127], [722, 136]],
                     [[5, 158], [155, 165], [305, 165], [540, 170], [554, 165], [689, 177], [733, 196]]]
        for baseline in baselines:
            Line.objects.create(document_part=self.part2, baseline=baseline)

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

    def test_align_task(self):
        """Unit tests for document alignment task"""
        # should log error on bad DocumentPart PK
        try:
            # ensure document with this pk actually does not exist
            Document.objects.get(pk=123456789).delete()
        except Document.DoesNotExist:
            pass
        with self.assertLogs('core.tasks') as mock_log:
            align.delay(document_pk=123456789)
            self.assertEqual(mock_log.output, ["ERROR:core.tasks:Trying to align text on non-existent Document: 123456789"])

        with patch("core.tasks.apps") as apps_mock:
            # should call apps.get_model and Document.objects.get
            align.delay(document_pk=1)
            apps_mock.get_model.assert_called_with('core', 'Document')
            apps_mock.get_model.return_value.objects.get.assert_called_with(pk=1)

            with patch("core.tasks.get_user_model") as get_user_model_mock:
                # should call User.objects.get
                align.delay(document_pk=1, user_pk=2)
                get_user_model_mock.assert_called()
                get_user_model_mock.return_value.objects.get.assert_called_with(pk=2)

                # should call part.align with transcription, witness pks (and default no parts [], n-gram of 4, merge=False)
                align.delay(document_pk=1, user_pk=2, transcription_pk=3, witness_pk=4)
                doc = apps_mock.get_model.return_value.objects.get.return_value
                doc.align.assert_called_with([], 3, 4, 25, 0, False, True, 0.8, ["Orphan", "Undefined"], None, 20, 600)

                # should call part.align with set n-gram value
                align.delay(document_pk=1, user_pk=2, transcription_pk=3, witness_pk=4, n_gram=2)
                doc.align.assert_called_with([], 3, 4, 2, 0, False, True, 0.8, ["Orphan", "Undefined"], None, 20, 600)

                # should call part.align with set parts
                align.delay(document_pk=1, part_pks=[1], user_pk=2, transcription_pk=3, witness_pk=4, n_gram=2)
                doc.align.assert_called_with([1], 3, 4, 2, 0, False, True, 0.8, ["Orphan", "Undefined"], None, 20, 600)

                # when part.align raises an exception:
                doc.align.side_effect = Exception
                # should notify the user about the exception, set the workflow state
                # back to transcribing, log the exception, and raise the exception
                with self.assertLogs('core.tasks') as mock_log:
                    with self.assertRaises(Exception):
                        align.delay(document_pk=1, part_pks=[1], user_pk=2, transcription_pk=3, witness_pk=4)
                    user = get_user_model_mock.return_value.objects.get.return_value
                    user.notify.assert_called()
                    apps_mock.get_model.assert_called_with('core', 'DocumentPart')
                    apps_mock.get_model.return_value.objects.filter.assert_called_with(pk__in=[1])
                    parts = apps_mock.get_model.return_value.objects.filter.return_value
                    apps_mock.get_model.return_value.objects.bulk_update.assert_called_with(parts, ["workflow_state"])
                    self.assertEqual(mock_log.output[0][:17], "ERROR:core.tasks:")
