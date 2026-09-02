"""
The goal here is not to test drf internals
but only our own layer on top of it.
So no need to test the content unless there is some magic in the serializer.
"""

import tempfile
import unittest
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from core.models import (
    Block,
    BlockType,
    Document,
    DocumentMetadata,
    DocumentPart,
    DocumentTag,
    Line,
    LineTranscription,
    LineType,
    Metadata,
    OcrModel,
    ProjectTag,
    TextualWitness,
    Transcription,
    VirtualCollection,
)
from core.tests.factory import CoreFactoryTestCase
from reporting.models import TaskGroup, TaskReport


class UserViewSetTestCase(CoreFactoryTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.factory.make_user()
        self.user2 = self.factory.make_user()
        self.admin = self.factory.make_user(is_staff=True)

    def test_simple_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-list')
        with self.assertNumQueries(6):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_simple_detail(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-detail', kwargs={'pk': self.user.pk})
        with self.assertNumQueries(5):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_only_admins_see_everyone(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.data['count'], 1)

        self.client.force_login(self.admin)
        resp = self.client.get(uri)
        self.assertEqual(resp.data['count'], 3)

    def test_user_cant_access_another_user(self):
        self.client.force_login(self.user)
        uri = reverse('api:user-detail', kwargs={'pk': self.user2.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 404)

    def test_get_project_tags(self):
        project = self.factory.make_project()
        tag = self.factory.make_project_tag(user=self.user)
        project.tags.add(tag)
        self.client.force_login(self.user)
        uri = reverse('api:project-tag-list')
        with self.assertNumQueries(4):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_create_project_tag(self):
        self.client.force_login(self.user)

        uri = reverse('api:project-tag-list')
        with self.assertNumQueries(3):
            resp = self.client.post(uri, {
                'name': 'test-tag',
                'color': '#123456'
            })
            self.assertEqual(resp.status_code, 201, resp.content)

    def test_get_current_user(self):
        uri = reverse('api:user-current')

        # should respond with 401 unauthorized if not logged in
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 401)

        # should respond with the current user with status 200 when logged in
        self.client.force_login(self.user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["pk"], self.user.pk)
        self.assertEqual(resp.json()["is_staff"], False)

        # should correctly respond for an admin user is_staff=True
        self.client.force_login(self.admin)
        resp = self.client.get(uri)
        self.assertEqual(resp.json()["pk"], self.admin.pk)
        self.assertEqual(resp.json()["is_staff"], True)


class DocumentViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.proj1 = self.factory.make_project(name='proj1')
        self.proj2 = self.factory.make_project(name='proj2', owner=self.proj1.owner)
        self.doc = self.factory.make_document(project=self.proj1, owner=self.proj1.owner)
        self.doc2 = self.factory.make_document(project=self.proj2, owner=self.proj1.owner)
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
        with self.assertNumQueries(14):
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

    def test_create_block_type_dedups_by_name(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:blocktype-list')

        resp1 = self.client.post(uri, {'name': 'MainZone'})
        self.assertEqual(resp1.status_code, 201)
        resp2 = self.client.post(uri, {'name': 'MainZone'})
        self.assertEqual(resp2.status_code, 201)

        self.assertEqual(resp1.json()['pk'], resp2.json()['pk'])
        self.assertEqual(BlockType.objects.filter(name='MainZone').count(), 1)

    def test_modify_ontology_template_pk_creates_owned_copy(self):
        template = BlockType.objects.create(name='MainZone', public=True, color='#123456')

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-modify-ontology', kwargs={'pk': self.doc.pk})
        resp = self.client.patch(
            uri,
            data={'valid_block_types': [template.pk]},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

        owned = BlockType.objects.get(document=self.doc, name='MainZone')
        self.assertEqual(owned.color, '#123456')
        self.assertNotEqual(owned.pk, template.pk)

    def test_modify_ontology_omitted_owned_pk_is_deleted(self):
        kept = BlockType.objects.create(name='Kept', document=self.doc)
        removed = BlockType.objects.create(name='Removed', document=self.doc)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-modify-ontology', kwargs={'pk': self.doc.pk})
        resp = self.client.patch(
            uri,
            data={'valid_block_types': [kept.pk]},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

        self.assertTrue(BlockType.objects.filter(pk=kept.pk).exists())
        self.assertFalse(BlockType.objects.filter(pk=removed.pk).exists())

    def test_modify_ontology_pk_owned_by_other_document_rejected(self):
        other_doc_type = BlockType.objects.create(name='Other', document=self.doc2)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-modify-ontology', kwargs={'pk': self.doc.pk})
        resp = self.client.patch(
            uri,
            data={'valid_block_types': [other_doc_type.pk]},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

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

    def test_share_group(self):
        self.client.force_login(self.doc.owner)
        group = self.factory.make_group(users=[self.doc.owner])

        uri = reverse('api:document-share', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_groups'][0]['pk'], group.pk)

    def test_share_group_not_part_of(self):
        self.client.force_login(self.doc.owner)
        group = self.factory.make_group()  # owner is not part of the group

        uri = reverse('api:document-share', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 400)

    def test_share_user(self):
        self.client.force_login(self.doc.owner)
        user = self.factory.make_user()

        uri = reverse('api:document-share', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, {'user': user.username})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_users'][0]['pk'], user.pk)

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

    @unittest.skip
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

    @patch('api.serializers.segment')
    def test_segment_routes_to_default_queue_for_regular_model(self, mock_segment):
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        uri = reverse('api:document-segment', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'seg_steps': 'both',
            'model': model.pk,
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_segment.si.return_value.apply_async.assert_called_with(queue=None)

    @patch('api.serializers.segment')
    def test_segment_routes_to_intensive_inference_queue_for_dfine_model(self, mock_segment):
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_SEGMENT)
        model.architecture = 'DFINEModel'
        model.save()
        uri = reverse('api:document-segment', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'seg_steps': 'both',
            'model': model.pk,
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_segment.si.return_value.apply_async.assert_called_with(queue='intensive-inference')

    @patch('api.serializers.transcribe')
    def test_transcribe_routes_to_default_queue_for_regular_model(self, mock_transcribe):
        trans = Transcription.objects.create(document=self.part.document)
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_RECOGNIZE)
        uri = reverse('api:document-transcribe', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model': model.pk,
            'transcription': trans.pk
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_transcribe.si.return_value.apply_async.assert_called_with(queue=None)

    @patch('api.serializers.transcribe')
    def test_transcribe_routes_to_intensive_inference_queue_for_dfine_model(self, mock_transcribe):
        trans = Transcription.objects.create(document=self.part.document)
        self.client.force_login(self.doc.owner)
        model = self.factory.make_model(self.doc, job=OcrModel.MODEL_JOB_RECOGNIZE)
        model.architecture = 'DFINEModel'
        model.save()
        uri = reverse('api:document-transcribe', kwargs={'pk': self.doc.pk})
        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'model': model.pk,
            'transcription': trans.pk
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_transcribe.si.return_value.apply_async.assert_called_with(queue='intensive-inference')

    def test_align(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-align', kwargs={'pk': self.doc.pk})

        witness = self.factory.make_witness(owner=self.doc.owner)

        resp = self.client.post(uri, data={
            'parts': [self.part.pk, self.part2.pk],
            'transcription': Transcription.objects.first().pk,

            "existing_witness": witness.pk,
            "n_gram": 2,
            "max_offset": 20,
            "merge": False,
            "full_doc": True,
            "threshold": 0.8,
            "region_types": ["Orphan", "Undefined"],
            "layer_name": "example",
            # "beam_size": 10,
            "gap": 1000000,
            "add_hyphens": False,
        })

        self.assertEqual(resp.status_code, 200, resp.content)

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

    @patch('escriptorium.celery.app.control.revoke')
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
        with self.assertNumQueries(16):
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

    @patch('escriptorium.celery.app.control.revoke')
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
        with self.assertNumQueries(15):
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

    def test_task_group(self):
        # make fake reports
        group = TaskGroup.objects.create(created_by=self.doc.owner, document=self.doc)

        # pending
        self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                task_id="11111", method="core.tasks.train")
        # running
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="22222", method="core.tasks.train")
        report2.start()
        # canceled
        report3 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="33333", method="core.tasks.train")
        report3.cancel(self.doc.owner)
        # error
        report4 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="44444", method="core.tasks.train")
        report4.error("Something terrible happened.")
        # finished
        report5 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="55555", method="core.tasks.train")
        report5.end()
        report6 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                          task_id="66666", method="core.tasks.train")
        report6.end()

        self.client.force_login(self.doc.owner)
        uri = reverse('api:task-group-list', kwargs={'document_pk': self.doc.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['results'][0]['method'], "core.tasks.train")
        data = {t['workflow_state']: t['count'] for t in resp.json()['results'][0]['tasks']}
        self.assertEqual(data['Queued'], 1)
        self.assertEqual(data['Running'], 1)
        self.assertEqual(data['Crashed'], 1)
        self.assertEqual(data['Finished'], 2)
        self.assertEqual(data['Canceled'], 1)

    def test_unrelated_task_group(self):
        group = TaskGroup.objects.create(created_by=self.doc.owner, document=self.doc)
        # unrelated group
        group2 = TaskGroup.objects.create(created_by=self.doc.owner, document=self.doc2)

        report = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group,
                                         task_id="111111", method="core.tasks.train")
        report.end()
        report2 = self.doc.reports.create(user=self.doc.owner, label="Fake report", group=group2,
                                          task_id="222222", method="core.tasks.train")
        report2.end()

        self.client.force_login(self.doc.owner)
        uri = reverse('api:task-group-list', kwargs={'document_pk': self.doc.pk})
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 1)
        data = {t['workflow_state']: t['count'] for t in resp.json()['results'][0]['tasks']}
        self.assertEqual(data['Finished'], 1)

    def test_filter_project(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?project=' + str(self.doc.project.pk))
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['pk'], self.doc.pk)

    def test_filter_tags(self):
        tag1 = self.factory.make_document_tag(project=self.doc.project, name='tag1')
        tag2 = self.factory.make_document_tag(project=self.doc.project, name='tag2')
        self.doc.tags.add(tag1)
        self.doc2.tags.add(tag1)
        self.doc2.tags.add(tag2)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['pk'], self.doc2.pk)

        # test OR logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + '|' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 2)

        # test AND logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + ',' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)

    def test_filter_no_tag(self):
        tag1 = self.factory.make_document_tag(project=self.doc.project)
        self.doc.tags.add(tag1)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=none')
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['pk'], self.doc2.pk)

        resp = self.client.get(uri + '?tags=none|' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

    def test_stats(self):
        part = self.factory.make_part(document=self.doc)
        transcription = self.factory.make_transcription(document=self.doc)
        self.factory.make_content(part, transcription=transcription)
        self.factory.make_img_annotations(part)
        self.factory.make_text_annotations(part, transcription)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-stats', kwargs={'pk': self.doc.pk})
        with self.assertNumQueries(9):
            # request an explicit ordering, since the default "-frequency"
            # ordering is non-deterministic for typologies with equal frequency
            resp = self.client.get(uri + '?ordering=typology')
            self.assertEqual(resp.status_code, 200)

            self.assertEqual(resp.data["regions"][0]["typology_name"], "blocktype")
            self.assertEqual(resp.data["regions"][0]["frequency"], 1)
            self.assertEqual(resp.data["lines"][0]["typology_name"], "linetype0")
            self.assertEqual(resp.data["lines"][0]["frequency"], 6)
            self.assertEqual(resp.data["lines"][1]["typology_name"], "linetype1")
            self.assertEqual(resp.data["lines"][1]["frequency"], 6)

            self.assertEqual(resp.data["image_annotations"][0]["taxonomy_name"], "imgtaxo")
            self.assertEqual(resp.data["image_annotations"][0]["frequency"], 3)

            self.assertEqual(resp.data["text_annotations"][0]["taxonomy_name"], "texttaxo")
            self.assertEqual(resp.data["text_annotations"][0]["frequency"], 3)

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    })
    def test_stats_cache_refresh(self):
        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-stats', kwargs={'pk': self.doc.pk})

        # first call, no regions yet: gets cached
        resp = self.client.get(uri)
        self.assertEqual(resp.data["regions"], [])

        # a region is added, but the stale cached response is still returned
        self.factory.make_content(self.factory.make_part(document=self.doc))
        resp = self.client.get(uri)
        self.assertEqual(resp.data["regions"], [])

        # forcing a refresh bypasses and updates the cache
        resp = self.client.get(uri, {'refresh': 'true'})
        self.assertEqual(resp.data["regions"][0]["frequency"], 1)

        # subsequent calls without refresh now get the fresh cached value
        resp = self.client.get(uri)
        self.assertEqual(resp.data["regions"][0]["frequency"], 1)

    def test_elements_by_type(self):
        part = self.factory.make_part(document=self.doc)
        transcription = self.factory.make_transcription(document=self.doc)
        self.factory.make_content(part, transcription=transcription)

        self.client.force_login(self.doc.owner)
        uri = reverse('api:document-stats', kwargs={'pk': self.doc.pk})
        stats_resp = self.client.get(uri)
        region_type_id = stats_resp.data["regions"][0]["typology_id"]

        uri = reverse('api:document-elements-by-type', kwargs={'pk': self.doc.pk})
        resp = self.client.get(uri, {'category': 'regions', 'type': region_type_id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["parts"]), 1)
        self.assertEqual(resp.data["parts"][0]["document_part_id"], part.pk)
        self.assertEqual(resp.data["parts"][0]["frequency"], 1)
        self.assertEqual(resp.data["parts"][0]["part_filename"], part.original_filename)

        resp = self.client.get(uri, {'category': 'regions', 'type': 'none'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["parts"]), 0)

        resp = self.client.get(uri, {'category': 'invalid', 'type': 'none'})
        self.assertEqual(resp.status_code, 400)


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
        with self.assertNumQueries(9):
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
        with self.assertNumQueries(11):
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
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(26):
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
        with self.assertNumQueries(11):
            resp = self.client.patch(
                uri, {'transcription_progress': 50},
                content_type='application/json')
            self.assertEqual(resp.status_code, 200, resp.content)

    def test_move(self):
        self.client.force_login(self.user)
        uri = reverse('api:part-move',
                      kwargs={'document_pk': self.part2.document.pk,
                              'pk': self.part2.pk})
        with self.assertNumQueries(10):
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
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(12):
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
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(12):
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
        with self.assertNumQueries(12):
            resp = self.client.patch(uri, {
                'box': '[[100,100], [150,150]]'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_delete(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertFalse(Block.objects.filter(pk=self.block.pk).exists())

    def test_update_locked(self):
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})

        # patching only locked doesn't touch other fields
        resp = self.client.patch(uri, {'locked': True}, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.block.refresh_from_db()
        self.assertTrue(self.block.locked)

        # a full update must pass locked through explicitly, or it gets reset
        resp = self.client.put(uri, {
            'document_part': self.part.pk,
            'box': [[10, 10], [20, 20], [50, 50]],
            'locked': True,
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.block.refresh_from_db()
        self.assertTrue(self.block.locked)

    def test_delete_acquires_document_part_lock(self):
        # Regression test: block delete must SELECT FOR UPDATE the parent
        # DocumentPart before running ordered_model's reorder UPDATE, so that
        # concurrent deletes on the same part are serialized rather than
        # deadlocking on each other's row locks.
        self.client.force_login(self.user)
        uri = reverse('api:block-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.block.pk})
        with patch('api.views.DocumentPart.objects.select_for_update',
                   wraps=DocumentPart.objects.select_for_update) as mock_sfu:
            resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 204, resp.content)
        mock_sfu.assert_called_once_with()


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
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(13):
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
        with self.assertNumQueries(13):
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
        # +1 over the unscoped version: the queryset now runs the document
        # permission check instead of deleting straight off Line.objects
        with self.assertNumQueries(13):
            resp = self.client.post(uri, {'lines': [self.line.pk]},
                                    content_type='application/json')
        self.assertEqual(Line.objects.count(), 2)
        self.assertEqual(resp.status_code, 200)

    def test_bulk_update(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-bulk-update',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        with self.assertNumQueries(23):
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

        # second merge will fail, because 'lines' is mandatory
        body = {}
        resp = self.client.post(uri, body, content_type="application/json")
        self.assertEqual(resp.status_code, 400, resp.content)

        # third merge should succeed
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

    def test_merge_empty_list_returns_400(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-merge', kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        resp = self.client.post(uri, {'lines': []}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("mandatory", resp.json()['error'])

    def test_delete(self):
        self.client.force_login(self.user)
        uri = reverse('api:line-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.line.pk})
        resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(Line.objects.filter(pk=self.line.pk).exists())

    def test_delete_acquires_document_part_lock(self):
        # Regression test: line delete must SELECT FOR UPDATE the parent
        # DocumentPart before running ordered_model's reorder UPDATE, so that
        # concurrent deletes on the same part are serialized rather than
        # deadlocking on each other's row locks.
        self.client.force_login(self.user)
        uri = reverse('api:line-detail',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk,
                              'pk': self.line.pk})
        with patch('api.views.DocumentPart.objects.select_for_update',
                   wraps=DocumentPart.objects.select_for_update) as mock_sfu:
            resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 200, resp.content)
        mock_sfu.assert_called_once_with()


class TranscriptionViewSetTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner
        self.transcription = self.factory.make_transcription(document=self.part.document)

    def test_stats(self):
        self.factory.make_content(self.part, transcription=self.transcription)
        self.client.force_login(self.user)
        uri = reverse('api:transcription-stats', kwargs={
            'document_pk': self.part.document.pk,
            'pk': self.transcription.pk
        })

        with self.assertNumQueries(6):
            resp = self.client.get(uri)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data['characters'][0]['char'], ' ')
            self.assertEqual(resp.data['characters'][0]['frequency'], 191)
            self.assertEqual(resp.data['characters'][1]['char'], 'e')
            self.assertEqual(resp.data['characters'][1]['frequency'], 44)
            self.assertEqual(resp.data['characters'][2]['char'], 'M')
            self.assertEqual(resp.data['characters'][2]['frequency'], 43)
            self.assertEqual(resp.data['characters'][-1]['char'], 'I')
            self.assertEqual(resp.data['characters'][-1]['frequency'], 20)

            self.assertEqual(resp.data['line_count'], 30)

    def test_stats_ordering(self):
        self.factory.make_content(self.part, transcription=self.transcription)
        self.client.force_login(self.user)
        uri = reverse('api:transcription-stats', kwargs={
            'document_pk': self.part.document.pk,
            'pk': self.transcription.pk
        }) + '?ordering=char'
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['characters'][0]['char'], ' ')
        self.assertEqual(resp.data['characters'][-1]['char'], 'Z')

    def test_parts_by_char(self):
        self.factory.make_content(self.part, transcription=self.transcription)
        self.client.force_login(self.user)
        uri = reverse('api:transcription-parts-by-char', kwargs={
            'document_pk': self.part.document.pk,
            'pk': self.transcription.pk
        })

        resp = self.client.get(uri, {'char': 'e'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['parts']), 1)
        self.assertEqual(resp.data['parts'][0]['document_part_id'], self.part.pk)
        self.assertEqual(resp.data['parts'][0]['frequency'], 44)

        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 400)


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
        with self.assertNumQueries(14):
            resp = self.client.patch(uri, {
                'content': 'update'
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:linetranscription-list',
                      kwargs={'document_pk': self.part.document.pk,
                              'part_pk': self.part.pk})

        # +1: the part is now resolved through the authorised document
        with self.assertNumQueries(26):
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

        with self.assertNumQueries(16):
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
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(29):
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

        # -2: the scoped queryset select_related's line and transcription,
        # which the per-pk LineTranscription.objects lookups did not
        # -1: the part is resolved once and cached on the view
        with self.assertNumQueries(33):
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
        # +1: the document permission check
        with self.assertNumQueries(6):
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

    def test_list(self):
        self.client.force_login(self.user)
        uri = reverse('api:ocrmodel-list')
        with self.assertNumQueries(3):
            resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

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

    def test_no_duplicates(self):
        # regression test
        doc = self.factory.make_document(owner=self.user)
        user2 = self.factory.make_user()
        model = self.factory.make_model(doc)
        group = self.factory.make_group(users=[self.user, user2])
        model.ocr_model_rights.create(ocr_model=model, user=user2)
        model.ocr_model_rights.create(ocr_model=model, group=group)

        self.client.force_login(self.user)
        uri = reverse('api:ocrmodel-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertEqual(resp.json()['count'], 1, resp.json())


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

    def test_documents_count(self):
        self.factory.make_document(project=self.project)
        uri = reverse('api:project-list')
        self.client.force_login(self.project.owner)
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['results'][0]['documents_count'], 1)
        # adding an archived document should not increase the count
        self.factory.make_document(project=self.project, workflow_state=Document.WORKFLOW_STATE_ARCHIVED)
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['results'][0]['documents_count'], 1)

    def test_add_tag_to_project(self):
        tag = self.factory.make_project_tag(user=self.project.owner)
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-detail', kwargs={'pk': self.project.pk})
        with self.assertNumQueries(13):
            resp = self.client.patch(uri, {
                'tags': [tag.pk]
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.project.tags.count(), 1)

    def test_remove_tag_from_project(self):
        tag1 = self.factory.make_project_tag(name='tag1', user=self.project.owner)
        tag2 = self.factory.make_project_tag(name='tag2', user=self.project.owner)
        self.project.tags.add(tag1)
        self.project.tags.add(tag2)
        self.assertEqual(self.project.tags.count(), 2)
        self.client.force_login(self.project.owner)
        uri = reverse('api:project-detail', kwargs={'pk': self.project.pk})
        with self.assertNumQueries(13):
            resp = self.client.patch(uri, {
                'tags': [tag2.pk]
            }, content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self.project.tags.count(), 1)

    def test_filter_tags(self):
        project2 = self.factory.make_project(owner=self.project.owner, name='proj2')
        self.factory.make_project(owner=self.project.owner, name='proj3')
        tag1 = self.factory.make_project_tag(user=self.project.owner, name='tag1')
        tag2 = self.factory.make_project_tag(user=self.project.owner, name='tag2')
        self.project.tags.add(tag1)
        project2.tags.add(tag1)
        project2.tags.add(tag2)

        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.get(uri)
        self.assertEqual(resp.json()['count'], 3)

        resp = self.client.get(uri + '?tags=' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['id'], project2.pk)

        # test OR logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + '|' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 2)

        # test AND logic
        resp = self.client.get(uri + '?tags=' + str(tag1.pk) + ',' + str(tag2.pk))
        self.assertEqual(resp.json()['count'], 1)

    def test_filter_no_tag(self):
        tag1 = self.factory.make_project_tag(user=self.project.owner)
        self.project.tags.add(tag1)
        project_without_tag = self.factory.make_project(name="proj without tags",
                                                        owner=self.project.owner)

        self.client.force_login(self.project.owner)
        uri = reverse('api:project-list')
        resp = self.client.get(uri)

        self.assertEqual(resp.json()['count'], 2)

        resp = self.client.get(uri + '?tags=none')
        self.assertEqual(resp.json()['count'], 1)
        self.assertEqual(resp.json()['results'][0]['id'], project_without_tag.pk)

        resp = self.client.get(uri + '?tags=none|' + str(tag1.pk))
        self.assertEqual(resp.json()['count'], 2)

    def test_share_group(self):
        self.client.force_login(self.project.owner)
        group = self.factory.make_group(users=[self.project.owner])

        uri = reverse('api:project-share', kwargs={'pk': self.project.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_groups'][0]['pk'], group.pk)

    def test_share_group_not_part_of(self):
        self.client.force_login(self.project.owner)
        group = self.factory.make_group()  # owner is not part of the group

        uri = reverse('api:project-share', kwargs={'pk': self.project.pk})
        resp = self.client.post(uri, {'group': group.pk})

        self.assertEqual(resp.status_code, 400)

    def test_share_user(self):
        self.client.force_login(self.project.owner)
        user = self.factory.make_user()

        uri = reverse('api:project-share', kwargs={'pk': self.project.pk})
        resp = self.client.post(uri, {'user': user.username})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['shared_with_users'][0]['pk'], user.pk)


class DocumentPartMetadataTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.part = self.factory.make_part()
        self.user = self.part.document.owner

    def test_create(self):
        self.client.force_login(self.user)
        uri = reverse('api:partmetadata-list',
                      kwargs={'document_pk': self.part.document.pk, 'part_pk': self.part.pk})
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(15):
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
        # +1: create now authorises the document, which it did not
        # do when the check hung off get_queryset()
        with self.assertNumQueries(12):
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
        with self.assertNumQueries(14):
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
        with self.assertNumQueries(13):
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
        # +1: create now authorises the document, which it did not do when
        # the check hung off get_queryset()
        with self.assertNumQueries(6):
            resp = self.client.delete(uri)
        self.assertEqual(resp.status_code, 204, resp.content)
        self.assertEqual(self.part.metadata.count(), 0)


class RelatedFieldNarrowingTestCase(CoreFactoryTestCase):
    """
    Narrowing a many=True related field has to reach its child_relation:
    that is where DRF resolves each pk.
    """

    def setUp(self):
        super().setUp()
        self.mine = self.factory.make_part()
        self.theirs = self.factory.make_part()
        self.assertNotEqual(self.mine.document.owner, self.theirs.document.owner)
        self.client.force_login(self.mine.document.owner)
        self.uri = reverse('api:document-segment',
                           kwargs={'pk': self.mine.document.pk})

    @patch('api.serializers.segment')
    def test_segment_only_accepts_parts_of_its_document(self, mock_segment):
        # the task is only ever handed parts of the document in the URL
        resp = self.client.post(self.uri, data={
            'parts': [self.theirs.pk],
            'steps': 'both',
        })
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(mock_segment.si.called)

    @patch('api.serializers.segment')
    def test_segment_accepts_its_own_parts(self, mock_segment):
        resp = self.client.post(self.uri, data={
            'parts': [self.mine.pk],
            'steps': 'both',
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(mock_segment.si.call_args.kwargs['instance_pks'],
                         [self.mine.pk])


class PkScopingTestCase(CoreFactoryTestCase):
    """Endpoints that take pks in the body resolve them through the
    viewset queryset, so they stay within the object named in the URL.

    Note the fixture: factory.make_project() get_or_creates on the slug, so
    calling it without a name returns one shared project for every document -
    and its owner then has legitimate project-owner rights over the second
    document. Both therefore get an explicitly named project, and setUp
    asserts the separation before any test runs.
    """

    def setUp(self):
        super().setUp()
        self.caller = self.factory.make_user()
        caller_doc = self.factory.make_document(
            owner=self.caller,
            project=self.factory.make_project(name='caller project',
                                              owner=self.caller))
        self.mine = self.factory.make_part(document=caller_doc)

        self.other = self.factory.make_user()
        other_doc = self.factory.make_document(
            owner=self.other,
            project=self.factory.make_project(name='other project',
                                              owner=self.other))
        self.theirs = self.factory.make_part(document=other_doc)

        self.assertNotIn(other_doc, Document.objects.for_user(self.caller))

        self.other_line = Line.objects.create(
            document_part=self.theirs, baseline=[[0, 0], [10, 10]])
        self.other_line2 = Line.objects.create(
            document_part=self.theirs, baseline=[[20, 20], [30, 30]])
        self.other_lt = self.other_line.transcriptions.create(
            transcription=other_doc.transcriptions.first(),
            content='other content')

        self.client.force_login(self.caller)
        self.kwargs = {'document_pk': self.mine.document.pk,
                       'part_pk': self.mine.pk}

    def call(self, name, payload, method='post'):
        return getattr(self.client, method)(
            reverse(name, kwargs=self.kwargs), data=payload,
            content_type='application/json')

    def test_line_bulk_delete_is_scoped_to_the_part(self):
        resp = self.call('api:line-bulk-delete', {'lines': [self.other_line.pk]})
        self.assertTrue(Line.objects.filter(pk=self.other_line.pk).exists())
        self.assertNotIn(b'other content', resp.content)

    def test_line_merge_is_scoped_to_the_part(self):
        resp = self.call('api:line-merge',
                         {'lines': [self.other_line.pk, self.other_line2.pk]})
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertTrue(Line.objects.filter(pk=self.other_line.pk).exists())
        self.assertNotIn(b'other content', resp.content)

    def test_line_move_is_scoped_to_the_part(self):
        resp = self.call('api:line-move',
                         {'lines': [{'pk': self.other_line.pk, 'order': 5}]})
        self.assertEqual(resp.status_code, 404, resp.content)
        self.other_line.refresh_from_db()
        self.assertEqual(self.other_line.order, 0)

    def test_line_bulk_create_ignores_payload_part(self):
        # document_part in the body must not override the part in the URL
        self.call('api:line-bulk-create',
                  {'lines': [{'document_part': self.theirs.pk,
                              'baseline': [[1, 1], [2, 2]]}]})
        self.assertEqual(Line.objects.filter(document_part=self.theirs).count(), 2)

    def test_line_bulk_create_requires_a_part_of_the_document(self):
        # a document_pk paired with a part_pk from another document
        resp = self.client.post(
            reverse('api:line-bulk-create',
                    kwargs={'document_pk': self.mine.document.pk,
                            'part_pk': self.theirs.pk}),
            data={'lines': [{'baseline': [[1, 1], [2, 2]]}]},
            content_type='application/json')
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertEqual(Line.objects.filter(document_part=self.theirs).count(), 2)

    def test_lt_bulk_update_is_scoped_to_the_part(self):
        resp = self.call('api:linetranscription-bulk-update',
                         {'lines': [{'pk': self.other_lt.pk,
                                     'content': 'changed'}]}, 'put')
        self.assertEqual(resp.status_code, 404, resp.content)
        self.other_lt.refresh_from_db()
        self.assertEqual(self.other_lt.content, 'other content')

    def test_lt_bulk_delete_is_scoped_to_the_part(self):
        self.call('api:linetranscription-bulk-delete',
                  {'lines': [self.other_lt.pk]})
        self.other_lt.refresh_from_db()
        self.assertEqual(self.other_lt.content, 'other content')

    def test_lt_bulk_create_requires_a_line_of_the_part(self):
        resp = self.call('api:linetranscription-bulk-create',
                         {'lines': [{'line': self.other_line2.pk,
                                     'transcription': self.theirs.document.transcriptions.first().pk,
                                     'content': 'added'}]})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(
            LineTranscription.objects.filter(line=self.other_line2).count(), 0)

    def test_collection_rejects_foreign_parts(self):
        resp = self.client.post(
            reverse('api:virtualcollection-list'),
            data={'name': 'mine', 'items_to_save': [
                {'document_part': self.theirs.pk,
                 'transcription_layer': self.theirs.document.transcriptions.first().pk}]},
            content_type='application/json')
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_collection_accepts_own_parts(self):
        resp = self.client.post(
            reverse('api:virtualcollection-list'),
            data={'name': 'mine', 'items_to_save': [
                {'document_part': self.mine.pk,
                 'transcription_layer': self.mine.document.transcriptions.first().pk}]},
            content_type='application/json')
        self.assertEqual(resp.status_code, 201, resp.content)

    def _another_users_model(self, job):
        model = self.factory.make_model(self.theirs.document, job=job)
        model.public = False
        model.save()
        return model

    @patch('api.serializers.segment')
    def test_segment_requires_a_readable_model(self, mock_segment):
        model = self._another_users_model(OcrModel.MODEL_JOB_SEGMENT)
        resp = self.client.post(
            reverse('api:document-segment', kwargs={'pk': self.mine.document.pk}),
            data={'parts': [self.mine.pk], 'steps': 'both', 'model': model.pk})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(mock_segment.si.called)

    @patch('api.serializers.transcribe')
    def test_transcribe_requires_a_readable_model(self, mock_transcribe):
        model = self._another_users_model(OcrModel.MODEL_JOB_RECOGNIZE)
        resp = self.client.post(
            reverse('api:document-transcribe', kwargs={'pk': self.mine.document.pk}),
            data={'parts': [self.mine.pk], 'model': model.pk,
                  'transcription': self.mine.document.transcriptions.first().pk})
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(mock_transcribe.si.called)

    @patch('core.tasks.forced_align.delay')
    def test_forced_align_requires_a_readable_model(self, mock_align):
        model = self._another_users_model(OcrModel.MODEL_JOB_RECOGNIZE)
        resp = self.client.post(
            reverse('api:document-forced-align',
                    kwargs={'pk': self.mine.document.pk}),
            data={'parts': [self.mine.pk], 'model': model.pk,
                  'transcription': self.mine.document.transcriptions.first().pk},
            content_type='application/json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertFalse(mock_align.called)

    def test_document_tag_must_belong_to_a_writable_project(self):
        tag = DocumentTag.objects.create(project=self.theirs.document.project,
                                         name='other-doctag', color='#fff')
        resp = self.client.patch(
            reverse('api:document-detail', kwargs={'pk': self.mine.document.pk}),
            data={'tags': [tag.pk]}, content_type='application/json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(self.mine.document.tags.count(), 0)

    def test_project_tag_must_belong_to_the_caller(self):
        tag = ProjectTag.objects.create(user=self.other, name='other-projtag',
                                        color='#fff')
        resp = self.client.patch(
            reverse('api:project-detail',
                    kwargs={'pk': self.mine.document.project.pk}),
            data={'tags': [tag.pk]}, content_type='application/json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(self.mine.document.project.tags.count(), 0)


# its own MEDIA_ROOT: the parts created here would otherwise claim the
# `default.png` upload name that imports.tests.test_exporters compares against
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ObjectAuthorisationTestCase(CoreFactoryTestCase):
    """Nested routes authorise the object in the URL on every method.

    The check runs from initial() rather than get_queryset(), so it covers the
    paths that build no queryset, and the PartViewSet actions resolve their
    part through the authorised queryset.

    Same fixture caveat as elsewhere: factory.make_project() get_or_creates on
    the slug, so both sides get an explicitly named project and setUp asserts
    the separation before any test runs.
    """

    def setUp(self):
        super().setUp()
        self.caller = self.factory.make_user()
        my_doc = self.factory.make_document(
            owner=self.caller,
            project=self.factory.make_project(name='caller project',
                                              owner=self.caller))
        self.mine = self.factory.make_part(document=my_doc)

        self.other = self.factory.make_user()
        self.other_doc = self.factory.make_document(
            owner=self.other,
            project=self.factory.make_project(name='other project',
                                              owner=self.other))
        self.theirs = self.factory.make_part(document=self.other_doc)

        self.assertNotIn(self.other_doc, Document.objects.for_user(self.caller))
        self.client.force_login(self.caller)

    def part_action(self, name, document, part, payload=None):
        return self.client.post(
            reverse(name, kwargs={'document_pk': document.pk, 'pk': part.pk}),
            data=payload or {}, content_type='application/json')

    # --- PartViewSet actions ------------------------------------------------

    def test_part_actions_refuse_another_users_document(self):
        for name in ['api:part-move', 'api:part-cancel',
                     'api:part-recalculate-ordering', 'api:part-rotate',
                     'api:part-crop']:
            resp = self.part_action(name, self.other_doc, self.theirs,
                                    {'index': 0, 'angle': 90,
                                     'x1': 0, 'y1': 0, 'x2': 1, 'y2': 1})
            self.assertIn(resp.status_code, (403, 404),
                          '%s allowed a foreign document: %s' % (name, resp.content))

    def test_part_actions_refuse_a_part_from_another_document(self):
        # own document_pk, foreign part_pk
        for name in ['api:part-recalculate-ordering', 'api:part-rotate',
                     'api:part-crop']:
            resp = self.part_action(name, self.mine.document, self.theirs,
                                    {'angle': 90, 'x1': 0, 'y1': 0,
                                     'x2': 1, 'y2': 1})
            self.assertEqual(resp.status_code, 404,
                             '%s allowed a foreign part: %s' % (name, resp.content))

    # --- create paths -------------------------------------------------------

    def test_create_line_refuses_another_users_part(self):
        resp = self.client.post(
            reverse('api:line-list', kwargs={'document_pk': self.other_doc.pk,
                                             'part_pk': self.theirs.pk}),
            data={'document_part': self.theirs.pk, 'baseline': [[1, 1], [2, 2]]},
            content_type='application/json')
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(Line.objects.filter(document_part=self.theirs).count(), 0)

    def test_create_document_metadata_refuses_another_users_document(self):
        resp = self.client.post(
            reverse('api:metadata-list',
                    kwargs={'document_pk': self.other_doc.pk}),
            data={'key': {'name': 'added'}, 'value': 'added'},
            content_type='application/json')
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(self.other_doc.documentmetadata_set.count(), 0)

    def test_create_part_metadata_refuses_another_users_part(self):
        resp = self.client.post(
            reverse('api:partmetadata-list',
                    kwargs={'document_pk': self.other_doc.pk,
                            'part_pk': self.theirs.pk}),
            data={'key': {'name': 'added'}, 'value': 'added'},
            content_type='application/json')
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(self.theirs.metadata.count(), 0)

    # --- part metadata read -------------------------------------------------

    def test_part_metadata_is_scoped_to_the_document(self):
        self.factory.make_part_metadata(self.theirs)
        resp = self.client.get(
            reverse('api:partmetadata-list',
                    kwargs={'document_pk': self.mine.document.pk,
                            'part_pk': self.theirs.pk}))
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertNotIn(b'testmdvalue', resp.content)

    # --- task groups --------------------------------------------------------

    def test_task_groups_are_scoped_to_the_document(self):
        TaskGroup.objects.create(document=self.other_doc, created_by=self.other,
                                 task='core.tasks.segment')
        resp = self.client.get(
            reverse('api:task-group-list',
                    kwargs={'document_pk': self.other_doc.pk}))
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertNotIn(self.other.username.encode(), resp.content)

    def test_owner_still_sees_their_own_task_groups(self):
        TaskGroup.objects.create(document=self.mine.document,
                                 created_by=self.caller,
                                 task='core.tasks.segment')
        resp = self.client.get(
            reverse('api:task-group-list',
                    kwargs={'document_pk': self.mine.document.pk}))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['count'], 1)

    # --- the neighbouring viewsets scope by owner; assert that holds ---------

    def test_owner_scoped_viewsets_hide_other_users_objects(self):
        collection = VirtualCollection.objects.create(name='theirs',
                                                      owner=self.other)
        witness = TextualWitness.objects.create(name='theirs', owner=self.other)
        report = TaskReport.objects.create(user=self.other,
                                           document=self.other_doc,
                                           label='theirs')
        for name, pk in [('api:virtualcollection-detail', collection.pk),
                         ('api:textualwitness-detail', witness.pk),
                         ('api:taskreport-detail', report.pk)]:
            resp = self.client.get(reverse(name, kwargs={'pk': pk}))
            self.assertEqual(resp.status_code, 404,
                             '%s exposed another user object: %s'
                             % (name, resp.content))

    # --- document tags ------------------------------------------------------

    def test_document_tag_create_requires_the_project(self):
        resp = self.client.post(
            reverse('api:document-tag-list',
                    kwargs={'project_pk': self.other_doc.project.pk}),
            data={'name': 'added', 'color': '#ffffff'})
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertFalse(DocumentTag.objects.filter(
            project=self.other_doc.project, name='added').exists())

    def test_document_tag_list_requires_the_project(self):
        DocumentTag.objects.create(project=self.other_doc.project,
                                   name='their tag', color='#fff')
        resp = self.client.get(
            reverse('api:document-tag-list',
                    kwargs={'project_pk': self.other_doc.project.pk}))
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertNotIn(b'their tag', resp.content)

    def test_owner_still_manages_their_own_tags(self):
        uri = reverse('api:document-tag-list',
                      kwargs={'project_pk': self.mine.document.project.pk})
        resp = self.client.post(uri, data={'name': 'mine', 'color': '#ffffff'})
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(self.client.get(uri).status_code, 200)
