import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.choices import AccountStatus
from apps.wallet.services import deposit, get_balance, get_or_create_wallet

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario_verificado(db):
    user = User.objects.create_user(
        email='endpoints@fairbet.pe',
        password='Test1234!',
        dni='123456781',
        first_name='Test',
        last_name='Endpoints',
        birth_date='1995-01-01',
    )
    user.account_status = AccountStatus.VERIFICADO
    user.save(update_fields=['account_status'])
    return user


@pytest.fixture
def usuario_pendiente(db):
    return User.objects.create_user(
        email='pendiente@fairbet.pe',
        password='Test1234!',
        dni='123456781',
        first_name='Test',
        last_name='Pendiente',
        birth_date='1995-01-01',
    )


@pytest.fixture
def client_autenticado(client, usuario_verificado):
    client.force_authenticate(user=usuario_verificado)
    return client, usuario_verificado


# ---------------------------------------------------------------------------
# Tests POST /api/wallet/deposit/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_deposit_endpoint_ok(client_autenticado):
    """Un usuario verificado puede depositar fichas y recibe el saldo actualizado."""
    client, user = client_autenticado
    url = reverse('wallet-deposit')

    response = client.post(url, {'amount': '200.0000'}, format='json')

    assert response.status_code == 201
    assert response.data['amount'] == '200.0000'
    assert Decimal(response.data['balance']) == Decimal('200.0000')
    assert 'transaction_id' in response.data


@pytest.mark.django_db
def test_deposit_endpoint_sin_auth(client):
    """Sin autenticación debe retornar 401."""
    url = reverse('wallet-deposit')
    response = client.post(url, {'amount': '100.0000'}, format='json')
    assert response.status_code == 401


@pytest.mark.django_db
def test_deposit_endpoint_cuenta_no_verificada(client, usuario_pendiente):
    """Un usuario no verificado no puede depositar — debe retornar 400."""
    client.force_authenticate(user=usuario_pendiente)
    url = reverse('wallet-deposit')
    response = client.post(url, {'amount': '100.0000'}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_deposit_endpoint_monto_invalido(client_autenticado):
    """Un monto negativo o cero debe retornar 400."""
    client, _ = client_autenticado
    url = reverse('wallet-deposit')

    response = client.post(url, {'amount': '0.0000'}, format='json')
    assert response.status_code == 400

    response = client.post(url, {'amount': '-50.0000'}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_deposit_endpoint_idempotente(client_autenticado):
    """El mismo idempotency_key no debe acreditar dos veces."""
    client, user = client_autenticado
    url = reverse('wallet-deposit')
    tid = str(uuid.uuid4())

    client.post(url, {'amount': '100.0000', 'idempotency_key': tid}, format='json')
    client.post(url, {'amount': '100.0000', 'idempotency_key': tid}, format='json')

    # Verificamos con el endpoint de balance
    balance_url = reverse('wallet-balance')
    response = client.get(balance_url)
    assert Decimal(response.data['balance']) == Decimal('100.0000')


@pytest.mark.django_db
def test_deposit_endpoint_idempotency_key_por_header(client_autenticado):
    """El idempotency key también se puede pasar por header."""
    client, user = client_autenticado
    url = reverse('wallet-deposit')
    tid = str(uuid.uuid4())

    client.post(url, {'amount': '100.0000'}, format='json', HTTP_IDEMPOTENCY_KEY=tid)
    client.post(url, {'amount': '100.0000'}, format='json', HTTP_IDEMPOTENCY_KEY=tid)

    balance_url = reverse('wallet-balance')
    response = client.get(balance_url)
    assert Decimal(response.data['balance']) == Decimal('100.0000')


# ---------------------------------------------------------------------------
# Tests GET /api/wallet/balance/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_balance_endpoint_saldo_inicial(client_autenticado):
    """Un usuario nuevo sin depósitos debe tener saldo 0."""
    client, user = client_autenticado
    url = reverse('wallet-balance')

    response = client.get(url)

    assert response.status_code == 200
    assert Decimal(response.data['balance']) == Decimal('0')
    assert response.data['currency'] == 'fichas'


@pytest.mark.django_db
def test_balance_endpoint_refleja_depositos(client_autenticado):
    """El balance debe reflejar los depósitos realizados."""
    client, user = client_autenticado

    get_or_create_wallet(user)
    deposit(user, Decimal('350.0000'))

    url = reverse('wallet-balance')
    response = client.get(url)

    assert response.status_code == 200
    assert Decimal(response.data['balance']) == Decimal('350.0000')


@pytest.mark.django_db
def test_balance_endpoint_sin_auth(client):
    """Sin autenticación debe retornar 401."""
    url = reverse('wallet-balance')
    response = client.get(url)
    assert response.status_code == 401


@pytest.mark.django_db
def test_withdraw_endpoint_ok_reduce_saldo(client_autenticado):
    client, user = client_autenticado
    get_or_create_wallet(user)
    deposit(user, Decimal('300.0000'))

    response = client.post(reverse('wallet-withdraw'), {'amount': '100.0000'}, format='json')

    assert response.status_code == 201
    assert response.data['message'] == 'Retiro virtual realizado correctamente.'
    assert Decimal(response.data['balance']) == Decimal('200.0000')
    assert get_balance(user) == Decimal('200.0000')


@pytest.mark.django_db
def test_withdraw_endpoint_saldo_insuficiente(client_autenticado):
    client, user = client_autenticado
    get_or_create_wallet(user)
    deposit(user, Decimal('50.0000'))

    response = client.post(reverse('wallet-withdraw'), {'amount': '100.0000'}, format='json')

    assert response.status_code == 400


@pytest.mark.django_db
def test_withdraw_endpoint_sin_auth(client):
    response = client.post(reverse('wallet-withdraw'), {'amount': '100.0000'}, format='json')
    assert response.status_code == 401


@pytest.mark.django_db
def test_withdraw_endpoint_cuenta_no_verificada(client, usuario_pendiente):
    client.force_authenticate(user=usuario_pendiente)
    response = client.post(reverse('wallet-withdraw'), {'amount': '100.0000'}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_withdraw_endpoint_idempotente(client_autenticado):
    client, user = client_autenticado
    get_or_create_wallet(user)
    deposit(user, Decimal('300.0000'))
    tid = str(uuid.uuid4())

    client.post(reverse('wallet-withdraw'), {'amount': '100.0000'}, format='json', HTTP_IDEMPOTENCY_KEY=tid)
    client.post(reverse('wallet-withdraw'), {'amount': '100.0000'}, format='json', HTTP_IDEMPOTENCY_KEY=tid)

    assert get_balance(user) == Decimal('200.0000')
