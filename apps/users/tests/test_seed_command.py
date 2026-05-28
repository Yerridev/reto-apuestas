import pytest
from django.core.management import call_command

from apps.betting.models import Event
from apps.users.choices import AccountStatus
from apps.users.models import User
from apps.wallet.services import get_balance


@pytest.mark.django_db
def test_seed_data_crea_usuarios_eventos_y_wallet():
    call_command('seed_data')

    admin = User.objects.get(email='admin@fairbet.pe')
    player1 = User.objects.get(email='player1@fairbet.pe')
    player2 = User.objects.get(email='player2@fairbet.pe')

    assert admin.is_superuser is True
    assert admin.is_staff is True
    assert player1.account_status == AccountStatus.VERIFICADO
    assert player2.account_status == AccountStatus.PENDIENTE_VERIFICACION
    assert get_balance(player1) >= 0
    assert Event.objects.exists()


@pytest.mark.django_db
def test_seed_data_es_idempotente_en_fondeo_wallet():
    call_command('seed_data')
    player1 = User.objects.get(email='player1@fairbet.pe')
    balance_1 = get_balance(player1)

    call_command('seed_data')
    player1.refresh_from_db()
    balance_2 = get_balance(player1)

    assert balance_2 == balance_1
