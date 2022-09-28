"""
The goal here is not to test drf internals
but only our own layer on top of it.
So no need to test the content unless there is some magic in the serializer.
"""

import unittest
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from core.models import (
    Block,
    DocumentMetadata,
    Line,
    LineTranscription,
    LineType,
    Metadata,
    OcrModel,
    Transcription,
)
from core.tests.factory import CoreFactoryTestCase


class UserViewSetTestCase(CoreFactoryTestCase):

    def setUp(self):
        super().setUp()

    def test_onboarding(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:user-detail', kwargs={'pk': user.pk})
        resp = self.client.patch(uri, {
            'onboarding': 'False',
        }, content_type='application/json')

        user.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(user.onboarding, False)


class DocumentViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.doc = self.factory.make_document()
        self.doc2 = self.factory.make_document(owner=self.doc.owner)
        self.part = self.factory.make_part(document=self.doc)
        self.part2 = self.factory.make_part(document=self.doc)

        self.line = Line.objects.create(
            baseline=[[10, 25], [50, 25]],
            mask=[[10, 10], [50, 10], [50, 50], [10, 50]],
            document_part=self.part)
        self.line2 = Line.objects.create(
            baseline=[[10, 80], [50, 80]],
            mask=[[10, 60], [50, 60], [50, 100], [10, 100]],
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

    def test_list(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        with self.assertNumQueries(16):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_detail(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-detail',
                      kwargs={'pk': self.doc.pk})
        with self.assertNumQueries(10):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_perm(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:document-detail',
                      kwargs={'pk': self.doc.pk})
        resp = self.client.get(uri)
        # Note: raises a 404 instead of 403 but its fine
        self.assertEqual(resp.status_code, 404)

    def test_segtrain_less_two_parts(self):
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        uri = reverse('api:document-segtrain', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk],
            'model': model.pk
        })

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], {'parts': [
            'Segmentation training requires at least 2 images.']})

    @unittest.skip
    def test_segtrain_new_model(self):
        # This test breaks CI as it consumes too many resources
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-segtrain', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model_name': 'new model'
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(OcrModel.objects.count(), 1)
        self.assertEqual(OcrModel.objects.first().name, "new model")

    @unittest.expectedFailure
    def test_segtrain_existing_model_rename(self):
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        uri = reverse('api:document-segtrain', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model': model.pk,
            'model_name': 'test new model'
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(OcrModel.objects.count(), 2)

    @unittest.expectedFailure
    def test_segment(self):
        uri = reverse('api:document-segment', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'seg_steps': 'both',
            'model': model.pk,
        })
        self.assertEqual(resp.status_code, 200)

    @unittest.expectedFailure
    def test_train_new_model(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-train', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model_name': 'testing new model',
            'transcription': self.transcription.pk
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.doc.ocr_models.filter(job=OcrModel.MODEL_JOB_RECOGNIZE).count(), 1)

    @unittest.expectedFailure
    def test_transcribe(self):
        trans = Transcription.objects.create(document=self.part.document)

        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_RECOGNIZE)
        uri = reverse('api:document-transcribe', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model': model.pk,
            'transcription': trans.pk
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'{"status":"ok"}')
        # won't work with dummy model and image
        # self.assertEqual(LineTranscription.objects.filter(transcription=trans).count(), 2)

    def test_list_document_with_tasks(self):
        # Creating a new Document that self.doc.owner shouldn't see
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report1 = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report1.start()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report")
        report2.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks'))

        json = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

    def test_list_document_with_tasks_staff_user(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        # Creating a new Document that self.doc.owner should also see since he is a staff member
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report")
        report2.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(8):
            resp = self.client.get(reverse('api:document-tasks'))

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 2)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
            {
                'pk': self.doc.pk,
                'name': self.doc.name,
                'owner': self.doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': self.doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
        ])

    def test_list_document_with_tasks_filter_wrong_user_id(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        self.client.force_login(self.doc.owner)
        resp = self.client.get(reverse('api:document-tasks') + '?user_id=blablabla')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {'error': 'Invalid user_id, it should be an int.'})

    def test_list_document_with_tasks_filter_user_id_disabled_for_normal_user(self):
        # Creating a new Document that self.doc.owner shouldn't see
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report")
        report2.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            # Filtering by user_id but the user is not part of the staff so the filter will be ignored
            resp = self.client.get(reverse('api:document-tasks') + f"?user_id={other_doc.owner.id}")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

    def test_list_document_with_tasks_filter_user_id(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks') + f"?user_id={other_doc.owner.id}")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        ])

    def test_list_document_with_tasks_filter_name(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        other_doc = self.factory.make_document(name="other doc", project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks') + "?name=other")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        ])

    def test_list_document_with_tasks_filter_wrong_task_state(self):
        self.client.force_login(self.doc.owner)
        resp = self.client.get(reverse('api:document-tasks') + '?task_state=wrongstate')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json(), {'error': 'Invalid task_state, it should match a valid workflow_state.'})

    def test_list_document_with_tasks_filter_task_state(self):
        self.doc.owner.is_staff = True
        self.doc.owner.save()
        other_doc = self.factory.make_document(project=self.factory.make_project(name="Test API"))
        report = other_doc.reports.create(user=other_doc.owner, label="Fake report")
        report.start()

        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(6):
            resp = self.client.get(reverse('api:document-tasks') + "?task_state=Running")

        self.assertEqual(resp.status_code, 200)
        json = resp.json()
        self.assertEqual(json['count'], 1)
        self.assertEqual(json['results'], [
            {
                'pk': other_doc.pk,
                'name': other_doc.name,
                'owner': other_doc.owner.username,
                'tasks_stats': {'Queued': 0, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
                'last_started_task': other_doc.reports.latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            },
        ])

    def test_cancel_all_tasks_for_document_not_found(self):
        self.client.force_login(self.doc.owner)
        with self.assertNumQueries(3):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': 2000}))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json(), {
            'error': "Document with pk 2000 doesn't exist",
            'status': 'Not Found'
        })

    def test_cancel_all_tasks_for_document_forbidden(self):
        # A normal user can't stop all tasks on a document he don't own
        user = self.factory.make_user()
        self.client.force_login(user)
        with self.assertNumQueries(4):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json(), {
            'detail': 'You do not have permission to perform this action.'
        })

    @patch('reporting.models.revoke')
    def test_cancel_all_tasks_for_document(self, mock_revoke):
        self.client.force_login(self.doc.owner)

        # Simulating a pending task
        report = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="11111", method="core.tasks.train")

        # Simulating a running training task
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="22222", method="core.tasks.train")
        report2.start()
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        model.training = True
        model.save()

        # Asserting that there is a running task on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 1, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

        # Stopping all tasks on self.doc
        def fake_revoke(id, terminate=False):
            if id == "11111":
                report.error('Canceled by celery')
            else:
                report2.error('Canceled by celery')

        mock_revoke.side_effect = fake_revoke
        with self.assertNumQueries(12):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {
            'status': 'canceled',
            'details': f'Canceled 2 pending/running tasks linked to document {self.doc.name}.'
        })
        self.assertEqual(mock_revoke.call_count, 2)

        # Assert that there is no more tasks running on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 0, 'Crashed': 0, 'Finished': 0, 'Canceled': 2},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])
        model.refresh_from_db()
        self.assertEqual(model.training, False)

    @patch('reporting.models.revoke')
    def test_cancel_all_tasks_for_document_staff_user(self, mock_revoke):
        # This user doesn't own self.doc but can cancel all of its tasks since he is a staff member
        user = self.factory.make_user()
        user.is_staff = True
        user.save()
        self.client.force_login(user)

        # Simulating a pending task
        report = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="11111", method="core.tasks.train")

        # Simulating a running training task
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", task_id="22222", method="core.tasks.train")
        report2.start()
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        model.training = True
        model.save()

        # Asserting that there is a running task on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 1, 'Running': 1, 'Crashed': 0, 'Finished': 0, 'Canceled': 0},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])

        # Stopping all tasks on self.doc
        def fake_revoke(id, terminate=False):
            if id == "11111":
                report.error('Canceled by celery')
            else:
                report2.error('Canceled by celery')

        mock_revoke.side_effect = fake_revoke
        with self.assertNumQueries(11):
            resp = self.client.post(reverse('api:document-cancel-tasks', kwargs={'pk': self.doc.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {
            'status': 'canceled',
            'details': f'Canceled 2 pending/running tasks linked to document {self.doc.name}.'
        })
        self.assertEqual(mock_revoke.call_count, 2)

        # Assert that there is no more tasks running on self.doc
        resp = self.client.get(reverse('api:document-tasks'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'], [{
            'pk': self.doc.pk,
            'name': self.doc.name,
            'owner': self.doc.owner.username,
            'tasks_stats': {'Queued': 0, 'Running': 0, 'Crashed': 0, 'Finished': 0, 'Canceled': 2},
            'last_started_task': self.doc.reports.filter(started_at__isnull=False).latest('started_at').started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }])
        model.refresh_from_db()
        self.assertEqual(model.training, False)


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
        with self.assertNumQueries(5):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_list_perm(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

    @override_settings(THUMBNAIL_ENABLE=False)
    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        with self.assertNumQueries(9):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_detail_perm(self):
        user = self.factory.make_user()
        self.client.force_login(user)
        uri = reverse('api:part-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'pk': self.part.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

    @override_settings(THUMBNAIL_ENABLE=False)
    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-list',
                      kwargs={'document_pk': self.part.document.pk})
        with self.assertNumQueries(14):
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
        with self.assertNumQueries(6):
            resp = self.client.patch(
                uri, {'transcription_progress': 50},
                content_type='application/json')
            self.assertEqual(resp.status_code, 200, resp.content)

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


class DocumentMetadataTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.doc = self.factory.make_document()
        metadatakey1 = Metadata.objects.create(name='testmeta1')
        self.dm1 = DocumentMetadata.objects.create(document=self.doc, key=metadatakey1, value='testval1')
        metadatakey2 = Metadata.objects.create(name='testmeta2')
        self.dm2 = DocumentMetadata.objects.create(document=self.doc, key=metadatakey2, value='testval2')

    def test_detail(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:metadata-detail',
                      kwargs={'document_pk': self.doc.pk,
                              'pk': self.dm1.pk})
        with self.assertNumQueries(6):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["key"], {"name": "testmeta1", "cidoc_id": None})
        self.assertEqual(resp.json()["value"], "testval1")

    def test_list(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:metadata-list',
                      kwargs={'document_pk': self.doc.pk})
        with self.assertNumQueries(8):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 2)

    def test_create(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:metadata-list',
                      kwargs={'document_pk': self.doc.pk})
        with self.assertNumQueries(6):
            resp = self.client.post(uri, {
                'key': {'name': 'testnewkey'},
                'value': 'testnewval'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 201, resp.content)


class BlockViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        for i in range(2):
            b = Block.objects.create(
                box=[10 + 50 * i, 10, 50 + 50 * i, 50],
                document_part=self.part)
        self.block = b

    def test_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
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
                'box': '[[10,10], [20,20], [50,50]]'
            })
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with self.assertNumQueries(5):
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
            box=[[10, 10], [10, 200], [200, 200], [200, 10]],
            document_part=self.part)
        self.line_type = LineType.objects.create(name='linetype')
        self.line = Line.objects.create(
            baseline=[[0, 0], [10, 10], [20, 20]],
            document_part=self.part,
            block=self.block,
            typology=self.line_type)
        self.line2 = Line.objects.create(
            document_part=self.part,
            block=self.block)
        self.orphan = Line.objects.create(
            baseline=[[30, 30], [40, 40], [50, 50]],
            document_part=self.part,
            block=None)

    # not used
    # def test_detail(self):
    # def test_list(self):

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {
                'document_part': self.part.pk,
                'baseline': '[[10, 10], [50, 50]]'
            })
        self.assertEqual(resp.status_code, 201, resp.content)
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
        with self.assertNumQueries(9):
            resp = self.client.post(uri, {'lines': [self.line.pk]},
                                    content_type='application/json')
        self.assertEqual(Line.objects.count(), 2)
        self.assertEqual(resp.status_code, 200)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(7):
            resp = self.client.put(uri, {'lines': [
                {'pk': self.line.pk,
                 'mask': '[[60, 40], [60, 50], [90, 50], [90, 40]]',
                 'region': None},
                {'pk': self.line2.pk,
                 'mask': '[[50, 40], [50, 30], [70, 30], [70, 40]]',
                 'region': self.block.pk}
            ]}, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.line.refresh_from_db()
        self.line2.refresh_from_db()
        self.assertEqual(self.line.mask, '[[60, 40], [60, 50], [90, 50], [90, 40]]')
        self.assertEqual(self.line2.mask, '[[50, 40], [50, 30], [70, 30], [70, 40]]')

    def test_bulk_update_order(self):
        order1, order2 = self.line.order, self.line2.order
        self.client.force_login(self.user)

        uri = reverse('api:line-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        resp = self.client.put(uri, {'lines': [
            {'pk': self.line.pk, 'order': order2},
            {'pk': self.line2.pk, 'order': order1}
        ]}, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)

        self.line.refresh_from_db()
        self.line2.refresh_from_db()
        self.assertEqual(self.line.order, order2)
        self.assertEqual(self.line2.order, order1)

    def test_merge(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-merge',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})

        # First merge will fail, because line2 doesn't have a baseline
        body = {'lines': [self.line.pk, self.line2.pk, self.orphan.pk]}
        resp = self.client.post(uri, body, content_type="application/json")
        self.assertEqual(resp.status_code, 400, resp.content)

        # Second merge should succeed
        body = {'lines': [self.line.pk, self.orphan.pk]}
        resp = self.client.post(uri, body, content_type="application/json")
        self.assertEqual(resp.status_code, 200, resp.content)

        created_pk = resp.data['lines']['created']['pk']
        created = Line.objects.get(pk=created_pk)
        self.assertEqual(created.typology.pk, self.line_type.pk)
        self.assertEqual(created.block.pk, self.block.pk)
        self.assertEqual(created.baseline, self.line.baseline + self.orphan.baseline)

        self.assertIsNone(Line.objects.filter(pk=self.line.pk).first())
        self.assertIsNone(Line.objects.filter(pk=self.orphan.pk).first())
        self.assertIsNotNone(Line.objects.filter(pk=self.line2.pk).first())


class LineTranscriptionViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.line = Line.objects.create(
            mask=[10, 10, 50, 50],
            document_part=self.part)
        self.line2 = Line.objects.create(
            mask=[10, 60, 50, 100],
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
        with self.assertNumQueries(6):
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
        uri = reverse('api:linetranscription-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.lt.pk})

        with self.assertNumQueries(8):
            resp = self.client.put(uri, {'content': 'test',
                                         'transcription': self.lt.transcription.pk,
                                         'line': self.lt.line.pk},
                                   content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.lt.refresh_from_db()
        self.assertEqual(len(self.lt.versions), 1)

    def test_bulk_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-create',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        ll = Line.objects.create(
            mask=[10, 10, 50, 50],
            document_part=self.part)
        with self.assertNumQueries(10):
            resp = self.client.post(
                uri,
                {'lines': [
                    {'line': ll.pk,
                     'transcription': self.transcription.pk,
                     'content': 'new transcription'},
                    {'line': ll.pk,
                     'transcription': self.transcription2.pk,
                     'content': 'new transcription 2'},
                ]}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})

        with self.assertNumQueries(15):
            resp = self.client.put(uri, {'lines': [
                {'pk': self.lt.pk,
                 'content': 'test1 new',
                 'transcription': self.transcription.pk,
                 'line': self.line.pk},
                {'pk': self.lt2.pk,
                 'content': 'test2 new',
                 'transcription': self.transcription.pk,
                 'line': self.line2.pk},
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
            resp = self.client.post(uri, {'lines': [self.lt.pk, self.lt2.pk]},
                                    content_type='application/json')
            lines = LineTranscription.objects.all()
            self.assertEqual(lines[0].content, "")
            self.assertEqual(lines[1].content, "")
            self.assertEqual(resp.status_code, 204)


class OcrModelViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.factory.make_user()

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:ocrmodel-list')
        model = SimpleUploadedFile("test_model.mlmodel",
                                   b"file_content")
        resp = self.client.post(uri, {'name': 'test_model',
                                      'job': 'Segment',
                                      'file': model})
        self.assertEqual(resp.status_code, 201)

    def test_shared_user(self):
        doc = self.factory.make_document()
        user2 = self.factory.make_user()
        model = self.factory.make_model(doc)
        model.ocr_model_rights.create(ocr_model=model, user=user2)

        self.client.force_login(user2)
        uri = reverse('api:ocrmodel-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()['count'], 1)

    def test_shared_group(self):
        doc = self.factory.make_document()
        user2 = self.factory.make_user()
        group = self.factory.make_group(users=[user2])
        model = self.factory.make_model(doc)
        model.ocr_model_rights.create(ocr_model=model, group=group)

        self.client.force_login(user2)
        uri = reverse('api:ocrmodel-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()['count'], 1)


class ProjectViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.project = self.factory.make_project()

    def test_regression_read_all_projects(self):
        other_user = self.factory.make_user()
        self.factory.make_project(owner=other_user)
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 1)

    def test_create(self):
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.post(uri, {'name': 'test proj'})
        self.assertEqual(resp.status_code, 201)


class DocumentPartMetadataTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:partmetadata-list',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(6):
            resp = self.client.post(uri, {'key': {'name': 'testname', 'cidoc': 'testcidoc'},
                                          'value': 'testvalue'},
                                    content_type='application/json')
        mds = self.part.metadata.all()
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(mds[0].key.name, "testname")
        self.assertEqual(mds[0].value, "testvalue")

    def test_create_existing_key(self):
        self.client.force_login(self.user)
        self.factory.make_part_metadata(self.part)
        uri = reverse('api:partmetadata-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})
        with self.assertNumQueries(5):
            resp = self.client.post(uri, {'key': {'name': 'testmd'},
                                          'value': 'testvalue2'},
                                    content_type='application/json')
        mds = self.part.metadata.all().order_by('id')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(mds[0].key.name, "testmd")
        self.assertEqual(mds[0].value, "testmdvalue")
        self.assertEqual(mds[1].key.name, "testmd")
        self.assertEqual(mds[1].value, "testvalue2")

    def test_update_key(self):
        md = self.factory.make_part_metadata(self.part)
        self.client.force_login(self.user)
        uri = reverse('api:partmetadata-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': md.pk})
        with self.assertNumQueries(8):
            resp = self.client.patch(uri, {'key': {'name': 'testname2'}},
                                     content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        mds = self.part.metadata.all()
        self.assertEqual(mds[0].key.name, "testname2")

    def test_update_value(self):
        self.client.force_login(self.user)
        md = self.factory.make_part_metadata(self.part)
        uri = reverse('api:partmetadata-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': md.pk})
        with self.assertNumQueries(7):
            resp = self.client.patch(uri, {'value': 'testvalue2'},
                                     content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        mds = self.part.metadata.all()
        self.assertEqual(mds[0].value, "testvalue2")

    def test_delete(self):
        self.client.force_login(self.user)
        md = self.factory.make_part_metadata(self.part)
        uri = reverse('api:partmetadata-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': md.pk})
        with self.assertNumQueries(5):
            resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertEqual(self.part.metadata.count(), 0)
