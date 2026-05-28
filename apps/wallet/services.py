import uuid
from decimal import Decimal

from django.db import transaction

from apps.users.choices import AccountStatus
from apps.wallet.models import Account, AccountType, Direction, LedgerEntry


class SaldoInsuficiente(Exception):
    pass


class CuentaNoEncontrada(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_account(user, account_type):
    try:
        return Account.objects.get(user=user, type=account_type)
    except Account.DoesNotExist:
        raise CuentaNoEncontrada(
            f'No existe cuenta {account_type} para el usuario {user.email}'
        )


def _get_global_account(account_type):
    account, _ = Account.objects.get_or_create(user=None, type=account_type)
    return account


def _calcular_saldo(account):
    """
    Calcula el saldo de una cuenta a partir de sus entradas.
    NUNCA se guarda el saldo como campo — siempre se deriva.
    Debe llamarse con la cuenta ya bloqueada via select_for_update en Account.
    """
    entradas = LedgerEntry.objects.filter(account=account)
    creditos = sum(e.amount for e in entradas if e.direction == Direction.CREDIT)
    debitos = sum(e.amount for e in entradas if e.direction == Direction.DEBIT)
    return creditos - debitos


def _lock_account(account):
    """
    Bloquea la fila de Account con SELECT FOR UPDATE.
    Esto serializa cualquier operación concurrente sobre la misma cuenta.
    Debe llamarse dentro de un transaction.atomic().
    """
    return Account.objects.select_for_update().get(pk=account.pk)


def _crear_par_balanceado(cuenta_origen, cuenta_destino, amount, description, transaction_id=None):
    """
    Crea dos entradas balanceadas: DEBIT en origen, CREDIT en destino.
    Debe llamarse siempre dentro de un transaction.atomic().
    """
    tid = transaction_id or uuid.uuid4()
    LedgerEntry.objects.create(
        account=cuenta_origen,
        amount=amount,
        direction=Direction.DEBIT,
        transaction_id=tid,
        description=f'{description} — débito {cuenta_origen.type}',
    )
    LedgerEntry.objects.create(
        account=cuenta_destino,
        amount=amount,
        direction=Direction.CREDIT,
        transaction_id=tid,
        description=f'{description} — crédito {cuenta_destino.type}',
    )
    return tid


# ---------------------------------------------------------------------------
# API pública del wallet
# ---------------------------------------------------------------------------

def get_or_create_wallet(user):
    """Obtiene o crea la cuenta wallet_usuario del usuario."""
    account, _ = Account.objects.get_or_create(
        user=user,
        type=AccountType.WALLET_USUARIO,
    )
    return account


def get_balance(user):
    """
    Retorna el saldo actual del wallet del usuario.
    Se calcula siempre desde las entradas — nunca desde un campo guardado.
    """
    with transaction.atomic():
        wallet = _get_account(user, AccountType.WALLET_USUARIO)
        _lock_account(wallet)
        return _calcular_saldo(wallet)


def deposit(user, amount, transaction_id=None):
    """
    Recarga fichas virtuales al wallet del usuario.
    Flujo: casa DEBIT → wallet_usuario CREDIT.

    Args:
        user: instancia del usuario.
        amount: Decimal con el monto a acreditar.
        transaction_id: UUID opcional para idempotencia.

    Returns:
        UUID de la transacción creada.
    """
    if amount <= Decimal('0'):
        raise ValueError('El monto debe ser mayor a cero.')

    if transaction_id and LedgerEntry.objects.filter(transaction_id=transaction_id).exists():
        return transaction_id

    with transaction.atomic():
        wallet = get_or_create_wallet(user)
        _lock_account(wallet)
        casa = _get_global_account(AccountType.CASA)
        tid = _crear_par_balanceado(
            cuenta_origen=casa,
            cuenta_destino=wallet,
            amount=amount,
            description='depósito simulado de fichas',
            transaction_id=transaction_id,
        )
    return tid


def withdraw(user, amount, transaction_id=None):
    """
    Retira fichas virtuales del wallet del usuario.
    Flujo: wallet_usuario DEBIT -> casa CREDIT.
    """
    if amount <= Decimal('0'):
        raise ValueError('El monto debe ser mayor a cero.')

    if user.account_status != AccountStatus.VERIFICADO:
        raise ValueError('Tu cuenta debe estar verificada para realizar retiros.')

    if transaction_id and LedgerEntry.objects.filter(transaction_id=transaction_id).exists():
        return transaction_id

    with transaction.atomic():
        if transaction_id and LedgerEntry.objects.select_for_update().filter(transaction_id=transaction_id).exists():
            return transaction_id

        wallet = _get_account(user, AccountType.WALLET_USUARIO)
        wallet = _lock_account(wallet)
        saldo = _calcular_saldo(wallet)

        if saldo < amount:
            raise SaldoInsuficiente(
                f'Saldo insuficiente: tiene {saldo}, necesita {amount}.'
            )

        casa = _get_global_account(AccountType.CASA)
        tid = _crear_par_balanceado(
            cuenta_origen=wallet,
            cuenta_destino=casa,
            amount=amount,
            description='retiro virtual de fichas',
            transaction_id=transaction_id,
        )
    return tid


def reserve_for_bet(user, amount, transaction_id=None):
    """
    Bloquea fondos para una apuesta pendiente.
    Flujo: wallet_usuario DEBIT → apuestas_pendientes CREDIT.

    Lanza SaldoInsuficiente si el usuario no tiene saldo suficiente.
    """
    if amount <= Decimal('0'):
        raise ValueError('El monto debe ser mayor a cero.')

    if transaction_id and LedgerEntry.objects.filter(transaction_id=transaction_id).exists():
        return transaction_id

    with transaction.atomic():
        wallet = _get_account(user, AccountType.WALLET_USUARIO)
        # Bloqueamos la fila de Account primero — esto serializa los requests
        # concurrentes sobre el mismo usuario. Mientras este bloque no haga
        # commit, ningún otro thread puede leer ni escribir esta cuenta.
        _lock_account(wallet)
        saldo = _calcular_saldo(wallet)

        if saldo < amount:
            raise SaldoInsuficiente(
                f'Saldo insuficiente: tiene {saldo}, necesita {amount}.'
            )

        pendientes = _get_global_account(AccountType.APUESTAS_PENDIENTES)
        tid = _crear_par_balanceado(
            cuenta_origen=wallet,
            cuenta_destino=pendientes,
            amount=amount,
            description='reserva de fondos para apuesta',
            transaction_id=transaction_id,
        )
    return tid


def settle_win(user, stake, odds, transaction_id=None):
    """
    Liquida una apuesta ganada.
    Flujo: apuestas_pendientes DEBIT → wallet_usuario CREDIT (payout completo).
    Payout = stake × odds, calculado con Decimal exacto.
    """
    if transaction_id and LedgerEntry.objects.filter(transaction_id=transaction_id).exists():
        return transaction_id

    payout = (stake * odds).quantize(Decimal('0.0001'))

    with transaction.atomic():
        pendientes = _get_global_account(AccountType.APUESTAS_PENDIENTES)
        wallet = _get_account(user, AccountType.WALLET_USUARIO)
        _lock_account(wallet)
        tid = _crear_par_balanceado(
            cuenta_origen=pendientes,
            cuenta_destino=wallet,
            amount=payout,
            description=f'liquidación ganada — payout {payout} (stake {stake} × odds {odds})',
            transaction_id=transaction_id,
        )
    return tid


def settle_loss(user, stake, transaction_id=None):
    """
    Liquida una apuesta perdida.
    Flujo: apuestas_pendientes DEBIT → casa CREDIT.
    El stake se queda en la casa.
    """
    if transaction_id and LedgerEntry.objects.filter(transaction_id=transaction_id).exists():
        return transaction_id

    with transaction.atomic():
        pendientes = _get_global_account(AccountType.APUESTAS_PENDIENTES)
        wallet = _get_account(user, AccountType.WALLET_USUARIO)
        _lock_account(wallet)
        casa = _get_global_account(AccountType.CASA)
        tid = _crear_par_balanceado(
            cuenta_origen=pendientes,
            cuenta_destino=casa,
            amount=stake,
            description=f'liquidación perdida — stake {stake} a la casa',
            transaction_id=transaction_id,
        )
    return tid
