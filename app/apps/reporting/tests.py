from django.test import TestCase
from django.urls import reverse

from core.tests.factory import CoreFactory


class DownloadsPageTestCase(TestCase):
    def setUp(self):
        self.factory = CoreFactory()
        self.user = self.factory.make_user()

    def test_downloads_page_renders(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('downloads'))
        self.assertEqual(resp.status_code, 200)
