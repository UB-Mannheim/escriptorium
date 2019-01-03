from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from versioning.models import TestModel, NoChangeException

User = get_user_model()


class VersioningTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user_1', password='test', email='1@test.com')
        self.user2 = User.objects.create_user(
            username='user_2', password='test', email='2@test.com')
    
    def test_nominal(self):
        test = TestModel.objects.create(content='test',
                                      version_author=self.user1.username)
        v1_revision = test.revision
        self.assertEqual(len(test.history), 0)
        test.new_version()
        test.author = self.user2.username
        test.content = 'test v2'
        test.save()
        self.assertEqual(len(test.history), 1)
        self.assertNotEqual(test.revision, v1_revision)
        v2_revision = test.revision
        
        test.new_version()
        test.content = 'test v3'
        v3_revision = test.revision
        
        test.new_version()
        test.content = 'test v4'
        v4_revision = test.revision
        
        self.assertEqual(len(test.history), 3)
        
        test.revert(v1_revision.hex)
        self.assertEqual(len(test.history), 3)
        self.assertEqual(test.revision, v1_revision)
        self.assertEqual(test.history[0].revision, v4_revision)
        self.assertEqual(test.history[1].revision, v3_revision)
        self.assertEqual(test.history[2].revision, v2_revision)
        
        test.revert(v3_revision.hex)
        self.assertEqual(len(test.history), 3)
        self.assertEqual(test.revision, v3_revision)
        self.assertEqual(test.history[0].revision, v1_revision)
        self.assertEqual(test.history[1].revision, v4_revision)
        self.assertEqual(test.history[2].revision, v2_revision)
    
    def test_save_version(self):
        test = TestModel.objects.create(content='test',
                                        version_author=self.user1.username)
        test.new_version()
        with self.assertRaises(RuntimeError):
            test.history[0].save()

        with self.assertRaises(RuntimeError):
            test.history[0].delete()

    def test_ignored_field(self):
        test = TestModel.objects.create(content='test',
                                        version_author=self.user1.username)
        test.new_version()
        self.assertNotIn('ignored', test.versions)


    def test_no_change(self):
        test = TestModel.objects.create(content='test',
                                        version_author=self.user1.username)
        test.new_version()
        with self.assertRaises(NoChangeException):
            test.new_version()
