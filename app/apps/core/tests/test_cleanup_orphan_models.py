import os

from django.conf import settings
from django.core.management import call_command

from core.models import OcrModel
from core.tests.factory import CoreFactoryTestCase


class CleanupOrphanModelsTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.models_dir = os.path.join(settings.MEDIA_ROOT, "models")

    def make_model_with_file(self, name, directory, filename):
        path = os.path.join(self.models_dir, directory)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, filename), "wb") as f:
            f.write(b"test")
        return OcrModel.objects.create(
            name=name, job=OcrModel.MODEL_JOB_RECOGNIZE,
            file="models/%s/%s" % (directory, filename), file_size=4
        )

    def make_fixture(self):
        self.make_model_with_file("kept", "hash0001", "kept.mlmodel")
        self.fileless = OcrModel.objects.create(name="fileless", job=OcrModel.MODEL_JOB_SEGMENT, file_size=0)
        os.makedirs(os.path.join(self.models_dir, "orphan01"), exist_ok=True)
        with open(os.path.join(self.models_dir, "orphan01", "orphan.mlmodel"), "wb") as f:
            f.write(b"test")

    def test_dry_run_changes_nothing(self):
        self.make_fixture()
        call_command("cleanup_orphan_models", dry_run=True)
        self.assertTrue(OcrModel.objects.filter(pk=self.fileless.pk).exists())
        self.assertTrue(os.path.isdir(os.path.join(self.models_dir, "orphan01")))
        self.assertTrue(OcrModel.objects.filter(file="models/hash0001/kept.mlmodel").exists())

    def test_cleanup_removes_fileless_rows_and_orphan_directories(self):
        self.make_fixture()
        call_command("cleanup_orphan_models")
        self.assertFalse(OcrModel.objects.filter(pk=self.fileless.pk).exists())
        self.assertFalse(os.path.exists(os.path.join(self.models_dir, "orphan01")))
        self.assertTrue(OcrModel.objects.filter(file="models/hash0001/kept.mlmodel").exists())
        self.assertTrue(os.path.isdir(os.path.join(self.models_dir, "hash0001")))

    def test_training_model_without_file_is_kept(self):
        self.make_fixture()
        self.fileless.training = True
        self.fileless.save()
        call_command("cleanup_orphan_models")
        self.assertTrue(OcrModel.objects.filter(pk=self.fileless.pk).exists())

    def test_model_with_missing_file_is_reported_but_kept(self):
        model = OcrModel.objects.create(
            name="dangling", job=OcrModel.MODEL_JOB_RECOGNIZE,
            file="models/hash9999/dangling.mlmodel", file_size=4
        )
        call_command("cleanup_orphan_models")
        self.assertTrue(OcrModel.objects.filter(pk=model.pk).exists())
