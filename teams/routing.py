from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/team/(?P<channel_id>\d+)/$', consumers.TeamChannelConsumer.as_asgi()),
]
