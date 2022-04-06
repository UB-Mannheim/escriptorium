from django.contrib.auth import get_user_model
from django.test import TestCase

from versioning.models import NoChangeException, TestModel

User = get_user_model()


class VersioningTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user_1', password='test', email='1@test.com')
        self.user2 = User.objects.create_user(
            username='user_2', password='test', email='2@test.com')
        self.instance = TestModel.objects.create(
            content='test',
            version_author=self.user1.username)

    def test_nominal(self):
        v1_revision = self.instance.revision
        self.assertEqual(len(self.instance.history), 0)
        self.instance.new_version()
        self.instance.author = self.user2.username
        self.instance.content = 'test v2'
        self.instance.save()
        self.assertEqual(len(self.instance.history), 1)
        self.assertNotEqual(self.instance.revision, v1_revision)
        v2_revision = self.instance.revision

        self.instance.new_version()
        self.instance.content = 'test v3'
        v3_revision = self.instance.revision

        self.instance.new_version()
        self.instance.content = 'test v4'
        v4_revision = self.instance.revision

        self.assertEqual(len(self.instance.history), 3)

        self.instance.revert(v1_revision.hex)
        self.assertEqual(len(self.instance.history), 3)
        self.assertEqual(self.instance.revision, v1_revision)
        self.assertEqual(self.instance.history[0].revision, v4_revision)
        self.assertEqual(self.instance.history[1].revision, v3_revision)
        self.assertEqual(self.instance.history[2].revision, v2_revision)

        self.instance.revert(v3_revision.hex)
        self.assertEqual(len(self.instance.history), 3)
        self.assertEqual(self.instance.revision, v3_revision)
        self.assertEqual(self.instance.history[0].revision, v1_revision)
        self.assertEqual(self.instance.history[1].revision, v4_revision)
        self.assertEqual(self.instance.history[2].revision, v2_revision)

    def test_save_version(self):
        self.instance.new_version()
        with self.assertRaises(RuntimeError):
            self.instance.history[0].save()

        with self.assertRaises(RuntimeError):
            self.instance.history[0].delete()

    def test_ignored_field(self):
        self.instance.new_version()
        self.assertNotIn('ignored', self.instance.versions[0]['data'])

    def test_no_change(self):
        self.instance.new_version()
        with self.assertRaises(NoChangeException):
            self.instance.new_version()

    def test_user_change(self):
        self.instance.new_version()
        # just check NoChangeException is not raised
        self.instance.new_version(author=self.user2.username)

    def test_delete(self):
        self.instance.new_version()
        self.assertEqual(len(self.instance.history), 1)
        self.instance.delete_revision(self.instance.versions[0]['revision'])
        self.assertEqual(len(self.instance.history), 0)

    def test_flush(self):
        self.instance.new_version()
        self.instance.new_version(content='test replace')
        self.assertEqual(len(self.instance.history), 2)
        self.instance.flush_history()
        self.assertEqual(len(self.instance.history), 0)

    def test_max_history(self):
        self.instance.new_version(content='test 1')
        self.instance.new_version(content='test 2')
        self.instance.new_version(content='test 3')
        self.instance.new_version(content='test 4')
        self.instance.new_version(content='test 5')
        self.assertEqual(len(self.instance.history), 5)
        self.instance.new_version(content='test 6')
        self.assertEqual(len(self.instance.history), 5)
        self.assertEqual(self.instance.history[0].content, 'test 6')
        self.assertEqual(self.instance.history[4].content, 'test 2')
