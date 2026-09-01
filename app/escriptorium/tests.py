import asyncio
import io
import json
from unittest.mock import patch

from django.core.handlers.asgi import ASGIHandler, ASGIRequest
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import clear_script_prefix, reverse

from escriptorium.middleware import ForceScriptNamePathMiddleware


class ASGITestMixin:
    # mimic daphne: no root_path in the scope, nginx strips the prefix
    def asgi_scope(self, path, query_string=b'', sessionid=None):
        headers = [(b'host', b'testserver')]
        if sessionid:
            headers.append((b'cookie', ('sessionid=' + sessionid).encode()))
        return {
            'type': 'http',
            'asgi': {'version': '3.0'},
            'http_version': '1.1',
            'method': 'GET',
            'scheme': 'http',
            'path': path,
            'query_string': query_string,
            'root_path': '',
            'headers': headers,
            'server': ('testserver', 80),
            'client': ('1.2.3.4', 5678),
        }

    def asgi_get(self, path, query_string=b'', sessionid=None):
        # the ASGI handler runs views on a worker thread with its own
        # database connection, so the data must be committed: use
        # TransactionTestCase for tests that need database objects
        scope = self.asgi_scope(path, query_string, sessionid)
        messages = []

        async def run():
            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}

            async def send(message):
                messages.append(message)

            try:
                await ASGIHandler()(scope, receive, send)
            finally:
                clear_script_prefix()

        asyncio.run(run())
        return messages

    def asgi_request(self, path='/api/users/', query_string=b''):
        scope = self.asgi_scope(path, query_string)
        return ASGIRequest(scope, io.BytesIO())


class ForceScriptNamePathMiddlewareTestCase(ASGITestMixin, TestCase):
    @override_settings(FORCE_SCRIPT_NAME='/escriptorium')
    def test_asgi_request_path_gets_prefix(self):
        request = self.asgi_request()
        self.assertEqual(request.path, '/api/users/')
        ForceScriptNamePathMiddleware(lambda r: None)(request)
        self.assertEqual(request.path, '/escriptorium/api/users/')
        self.assertEqual(
            request.build_absolute_uri(),
            'http://testserver/escriptorium/api/users/')

    def test_noop_without_force_script_name(self):
        request = self.asgi_request()
        ForceScriptNamePathMiddleware(lambda r: None)(request)
        self.assertEqual(request.path, '/api/users/')

    @override_settings(FORCE_SCRIPT_NAME='/escriptorium')
    def test_noop_when_path_already_prefixed(self):
        request = self.asgi_request()
        request.path = '/escriptorium/api/users/'
        ForceScriptNamePathMiddleware(lambda r: None)(request)
        self.assertEqual(request.path, '/escriptorium/api/users/')


class ASGISubpathTestCase(ASGITestMixin, TransactionTestCase):
    @override_settings(FORCE_SCRIPT_NAME='/escriptorium')
    def test_pagination_next_link_contains_script_name(self):
        from core.models import OcrModel
        from core.tests.factory import CoreFactory

        factory = CoreFactory()
        user = factory.make_user()
        for i in range(2):
            OcrModel.objects.create(name='model-%d' % i, owner=user,
                                    job=OcrModel.MODEL_JOB_SEGMENT,
                                    file_size=0, public=True)
        self.client.force_login(user)
        sessionid = self.client.cookies['sessionid'].value
        messages = self.asgi_get('/api/models/', b'paginate_by=1', sessionid)
        body = b''.join(m.get('body', b'') for m in messages
                        if m['type'] == 'http.response.body')
        data = json.loads(body)
        self.assertIn('/escriptorium/api/models/', data['next'])


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
