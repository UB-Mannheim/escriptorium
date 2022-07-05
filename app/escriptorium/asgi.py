"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "escriptorium.settings")
django.setup()
asgi_app = get_asgi_application()

# needs to be imported AFTER django.setup
import users.routing  # noqa: E402

application = ProtocolTypeRouter({
    'http': asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                users.routing.websocket_urlpatterns
            )
        )
    )
})
