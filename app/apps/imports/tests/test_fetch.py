from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from imports import fetch


def resolves_to(*addresses, **per_host):
    """Stand in for getaddrinfo so the tests don't depend on real DNS.

    Positional addresses answer for any host; per_host overrides by name, with
    dots written as underscores.
    """
    def fake(host, port, **kwargs):
        answers = per_host.get(str(host).replace('.', '_'), addresses)
        return [(2, 1, 6, '', (address, port or 80)) for address in answers]
    return fake


class FakeResponse:
    def __init__(self, status_code=200, location=None):
        self.status_code = status_code
        self.headers = {'Location': location} if location else {}
        self.is_redirect = location is not None


@override_settings(IMPORT_ALLOWED_DOMAINS=['*'],
                   IMPORT_ALLOW_PRIVATE_ADDRESSES=False)
class ValidateUriTestCase(SimpleTestCase):
    def assertRefused(self, uri):
        with self.assertRaises(fetch.UnsafeUriError):
            fetch.validate_uri(uri)

    def test_non_http_schemes_are_refused(self):
        for uri in ['file:///tmp/x', 'ftp://example.com/x',
                    'gopher://example.com/', 'data:text/plain,x']:
            self.assertRefused(uri)

    @patch('socket.getaddrinfo', resolves_to('127.0.0.1'))
    def test_loopback_is_refused(self):
        self.assertRefused('http://localhost.example.com/')

    @patch('socket.getaddrinfo', resolves_to('169.254.169.254'))
    def test_link_local_address_is_refused(self):
        self.assertRefused('http://link-local.example.com/')

    @patch('socket.getaddrinfo', resolves_to('10.0.0.5'))
    def test_private_range_is_refused(self):
        self.assertRefused('http://internal.example.com/')

    @patch('socket.getaddrinfo', resolves_to('::1'))
    def test_ipv6_loopback_is_refused(self):
        self.assertRefused('http://v6.example.com/')

    @patch('socket.getaddrinfo', resolves_to('93.184.216.34', '10.0.0.5'))
    def test_refused_when_any_answer_is_private(self):
        # a name that resolves to both a public and a private address must not
        # get through on the strength of the public one
        self.assertRefused('http://split.example.com/')

    @patch('socket.getaddrinfo', resolves_to('93.184.216.34'))
    def test_public_address_is_allowed(self):
        fetch.validate_uri('http://example.com/manifest.json')

    @patch('socket.getaddrinfo', resolves_to('169.254.169.254'))
    @override_settings(IMPORT_ALLOW_PRIVATE_ADDRESSES=True)
    def test_escape_hatch_allows_private_addresses(self):
        fetch.validate_uri('http://link-local.example.com/')

    @patch('socket.getaddrinfo', resolves_to('93.184.216.34'))
    @override_settings(IMPORT_ALLOWED_DOMAINS=['gallica.bnf.fr'])
    def test_domain_allowlist_is_enforced(self):
        self.assertRefused('http://example.com/')
        fetch.validate_uri('http://gallica.bnf.fr/manifest.json')


@override_settings(IMPORT_ALLOWED_DOMAINS=['*'],
                   IMPORT_ALLOW_PRIVATE_ADDRESSES=False)
class FetchGetTestCase(SimpleTestCase):
    @patch('socket.getaddrinfo', resolves_to('93.184.216.34'))
    @patch('requests.get')
    def test_public_get_is_performed(self, session_get):
        session_get.return_value = FakeResponse(200)
        self.assertEqual(fetch.get('http://example.com/').status_code, 200)

    @patch('socket.getaddrinfo',
           resolves_to('93.184.216.34',
                       **{'169_254_169_254': ('169.254.169.254',)}))
    @patch('requests.get')
    def test_redirect_to_a_private_address_is_refused(self, session_get):
        # the uri the user gives is public; it 302s to a link-local address
        session_get.return_value = FakeResponse(
            302, location='http://169.254.169.254/')

        with self.assertRaises(fetch.UnsafeUriError):
            fetch.get('http://example.com/')

        # the first hop was fetched, the redirect target never was
        self.assertEqual(session_get.call_count, 1)

    @patch('socket.getaddrinfo', resolves_to('93.184.216.34'))
    @patch('requests.get')
    def test_redirect_loop_is_bounded(self, session_get):
        session_get.return_value = FakeResponse(
            302, location='http://example.com/next')

        with self.assertRaises(fetch.UnsafeUriError):
            fetch.get('http://example.com/')

        self.assertEqual(session_get.call_count, fetch.MAX_REDIRECTS + 1)

    @patch('socket.getaddrinfo', resolves_to('93.184.216.34'))
    @patch('requests.get')
    def test_a_timeout_is_always_passed(self, session_get):
        session_get.return_value = FakeResponse(200)
        fetch.get('http://example.com/')

        self.assertEqual(session_get.call_args.kwargs['timeout'],
                         fetch.DEFAULT_TIMEOUT)
        self.assertFalse(session_get.call_args.kwargs['allow_redirects'])
