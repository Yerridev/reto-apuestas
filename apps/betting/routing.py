from django.urls import path

from apps.betting.consumers import OddsConsumer

websocket_urlpatterns = [
    path('ws/odds/event/<int:event_id>/', OddsConsumer.as_asgi(), name='ws-odds'),
]
