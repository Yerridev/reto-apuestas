import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from apps.wallet.models import Account, AccountType, Direction, LedgerEntry

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        email='invariante@fairbet.pe',
        password='Test1234!',
        dni='123456781',
        first_name='Test',
        last_name='User',
        birth_date='1995-01-01',
    )


@pytest.fixture
def cuentas(usuario):
    wallet = Account.objects.create(user=usuario, type=AccountType.WALLET_USUARIO)
    casa, _ = Account.objects.get_or_create(user=None, type=AccountType.CASA)
    return wallet, casa


@pytest.fixture
def cuentas_hypothesis(db):
    """
    Fixture para los tests de hypothesis. Usamos django_db normal (sin transaction=True)
    para que el usuario y las cuentas persistan entre ejemplos. Las LedgerEntry se limpian
    manualmente al inicio de cada ejemplo dentro del test.
    """
    user, _ = User.objects.get_or_create(
        email='hypothesis@fairbet.pe',
        defaults={
            'dni': '123456781',
            'first_name': 'Hyp',
            'last_name': 'Test',
            'birth_date': '1995-01-01',
        },
    )
    wallet, _ = Account.objects.get_or_create(user=user, type=AccountType.WALLET_USUARIO)
    casa, _ = Account.objects.get_or_create(user=None, type=AccountType.CASA)
    return wallet, casa


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def crear_entradas_balanceadas(wallet_account, casa_account, amount, transaction_id=None):
    """
    Simula un depósito: casa DEBIT, wallet_usuario CREDIT.
    Las dos entradas juntas suman cero (invariante de partida doble).
    """
    tid = transaction_id or uuid.uuid4()
    LedgerEntry.objects.create(
        account=casa_account,
        amount=amount,
        direction=Direction.DEBIT,
        transaction_id=tid,
        description='depósito simulado — débito casa',
    )
    LedgerEntry.objects.create(
        account=wallet_account,
        amount=amount,
        direction=Direction.CREDIT,
        transaction_id=tid,
        description='depósito simulado — crédito wallet',
    )


def calcular_suma_global():
    """
    La suma global de todas las entradas debe ser siempre cero.
    CREDIT suma positivo, DEBIT suma negativo.
    """
    total = Decimal('0')
    for entry in LedgerEntry.objects.all():
        if entry.direction == Direction.CREDIT:
            total += entry.amount
        else:
            total -= entry.amount
    return total


# ---------------------------------------------------------------------------
# Tests normales (pytest)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_suma_global_cero_tras_deposito(cuentas):
    """Después de un depósito la suma global de entradas debe ser 0."""
    wallet, casa = cuentas
    crear_entradas_balanceadas(wallet, casa, Decimal('100.0000'))
    assert calcular_suma_global() == Decimal('0')


@pytest.mark.django_db
def test_suma_global_cero_multiples_operaciones(cuentas):
    """La invariante se mantiene con varias operaciones seguidas."""
    wallet, casa = cuentas
    for monto in ['50.0000', '200.0000', '75.5000']:
        crear_entradas_balanceadas(wallet, casa, Decimal(monto))
    assert calcular_suma_global() == Decimal('0')


@pytest.mark.django_db
def test_saldo_calculado_correctamente(cuentas):
    """El saldo del wallet debe reflejar exactamente los créditos menos los débitos."""
    wallet, casa = cuentas
    crear_entradas_balanceadas(wallet, casa, Decimal('300.0000'))

    creditos = LedgerEntry.objects.filter(account=wallet, direction=Direction.CREDIT)
    debitos = LedgerEntry.objects.filter(account=wallet, direction=Direction.DEBIT)
    saldo = sum(e.amount for e in creditos) - sum(e.amount for e in debitos)

    assert saldo == Decimal('300.0000')


@pytest.mark.django_db
def test_idempotencia_transaction_id(cuentas):
    """Dos entradas con el mismo transaction_id representan la misma operación."""
    wallet, casa = cuentas
    tid = uuid.uuid4()
    crear_entradas_balanceadas(wallet, casa, Decimal('100.0000'), transaction_id=tid)

    entradas = LedgerEntry.objects.filter(transaction_id=tid)
    assert entradas.count() == 2


# ---------------------------------------------------------------------------
# Property-based tests con hypothesis
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@given(
    monto=st.decimals(
        min_value=Decimal('0.0001'),
        max_value=Decimal('9999.9999'),
        places=4,
    )
)
@h_settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_invariante_partida_doble_hypothesis(monto, cuentas_hypothesis):
    """
    Propiedad: sin importar el monto, después de crear entradas balanceadas
    la suma global siempre es cero.
    Suprimimos function_scoped_fixture porque limpiamos LedgerEntry manualmente
    al inicio de cada ejemplo — el fixture no necesita resetearse.
    """
    LedgerEntry.objects.all().delete()
    wallet, casa = cuentas_hypothesis
    crear_entradas_balanceadas(wallet, casa, monto)
    assert calcular_suma_global() == Decimal('0')


@pytest.mark.django_db
@given(
    montos=st.lists(
        st.decimals(min_value=Decimal('0.0001'), max_value=Decimal('999.9999'), places=4),
        min_size=1,
        max_size=10,
    )
)
@h_settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_invariante_multiples_operaciones_hypothesis(montos, cuentas_hypothesis):
    """
    Propiedad: la invariante se mantiene con cualquier cantidad de operaciones,
    no importa cuántas ni de qué montos.
    """
    LedgerEntry.objects.all().delete()
    wallet, casa = cuentas_hypothesis
    for monto in montos:
        crear_entradas_balanceadas(wallet, casa, monto)
    assert calcular_suma_global() == Decimal('0')
