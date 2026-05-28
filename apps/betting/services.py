from decimal import Decimal

from django.db import transaction

from apps.betting.choices import BetStatus
from apps.betting.models import Bet, Market
from apps.wallet.models import AccountType, Direction, LedgerEntry
from apps.wallet.services import (
    _calcular_saldo,
    _crear_par_balanceado,
    _get_account,
    _get_global_account,
    _lock_account,
)


class CashoutNoPermitido(Exception):
    pass


def _cashout_entry(transaction_id):
    return (
        LedgerEntry.objects.filter(
            transaction_id=transaction_id,
            direction=Direction.CREDIT,
            account__type=AccountType.WALLET_USUARIO,
        )
        .select_related('account')
        .first()
    )


def cashout(bet, odds_actual, transaction_id=None):
    """
    Cancela una apuesta aceptada y acredita el valor de cashout al wallet.
    Formula: stake * odds_original / odds_actual * 0.85.
    """
    if odds_actual <= Decimal('0'):
        raise ValueError('odds_actual debe ser mayor a cero.')

    if transaction_id:
        existing_entry = _cashout_entry(transaction_id)
        if existing_entry:
            return existing_entry.amount, _calcular_saldo(existing_entry.account)

    with transaction.atomic():
        bet = (
            Bet.objects.select_for_update()
            .select_related('market', 'user')
            .get(pk=bet.pk)
        )

        if transaction_id:
            existing_entry = _cashout_entry(transaction_id)
            if existing_entry:
                return existing_entry.amount, _calcular_saldo(existing_entry.account)

        if bet.status != BetStatus.ACCEPTED:
            raise CashoutNoPermitido('Solo se permite cashout de apuestas accepted.')
        if bet.market.status != Market.Status.ABIERTO:
            raise CashoutNoPermitido('El mercado no esta abierto.')
        if bet.is_settled:
            raise CashoutNoPermitido('No se puede hacer cashout de una apuesta liquidada o cancelada.')

        cashout_value = (
            bet.stake * bet.odds / odds_actual * Decimal('0.85')
        ).quantize(Decimal('0.0001'))

        wallet = _get_account(bet.user, AccountType.WALLET_USUARIO)
        wallet = _lock_account(wallet)
        pendientes = _get_global_account(AccountType.APUESTAS_PENDIENTES)

        _crear_par_balanceado(
            cuenta_origen=pendientes,
            cuenta_destino=wallet,
            amount=cashout_value,
            description='cashout de apuesta',
            transaction_id=transaction_id,
        )

        bet.status = BetStatus.CANCELLED
        bet.save(update_fields=['status'])

        return cashout_value, _calcular_saldo(wallet)
