import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.betting.choices import BetStatus
from apps.betting.models import Bet, Event, Market, Selection
from apps.users.choices import AccountStatus
from apps.wallet.services import deposit, get_balance, get_or_create_wallet

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


def crear_usuario(email, dni, status=AccountStatus.VERIFICADO, is_staff=False):
    return User.objects.create_user(
        email=email,
        password='Test1234!',
        dni=dni,
        first_name='Bet',
        last_name='User',
        birth_date='1995-01-01',
        account_status=status,
        is_staff=is_staff,
    )


@pytest.fixture
def usuario_verificado(db):
    return crear_usuario('bet-ok@fairbet.pe', '102687744')


@pytest.fixture
def usuario_autoexcluido(db):
    return crear_usuario(
        'bet-autoexcluido@fairbet.pe',
        '102687752',
        status=AccountStatus.AUTOEXCLUIDO,
    )


@pytest.fixture
def admin_user(db):
    return crear_usuario('admin-betting@fairbet.pe', '102687760', is_staff=True)


@pytest.fixture
def mercado_abierto(db):
    event = Event.objects.create(
        name='Alianza Lima vs Sporting Cristal',
        sport='futbol',
        starts_at=timezone.now() + timezone.timedelta(days=1),
    )
    market = Market.objects.create(event=event, name='Resultado final', market_type=Market.Type.UNO_X_DOS)
    Selection.objects.create(market=market, name='local', odds=Decimal('2.1000'))
    Selection.objects.create(market=market, name='empate', odds=Decimal('3.4000'))
    Selection.objects.create(market=market, name='visitante', odds=Decimal('3.8000'))
    return market


@pytest.fixture
def selection_local(mercado_abierto):
    return mercado_abierto.selections.get(name='local')


def autenticar(client, user):
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_crear_apuesta_valida_reserva_saldo_y_queda_accepted(client, usuario_verificado, selection_local):
    get_or_create_wallet(usuario_verificado)
    deposit(usuario_verificado, Decimal('100.0000'))
    url = reverse('bet-create')

    response = autenticar(client, usuario_verificado).post(
        url,
        {'selection': selection_local.id, 'stake': '25.0000'},
        format='json',
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )

    assert response.status_code == 201
    assert response.data['status'] == BetStatus.ACCEPTED
    assert response.data['odds'] == '2.1000'
    assert Bet.objects.count() == 1
    assert get_balance(usuario_verificado) == Decimal('75.0000')


@pytest.mark.django_db
def test_crear_apuesta_rechaza_usuario_autoexcluido(client, usuario_autoexcluido, selection_local):
    get_or_create_wallet(usuario_autoexcluido)
    deposit(usuario_autoexcluido, Decimal('100.0000'))

    response = autenticar(client, usuario_autoexcluido).post(
        reverse('bet-create'),
        {'selection': selection_local.id, 'stake': '25.0000'},
        format='json',
    )

    assert response.status_code == 403
    assert Bet.objects.count() == 0


@pytest.mark.django_db
def test_crear_apuesta_rechaza_saldo_insuficiente(client, usuario_verificado, selection_local):
    get_or_create_wallet(usuario_verificado)

    response = autenticar(client, usuario_verificado).post(
        reverse('bet-create'),
        {'selection': selection_local.id, 'stake': '25.0000'},
        format='json',
    )

    assert response.status_code == 400
    assert Bet.objects.count() == 0


@pytest.mark.django_db
def test_crear_apuesta_rechaza_evento_ya_iniciado(client, usuario_verificado, selection_local):
    get_or_create_wallet(usuario_verificado)
    deposit(usuario_verificado, Decimal('100.0000'))
    selection_local.market.event.starts_at = timezone.now() - timezone.timedelta(minutes=1)
    selection_local.market.event.save(update_fields=['starts_at'])

    response = autenticar(client, usuario_verificado).post(
        reverse('bet-create'),
        {'selection': selection_local.id, 'stake': '25.0000'},
        format='json',
    )

    assert response.status_code == 400
    assert Bet.objects.count() == 0


@pytest.mark.django_db
def test_crear_apuesta_rechaza_mercado_cerrado(client, usuario_verificado, selection_local):
    get_or_create_wallet(usuario_verificado)
    deposit(usuario_verificado, Decimal('100.0000'))
    selection_local.market.status = Market.Status.CERRADO
    selection_local.market.save(update_fields=['status'])

    response = autenticar(client, usuario_verificado).post(
        reverse('bet-create'),
        {'selection': selection_local.id, 'stake': '25.0000'},
        format='json',
    )

    assert response.status_code == 400
    assert Bet.objects.count() == 0


@pytest.mark.django_db
def test_settle_event_solo_admin_liquida_bets(client, usuario_verificado, admin_user, mercado_abierto):
    get_or_create_wallet(usuario_verificado)
    deposit(usuario_verificado, Decimal('100.0000'))
    local = mercado_abierto.selections.get(name='local')
    visitante = mercado_abierto.selections.get(name='visitante')
    bet_won = Bet.objects.create(
        user=usuario_verificado,
        market=mercado_abierto,
        selection=local,
        stake=Decimal('10.0000'),
        odds=local.odds,
        transaction_id=uuid.uuid4(),
    )
    bet_lost = Bet.objects.create(
        user=usuario_verificado,
        market=mercado_abierto,
        selection=visitante,
        stake=Decimal('20.0000'),
        odds=visitante.odds,
        transaction_id=uuid.uuid4(),
    )

    url = reverse('event-settle', kwargs={'pk': mercado_abierto.event_id})
    forbidden = autenticar(client, usuario_verificado).post(url, {'result': 'gana_local'}, format='json')
    assert forbidden.status_code == 403

    response = autenticar(client, admin_user).post(url, {'result': 'gana_local'}, format='json')

    assert response.status_code == 200
    bet_won.refresh_from_db()
    bet_lost.refresh_from_db()
    assert bet_won.status == BetStatus.SETTLED_WON
    assert bet_lost.status == BetStatus.SETTLED_LOST
    assert response.data['settled_won'] == 1
    assert response.data['settled_lost'] == 1
