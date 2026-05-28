import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.audit.models import SuspiciousActivity
from apps.audit.services import verify_chain
from apps.betting.choices import BetStatus
from apps.betting.models import Bet, Event, Market, Selection
from apps.users.choices import AccountStatus
from apps.wallet.models import Direction, LedgerEntry
from apps.wallet.services import deposit, get_or_create_wallet
from apps.wallet.services import reserve_for_bet
from apps.betting.services import cashout

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email='audit-admin@fairbet.pe',
        password='Test1234!',
        dni='102687740',
        first_name='Audit',
        last_name='Admin',
        birth_date='1995-01-01',
        account_status=AccountStatus.VERIFICADO,
        is_staff=True,
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email='audit-user@fairbet.pe',
        password='Test1234!',
        dni='746960471',
        first_name='Audit',
        last_name='User',
        birth_date='1995-01-01',
        account_status=AccountStatus.VERIFICADO,
    )


@pytest.fixture
def market_with_selection(db):
    event = Event.objects.create(
        name='Peru vs Chile',
        sport='futbol',
        starts_at=timezone.now() + timezone.timedelta(days=1),
    )
    market = Market.objects.create(
        event=event,
        name='Resultado final',
        market_type=Market.Type.UNO_X_DOS,
    )
    selection = Selection.objects.create(
        market=market,
        name='local',
        odds=Decimal('2.1000'),
    )
    return market, selection


@pytest.mark.django_db
def test_primer_registro():
    record = AuditLog.objects.create(
        event_type='wallet.deposit',
        payload={'amount': '10.0000'},
    )

    assert record.prev_hash == '0'


@pytest.mark.django_db
def test_cadena_valida():
    AuditLog.objects.create(event_type='wallet.deposit', payload={'amount': '10.0000'})
    AuditLog.objects.create(event_type='bet.accepted', payload={'stake': '5.0000'})
    AuditLog.objects.create(event_type='bet.settled', payload={'status': 'settled_won'})

    result = verify_chain()

    assert result == {'valid': True, 'total_records': 3}


@pytest.mark.django_db
def test_cadena_rota():
    AuditLog.objects.create(event_type='wallet.deposit', payload={'amount': '10.0000'})
    broken = AuditLog.objects.create(event_type='bet.accepted', payload={'stake': '5.0000'})
    AuditLog.objects.create(event_type='bet.settled', payload={'status': 'settled_won'})

    broken.payload = {'stake': '999.0000'}
    broken.save(update_fields=['payload'])

    result = verify_chain()

    assert result['valid'] is False
    assert result['broken_at'] == 2
    assert result['expected_hash'] != result['found_hash']


@pytest.mark.django_db
def test_signal_wallet_crea_auditlog(regular_user):
    get_or_create_wallet(regular_user)

    deposit(regular_user, Decimal('25.0000'))

    records = AuditLog.objects.filter(event_type='wallet.ledgerentry.created')
    assert records.count() == 2
    assert all(record.payload['transaction_id'] for record in records)
    assert {record.payload['direction'] for record in records} == {
        Direction.CREDIT,
        Direction.DEBIT,
    }


@pytest.mark.django_db
def test_signal_bet_crea_log_al_crear_y_al_cambiar_estado(regular_user, market_with_selection):
    market, selection = market_with_selection
    bet = Bet.objects.create(
        user=regular_user,
        market=market,
        selection=selection,
        stake=Decimal('10.0000'),
        odds=selection.odds,
        transaction_id=uuid.uuid4(),
    )

    created_log = AuditLog.objects.filter(event_type='bet.created').get()
    assert created_log.payload['bet_id'] == bet.id
    assert created_log.payload['status'] == BetStatus.ACCEPTED

    bet._original_status = bet.status
    bet.status = BetStatus.SETTLED_WON
    bet.save(update_fields=['status'])

    status_log = AuditLog.objects.filter(event_type='bet.status_changed').get()
    assert status_log.payload['old_status'] == BetStatus.ACCEPTED
    assert status_log.payload['new_status'] == BetStatus.SETTLED_WON


@pytest.mark.django_db
def test_verify_endpoint_retorna_ok_para_admin(client, admin_user):
    client.force_authenticate(user=admin_user)
    AuditLog.objects.create(event_type='wallet.deposit', payload={'amount': '10.0000'})
    AuditLog.objects.create(event_type='bet.accepted', payload={'stake': '5.0000'})

    response = client.get(reverse('audit-verify'))

    assert response.status_code == 200
    assert response.data == {'valid': True, 'total_records': 2}


@pytest.mark.django_db
def test_verify_endpoint_detecta_cadena_rota(client, admin_user):
    client.force_authenticate(user=admin_user)
    AuditLog.objects.create(event_type='wallet.deposit', payload={'amount': '10.0000'})
    broken = AuditLog.objects.create(event_type='bet.accepted', payload={'stake': '5.0000'})

    broken.payload = {'stake': '111.0000'}
    broken.save(update_fields=['payload'])

    response = client.get(reverse('audit-verify'))

    assert response.status_code == 200
    assert response.data['valid'] is False
    assert response.data['broken_at'] == 2


@pytest.mark.django_db
def test_verify_endpoint_requiere_admin(client, regular_user):
    client.force_authenticate(user=regular_user)

    response = client.get(reverse('audit-verify'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_apuestas_rapidas_crea_suspicious_activity(regular_user, market_with_selection):
    market, selection = market_with_selection
    for _ in range(6):
        Bet.objects.create(
            user=regular_user,
            market=market,
            selection=selection,
            stake=Decimal('1.0000'),
            odds=selection.odds,
            transaction_id=uuid.uuid4(),
        )

    assert SuspiciousActivity.objects.filter(
        user=regular_user,
        rule_triggered='apuestas_rapidas',
    ).exists()


@pytest.mark.django_db
def test_deposito_cashout_crea_suspicious_activity(regular_user, market_with_selection):
    market, selection = market_with_selection
    get_or_create_wallet(regular_user)
    deposit(regular_user, Decimal('100.0000'))
    reserve_for_bet(regular_user, Decimal('10.0000'))
    bet = Bet.objects.create(
        user=regular_user,
        market=market,
        selection=selection,
        stake=Decimal('10.0000'),
        odds=selection.odds,
        transaction_id=uuid.uuid4(),
    )

    cashout(bet, Decimal('2.0000'), transaction_id=uuid.uuid4())

    assert SuspiciousActivity.objects.filter(
        user=regular_user,
        rule_triggered='deposito_cashout',
    ).exists()


@pytest.mark.django_db
def test_suspicious_endpoint_solo_admin(client, admin_user, regular_user):
    SuspiciousActivity.objects.create(
        user=regular_user,
        rule_triggered='apuestas_rapidas',
        detail={'count': 6},
    )

    client.force_authenticate(user=regular_user)
    forbidden = client.get(reverse('audit-suspicious'))
    assert forbidden.status_code == 403

    client.force_authenticate(user=admin_user)
    response = client.get(reverse('audit-suspicious'))
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['rule_triggered'] == 'apuestas_rapidas'


@pytest.mark.django_db
def test_dashboard_endpoint_admin(client, admin_user):
    client.force_authenticate(user=admin_user)

    response = client.get(reverse('api-dashboard'))

    assert response.status_code == 200
    assert set(response.data) == {
        'ggr',
        'total_bets',
        'total_bets_won',
        'total_bets_lost',
        'total_bets_pending',
        'active_users',
        'exposure_by_event',
    }
