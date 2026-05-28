import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase
from django.utils import timezone

from apps.betting.models import Event, Market, Selection

User = get_user_model()


@pytest.mark.django_db
class TestOddsEndpoint:
    """Tests para endpoint REST de cuotas"""

    def test_get_event_odds(self):
        """Test GET /api/events/{id}/odds/"""
        event = Event.objects.create(
            name='Test Event',
            sport='futbol',
            starts_at=timezone.now() + timezone.timedelta(days=1),
        )
        market = Market.objects.create(
            event=event,
            name='Resultado',
            market_type=Market.Type.UNO_X_DOS,
        )
        sel1 = Selection.objects.create(market=market, name='local', odds=Decimal('2.5000'))
        sel2 = Selection.objects.create(market=market, name='empate', odds=Decimal('3.2000'))

        client = Client()
        response = client.get(f'/api/events/{event.id}/odds/')

        assert response.status_code == 200
        data = response.json()
        assert data['event_id'] == event.id
        assert data['event_name'] == 'Test Event'
        assert 'markets' in data
        assert 'timestamp' in data

    def test_event_odds_not_found(self):
        """Test 404 cuando evento no existe"""
        client = Client()
        response = client.get('/api/events/99999/odds/')
        assert response.status_code == 404

