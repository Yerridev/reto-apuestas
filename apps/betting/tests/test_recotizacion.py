"""
Tests para la política de re-cotización (Paso B).

Cubre:
- Sin odds_expected: apuesta acepta sin verificar cuota
- odds_expected coincide con actuales: apuesta aceptada normal
- odds_expected difiere de actuales: 409 con odds_current en la respuesta
- 409 no debita el wallet ni crea la apuesta
- Después del 409 el usuario puede reenviar con odds_current y se acepta
"""
import uuid
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.betting.models import Bet, Event, Market, Selection
from apps.users.choices import AccountStatus
from apps.wallet.services import deposit, get_balance, get_or_create_wallet
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def usuario(db):
    u = User.objects.create_user(
        email='recot@fairbet.pe', password='Test1234!',
        dni='123456781', first_name='R', last_name='C',
        birth_date='1995-01-01', account_status=AccountStatus.VERIFICADO,
    )
    get_or_create_wallet(u)
    deposit(u, Decimal('500.0000'))
    return u


@pytest.fixture
def selection(db):
    event = Event.objects.create(
        name='Partido recot', sport='futbol',
        status=Event.Status.EN_VIVO,
        starts_at=timezone.now() - timezone.timedelta(minutes=5),
    )
    market = Market.objects.create(event=event, name='Resultado', market_type=Market.Type.UNO_X_DOS)
    return Selection.objects.create(market=market, name='local', odds=Decimal('2.5000'))


def auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_sin_odds_expected_acepta_sin_verificar(usuario, selection):
    """Si no se envía odds_expected, la apuesta se acepta normalmente."""
    response = auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '50.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert response.status_code == 201
    assert Bet.objects.count() == 1


@pytest.mark.django_db
def test_odds_expected_correctas_acepta(usuario, selection):
    """odds_expected igual a las actuales → apuesta aceptada."""
    response = auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '50.0000',
        'odds_expected': '2.5000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert response.status_code == 201
    assert Bet.objects.count() == 1


@pytest.mark.django_db
def test_odds_changed_retorna_409(usuario, selection):
    """odds_expected diferente a las actuales → 409 con odds_current."""
    response = auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '50.0000',
        'odds_expected': '2.8000',  # usuario vio 2.80, ahora son 2.50
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert response.status_code == 409
    assert response.data['odds_current'] == '2.5000'
    assert response.data['odds_expected'] == '2.8000'
    assert 'cuotas han cambiado' in response.data['detail'].lower()


@pytest.mark.django_db
def test_409_no_debita_wallet(usuario, selection):
    """El 409 no debe tocar el saldo del usuario."""
    balance_before = get_balance(usuario)

    auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '50.0000',
        'odds_expected': '9.9999',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert get_balance(usuario) == balance_before
    assert Bet.objects.count() == 0


@pytest.mark.django_db
def test_reconfirmar_con_odds_actuales_acepta(usuario, selection):
    """Tras un 409, el usuario reenvía con odds_current y se acepta."""
    key = str(uuid.uuid4())

    # Primer intento con odds viejas
    r1 = auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '50.0000',
        'odds_expected': '3.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=key)
    assert r1.status_code == 409

    # Segundo intento con odds actuales (nueva key por ser apuesta distinta)
    r2 = auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '50.0000',
        'odds_expected': r1.data['odds_current'],
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert r2.status_code == 201
    assert Bet.objects.count() == 1
