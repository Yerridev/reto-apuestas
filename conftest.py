import pytest
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
