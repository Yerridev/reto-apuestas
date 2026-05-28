import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.betting.choices import BetStatus
from apps.betting.models import AccumulatedBet, Event, Market, Selection
from apps.users.choices import AccountStatus
from apps.wallet.services import deposit, get_balance, get_or_create_wallet

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    user = User.objects.create_user(
        email='acc@fairbet.pe',
        password='Test1234!',
        dni='746960471',
        first_name='Acc',
        last_name='User',
        birth_date='1995-01-01',
        account_status=AccountStatus.VERIFICADO,
    )
    get_or_create_wallet(user)
    deposit(user, Decimal('1000.0000'))
    return user


@pytest.fixture
def eventos(db):
    e1 = Event.objects.create(
        name='Evento 1', sport='futbol',
        starts_at=timezone.now() + timezone.timedelta(days=1),
    )
    e2 = Event.objects.create(
        name='Evento 2', sport='futbol',
        starts_at=timezone.now() + timezone.timedelta(days=2),
    )
    return e1, e2


@pytest.fixture
def admin_user(db):
    admin = User.objects.create_user(
        email='admin-acc@fairbet.pe',
        password='Test1234!',
        dni='102687740',
        first_name='Admin',
        last_name='Acc',
        birth_date='1990-01-01',
        account_status=AccountStatus.VERIFICADO,
        is_staff=True,
        is_superuser=True,
    )
    get_or_create_wallet(admin)
    deposit(admin, Decimal('1000.0000'))
    return admin


@pytest.fixture
def selections(eventos):
    e1, e2 = eventos
    m1 = Market.objects.create(event=e1, name='Resultado final', market_type=Market.Type.UNO_X_DOS)
    m2 = Market.objects.create(event=e2, name='Resultado final', market_type=Market.Type.UNO_X_DOS)
    s1 = Selection.objects.create(market=m1, name='local', odds=Decimal('2.1000'))
    s2 = Selection.objects.create(market=m2, name='visitante', odds=Decimal('3.8000'))
    return s1, s2


def autenticar(client, user):
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_colocar_combinada_valida(client, user, selections):
    s1, s2 = selections
    url = reverse('accumulated-create')
    key = str(uuid.uuid4())

    response = autenticar(client, user).post(url, {
        'selections': [s1.id, s2.id],
        'stake': '100.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=key)

    assert response.status_code == 201
    data = response.data
    assert data['status'] == BetStatus.ACCEPTED
    assert Decimal(data['combined_odds']) == Decimal('7.9800')
    assert len(data['legs']) == 2

    acc = AccumulatedBet.objects.get(pk=data['id'])
    assert acc.legs.count() == 2
    expected_balance = Decimal('1000.0000') - Decimal('100.0000')
    assert get_balance(user) == expected_balance


@pytest.mark.django_db
def test_combinada_rechaza_menos_de_2_selecciones(client, user, selections):
    s1, _ = selections
    response = autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id],
        'stake': '100.0000',
    }, format='json')
    assert response.status_code == 400
    assert AccumulatedBet.objects.count() == 0


@pytest.mark.django_db
def test_combinada_rechaza_mismo_mercado(client, user, selections):
    s1, _ = selections
    m1 = s1.market
    s3 = Selection.objects.create(market=m1, name='visitante', odds=Decimal('3.8000'))

    response = autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s3.id],
        'stake': '100.0000',
    }, format='json')
    assert response.status_code == 400
    assert AccumulatedBet.objects.count() == 0


@pytest.mark.django_db
def test_combinada_rechaza_evento_ya_iniciado(client, user, selections):
    s1, s2 = selections
    s1.market.event.starts_at = timezone.now() - timezone.timedelta(hours=1)
    s1.market.event.save(update_fields=['starts_at'])

    response = autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '100.0000',
    }, format='json')
    assert response.status_code == 400
    assert AccumulatedBet.objects.count() == 0


@pytest.mark.django_db
def test_combinada_idempotente(client, user, selections):
    s1, s2 = selections
    key = str(uuid.uuid4())

    first = autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '100.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=key)
    second = autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '100.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=key)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data['id'] == second.data['id']
    assert AccumulatedBet.objects.count() == 1


@pytest.mark.django_db
def test_liquidar_evento_liquida_combinada_perdedora(client, user, selections, admin_user):
    s1, s2 = selections
    get_or_create_wallet(admin_user)

    autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '100.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    balance_before = get_balance(user)
    acc = AccumulatedBet.objects.get(user=user)

    admin_client = autenticar(APIClient(), admin_user)
    settle_url = reverse('event-settle', kwargs={'pk': s1.market.event_id})
    response = admin_client.post(settle_url, {'result': 'gana_visitante'}, format='json')
    assert response.status_code == 200

    acc.refresh_from_db()
    assert acc.status == BetStatus.SETTLED_LOST
    assert balance_before == get_balance(user)


@pytest.mark.django_db
def test_liquidar_evento_liquida_combinada_ganadora(client, user, selections, admin_user):
    s1, s2 = selections
    get_or_create_wallet(admin_user)

    autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '100.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    acc = AccumulatedBet.objects.get(user=user)
    balance_before = get_balance(user)

    admin_client = autenticar(APIClient(), admin_user)

    settle_url_1 = reverse('event-settle', kwargs={'pk': s1.market.event_id})
    resp1 = admin_client.post(settle_url_1, {'result': 'gana_local'}, format='json')
    assert resp1.status_code == 200

    acc.refresh_from_db()
    assert acc.status == BetStatus.ACCEPTED

    settle_url_2 = reverse('event-settle', kwargs={'pk': s2.market.event_id})
    resp2 = admin_client.post(settle_url_2, {'result': 'gana_visitante'}, format='json')
    assert resp2.status_code == 200

    acc.refresh_from_db()
    assert acc.status == BetStatus.SETTLED_WON
    expected_payout = Decimal('100.0000') * Decimal('7.9800')
    expected_balance = balance_before + expected_payout
    assert get_balance(user) == expected_balance


@pytest.mark.django_db
def test_listar_combinadas(client, user, selections):
    s1, s2 = selections
    autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '50.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    autenticar(client, user).post(reverse('accumulated-create'), {
        'selections': [s1.id, s2.id],
        'stake': '30.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    response = autenticar(client, user).get(reverse('accumulated-list'))
    assert response.status_code == 200
    assert len(response.data) == 2


@pytest.mark.django_db
def test_apuesta_combinada_en_vivo_permite_eventos_iniciados(client, user, eventos, selections):
    """Verifica que apuestas combinadas acepten eventos EN_VIVO aunque hayan iniciado."""
    s1, s2 = selections
    e1, e2 = eventos
    
    # Marcar ambos eventos como EN_VIVO y que ya hayan iniciado
    e1.status = Event.Status.EN_VIVO
    e1.starts_at = timezone.now() - timezone.timedelta(minutes=5)
    e1.save(update_fields=['status', 'starts_at'])
    
    e2.status = Event.Status.EN_VIVO
    e2.starts_at = timezone.now() - timezone.timedelta(minutes=3)
    e2.save(update_fields=['status', 'starts_at'])

    response = autenticar(client, user).post(
        reverse('accumulated-create'),
        {
            'selections': [s1.id, s2.id],
            'stake': '50.0000',
        },
        format='json',
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )

    assert response.status_code == 201
    assert response.data['status'] == BetStatus.ACCEPTED
    assert AccumulatedBet.objects.count() == 1


