import threading
import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.wallet.models import Account, AccountType
from apps.wallet.services import (
    SaldoInsuficiente,
    deposit,
    get_balance,
    get_or_create_wallet,
    reserve_for_bet,
    settle_loss,
    settle_win,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        email='servicios@fairbet.pe',
        password='Test1234!',
        dni='123456781',
        first_name='Test',
        last_name='User',
        birth_date='1995-01-01',
    )


@pytest.fixture
def usuario_con_saldo(usuario):
    get_or_create_wallet(usuario)
    deposit(usuario, Decimal('500.0000'))
    return usuario


# ---------------------------------------------------------------------------
# Tests de servicios
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_deposit_acredita_saldo(usuario):
    """Después de un depósito el saldo del usuario debe reflejar el monto."""
    get_or_create_wallet(usuario)
    deposit(usuario, Decimal('200.0000'))
    assert get_balance(usuario) == Decimal('200.0000')


@pytest.mark.django_db
def test_deposit_idempotente(usuario):
    """Dos depósitos con el mismo transaction_id solo deben acreditar una vez."""
    get_or_create_wallet(usuario)
    tid = uuid.uuid4()
    deposit(usuario, Decimal('100.0000'), transaction_id=tid)
    deposit(usuario, Decimal('100.0000'), transaction_id=tid)
    assert get_balance(usuario) == Decimal('100.0000')


@pytest.mark.django_db
def test_reserve_for_bet_descuenta_saldo(usuario_con_saldo):
    """Reservar fondos para una apuesta debe reducir el saldo disponible."""
    saldo_antes = get_balance(usuario_con_saldo)
    reserve_for_bet(usuario_con_saldo, Decimal('100.0000'))
    saldo_despues = get_balance(usuario_con_saldo)
    assert saldo_despues == saldo_antes - Decimal('100.0000')


@pytest.mark.django_db
def test_reserve_for_bet_saldo_insuficiente(usuario_con_saldo):
    """Intentar apostar más del saldo disponible debe lanzar SaldoInsuficiente."""
    with pytest.raises(SaldoInsuficiente):
        reserve_for_bet(usuario_con_saldo, Decimal('9999.0000'))


@pytest.mark.django_db
def test_settle_win_acredita_payout_exacto(usuario_con_saldo):
    """El payout de una apuesta ganada debe ser exactamente stake × odds."""
    stake = Decimal('100.0000')
    odds = Decimal('2.5000')
    payout_esperado = Decimal('250.0000')

    saldo_antes = get_balance(usuario_con_saldo)
    reserve_for_bet(usuario_con_saldo, stake)
    settle_win(usuario_con_saldo, stake, odds)
    saldo_despues = get_balance(usuario_con_saldo)

    assert saldo_despues == saldo_antes - stake + payout_esperado


@pytest.mark.django_db
def test_settle_loss_no_devuelve_stake(usuario_con_saldo):
    """Al perder una apuesta el stake no debe volver al wallet del usuario."""
    stake = Decimal('100.0000')
    saldo_antes = get_balance(usuario_con_saldo)
    reserve_for_bet(usuario_con_saldo, stake)
    settle_loss(usuario_con_saldo, stake)
    saldo_despues = get_balance(usuario_con_saldo)

    assert saldo_despues == saldo_antes - stake


@pytest.mark.django_db
def test_saldo_nunca_negativo(usuario_con_saldo):
    """El saldo del usuario nunca debe quedar negativo."""
    saldo = get_balance(usuario_con_saldo)
    assert saldo >= Decimal('0')

    with pytest.raises(SaldoInsuficiente):
        reserve_for_bet(usuario_con_saldo, saldo + Decimal('1.0000'))

    assert get_balance(usuario_con_saldo) >= Decimal('0')


# ---------------------------------------------------------------------------
# Test de concurrencia — W-09
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
def test_concurrencia_sin_doble_gasto():
    """
    Simula N requests simultáneos intentando apostar el mismo saldo.
    Solo los que encuentren saldo suficiente deben poder reservar.
    El saldo final nunca debe ser negativo.
    """
    user = User.objects.create_user(
        email='concurrencia@fairbet.pe',
        password='Test1234!',
        dni='123456781',
        first_name='Test',
        last_name='Concurrencia',
        birth_date='1995-01-01',
    )
    get_or_create_wallet(user)
    deposit(user, Decimal('300.0000'))

    errores = []
    exitos = []

    def intentar_reserva():
        try:
            reserve_for_bet(user, Decimal('100.0000'))
            exitos.append(True)
        except SaldoInsuficiente:
            errores.append(True)

    # 10 threads intentan reservar 100 cada uno, solo 3 deben poder
    hilos = [threading.Thread(target=intentar_reserva) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    saldo_final = get_balance(user)

    # El saldo nunca debe ser negativo
    assert saldo_final >= Decimal('0'), f'Saldo negativo detectado: {saldo_final}'

    # Solo 3 reservas de 100 caben en 300
    assert len(exitos) <= 3, f'Se permitieron {len(exitos)} reservas, máximo 3'

    # exitos + errores = 10 threads
    assert len(exitos) + len(errores) == 10
