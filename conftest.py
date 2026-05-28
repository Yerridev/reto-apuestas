import pytest
from channels.layers import get_channel_layer
from django.core.cache import cache
from rest_framework.settings import api_settings


@pytest.fixture(autouse=True)
def _disable_throttling(settings):
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'anon': '10000/minute',
        'user': '10000/minute',
        'auth_register': '10000/hour',
    }
    api_settings.reload()
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _in_memory_channel_layer(settings):
    """
    Reemplaza RedisChannelLayer por InMemoryChannelLayer en todos los tests.
    Evita depóndencia de Redis durante el test suite.
    """
    settings.CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }
    yield
