"""Outbound HTTP for imports.

Import URIs are supplied by users - directly for IIIF and METS, indirectly for
everything a METS document points at - so every fetch here goes to a
user-supplied target. Going through this module keeps the target checks in one
place and applies them again on each redirect hop, since only the first URI is
the one the user typed.
"""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.utils.translation import gettext as _

DEFAULT_TIMEOUT = 30
MAX_REDIRECTS = 5
REDIRECT_STATUSES = (301, 302, 303, 307, 308)


class UnsafeUriError(Exception):
    """The target is refused before any request is made."""


def domain_allowed(uri):
    domain = urlparse(uri).netloc
    return ('*' in settings.IMPORT_ALLOWED_DOMAINS
            or domain in settings.IMPORT_ALLOWED_DOMAINS)


def validate_uri(uri, check_domain=True):
    parsed = urlparse(uri)

    if parsed.scheme not in ('http', 'https'):
        raise UnsafeUriError(_("Only http and https addresses can be imported."))

    if check_domain and not domain_allowed(uri):
        raise UnsafeUriError(
            _("You're not allowed to import files from this domain, "
              "please contact your instance administrator."))

    host = parsed.hostname
    if not host:
        raise UnsafeUriError(_("The address is missing a host."))

    if getattr(settings, 'IMPORT_ALLOW_PRIVATE_ADDRESSES', False):
        # deployments whose IIIF or METS source sits on the internal network
        return

    try:
        infos = socket.getaddrinfo(host, parsed.port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, ValueError):
        raise UnsafeUriError(
            _("The document is unreachable, unreadable or the host timed out."))

    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        # is_global excludes loopback, link-local, the private ranges and
        # the reserved blocks
        if not address.is_global:
            raise UnsafeUriError(
                _("Importing from a private or local network address is not "
                  "allowed."))


def get(uri, check_domain=True, timeout=DEFAULT_TIMEOUT, **kwargs):
    """requests.get, with the target validated before every hop.

    Note this validates the name, then resolves it again inside requests, so a
    host whose DNS answer changes between the two still gets through. Closing
    that needs the connection pinned to the address that was checked.
    """
    kwargs.pop('allow_redirects', None)

    for _hop in range(MAX_REDIRECTS + 1):
        validate_uri(uri, check_domain=check_domain)
        response = requests.get(uri, timeout=timeout,
                                allow_redirects=False, **kwargs)

        # keyed off the status rather than response.is_redirect so that a
        # stubbed response without that attribute is not read as a redirect
        location = response.headers.get('Location')
        if response.status_code in REDIRECT_STATUSES and isinstance(location, str):
            uri = urljoin(uri, location)
            continue

        return response

    raise UnsafeUriError(_("Too many redirects while fetching the document."))
