from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class APIAuthURLTestCase(TestCase):
    def test_browsable_api_login_page(self):
        # rest_framework.urls is included at the top level so that the
        # 'rest_framework' namespace resolves from DRF's own templates
        # (namespaces nested inside an app_name-ed include do not)
        self.assertEqual(reverse('rest_framework:login'),
                         '/api/api-auth/login/')
        response = self.client.get('/api/api-auth/login/')
        self.assertEqual(response.status_code, 200)


class HealthTestCase(TestCase):
    def test_liveness(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_liveness_needs_no_database(self):
        with self.assertNumQueries(0):
            self.client.get(reverse('health'))

    def test_liveness_is_not_cached(self):
        response = self.client.get(reverse('health'))
        self.assertIn('no-cache', response['Cache-Control'])

    def test_readiness(self):
        response = self.client.get(reverse('health-ready'))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content['status'], 'ok')
        # the test settings swap in a dummy cache and an eager celery, but
        # every check should still report on itself
        self.assertEqual(set(content['checks']),
                         {'database', 'cache', 'celery_broker'})
        self.assertEqual(set(content['checks'].values()), {'ok'})

    def test_readiness_reports_a_dead_dependency(self):
        with patch('escriptorium.views.check_database',
                   side_effect=Exception('connection refused')):
            response = self.client.get(reverse('health-ready'))

        self.assertEqual(response.status_code, 503)
        content = response.json()
        self.assertEqual(content['status'], 'error')
        self.assertEqual(content['checks']['database'], 'connection refused')
        # the other checks still run and are still reported
        self.assertEqual(content['checks']['cache'], 'ok')

    def test_readiness_truncates_long_errors(self):
        with patch('escriptorium.views.check_database',
                   side_effect=Exception('x' * 500)):
            response = self.client.get(reverse('health-ready'))

        self.assertEqual(len(response.json()['checks']['database']), 200)
