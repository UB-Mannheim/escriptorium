from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from versioning.models import TestModel

User = get_user_model()


class VersioningTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user_1', password='test', email='1@test.com')
        self.user2 = User.objects.create_user(
            username='user_2', password='test', email='2@test.com')
    
    def test_nominal(self):
        v1 = TestModel.objects.create(identity=1, content='test', author=self.user1.username)
        self.assertEqual(TestModel.objects.count(), 1)
        self.assertEqual(v1.current_version, v1)
        self.assertEqual(v1.is_current, True)
        
        v2 = v1.make_new_version()
        v2.content = 'test v2'
        v2.author = self.user2.username
        v2.save()

        v3 = v2.make_new_version()
        v3.content = 'test v3'
        v3.save()

        v4 = v1.make_new_version()
        v4.content = 'test v4'
        v4.save()
        
        self.assertEqual(TestModel.objects.count(), 1)
        self.assertEqual(v4.history().count(), 4)
        self.assertEqual(v1.content, 'test')
        self.assertEqual(v2.content, 'test v2')
        self.assertEqual(v3.content, 'test v3')
        self.assertEqual(v4.content, 'test v4')
        self.assertEqual(v1.current_version, v4)

        v4.revert_to(v1)
        self.assertEqual(TestModel.objects.count(), 1)  # still 1 because v1 is hidden
        self.assertEqual(v4.history().count(), 4)
        self.assertEqual(v4.current_version, v1)

        v1.revert_to_revision(v2.revision)
        self.assertEqual(v1.current_version, v2)

        v3.revert_to(v1)
        self.assertEqual(v3.current_version, v1)
