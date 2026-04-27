"""
ASGI config for TeamSync project.
Handles both HTTP and WebSocket connections.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teamsync.settings')

django_asgi_app = get_asgi_application()

# Import after django setup
from chat.routing import websocket_urlpatterns as chat_ws
from teams.routing import websocket_urlpatterns as teams_ws

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat_ws + teams_ws
            )
        )
    ),
})
