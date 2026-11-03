from django.contrib.auth.models import Permission
from django.urls import reverse

from core.models import InstanceSettings
from core.tests.factory import CoreFactoryTestCase
from users.models import User


def can_train_perm():
    return Permission.objects.get(content_type__app_label='core', codename='can_train')


class TrainingViewsPermissionTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.factory.make_user()
        self.doc = self.factory.make_document(owner=self.user)

    def test_training_page_forbidden_without_permission(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('training')).status_code, 403)

    def test_training_page_allowed_with_permission(self):
        self.user.user_permissions.add(can_train_perm())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('training')).status_code, 200)

    def test_legacy_process_train_forbidden_without_permission(self):
        self.client.force_login(self.user)
        uri = reverse('document-parts-process', kwargs={'pk': self.doc.pk})
        for task in ('train', 'segtrain'):
            resp = self.client.post(uri, data={'task': task})
            self.assertEqual(resp.status_code, 403, task)


class DefaultUserPermissionsTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.settings_obj = InstanceSettings.get_solo()

    def test_no_default_permissions(self):
        user = self.factory.make_user()
        self.assertFalse(user.user_permissions.exists())

    def test_new_user_gets_default_permissions(self):
        self.settings_obj.default_user_permissions.add(can_train_perm())
        user = self.factory.make_user()
        self.assertTrue(User.objects.get(pk=user.pk).has_perm('core.can_train'))

    def test_existing_user_save_does_not_grant(self):
        user = self.factory.make_user()
        self.settings_obj.default_user_permissions.add(can_train_perm())
        user.first_name = 'changed'
        user.save()
        self.assertFalse(user.user_permissions.exists())


class InstanceSettingsAdminApplyTestCase(CoreFactoryTestCase):
    def setUp(self):
        super().setUp()
        self.admin = self.factory.make_user(is_staff=True, is_superuser=True)
        # created before any default is configured
        self.active = self.factory.make_user()
        self.inactive = self.factory.make_user(is_active=False)
        self.url = reverse('admin:core_instancesettings_change')

    def _post(self, perm):
        settings_obj = InstanceSettings.get_solo()
        return self.client.post(self.url, data={
            'page_batch_segmentation': settings_obj.page_batch_segmentation,
            'page_batch_recognition': settings_obj.page_batch_recognition,
            'default_user_permissions': [perm.pk],
            '_apply_default_perms': '1',
        })

    def test_apply_to_existing_active_users(self):
        perm = can_train_perm()
        self.client.force_login(self.admin)
        resp = self._post(perm)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.active.user_permissions.filter(pk=perm.pk).exists())
        self.assertFalse(self.inactive.user_permissions.filter(pk=perm.pk).exists())
        # idempotent
        resp = self._post(perm)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.active.user_permissions.filter(pk=perm.pk).count(), 1)

    def test_plain_save_does_not_apply(self):
        perm = can_train_perm()
        self.client.force_login(self.admin)
        settings_obj = InstanceSettings.get_solo()
        self.client.post(self.url, data={
            'page_batch_segmentation': settings_obj.page_batch_segmentation,
            'page_batch_recognition': settings_obj.page_batch_recognition,
            'default_user_permissions': [perm.pk],
            '_save': '1',
        })
        self.assertTrue(InstanceSettings.get_solo().default_user_permissions.filter(pk=perm.pk).exists())
        self.assertFalse(self.active.user_permissions.exists())
