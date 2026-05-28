import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.betting.choices import BetStatus
from apps.betting.models import AccumulatedBet, AccumulatedBetLeg, Bet, Event, Market
from apps.users.choices import AccountStatus
from apps.wallet.models import AccountType, Direction, LedgerEntry
from apps.wallet.services import (
    _calcular_saldo,
    _crear_par_balanceado,
    _get_account,
    _get_global_account,
    _lock_account,
    reserve_for_bet,
    settle_loss,
    settle_win,
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


def place_accumulator(user, selections_data, stake, transaction_id=None):
    if user.account_status != AccountStatus.VERIFICADO:
        raise ValueError('Tu cuenta debe estar verificada para apostar.')

    if len(selections_data) < 2:
        raise ValueError('La combinada debe tener al menos 2 selecciones.')

    seen_markets = set()
    combined_odds = Decimal('1.0000')
    legs_info = []

    for sel_data in selections_data:
        selection = sel_data['selection']
        market = selection.market

        if market.id in seen_markets:
            raise ValueError(f'Dos selecciones del mismo mercado ({market.name}) no son válidas.')
        seen_markets.add(market.id)

        event = market.event
        if event.status != Event.Status.PROGRAMADO:
            raise ValueError(f'El evento "{event.name}" no esta programado.')
        if event.starts_at <= timezone.now():
            raise ValueError(f'El evento "{event.name}" ya inicio.')
        if market.status != Market.Status.ABIERTO:
            raise ValueError(f'El mercado "{market.name}" no esta abierto.')
        if stake > settings.MAX_BET_STAKE:
            raise ValueError('El monto supera el limite maximo por apuesta.')

        combined_odds = (combined_odds * selection.odds).quantize(Decimal('0.0001'))
        legs_info.append({'selection': selection, 'market': market, 'odds': selection.odds})

    existing = AccumulatedBet.objects.filter(transaction_id=transaction_id, user=user).first()
    if existing:
        return existing

    with transaction.atomic():
        reserve_for_bet(user, stake, transaction_id=transaction_id)

        acc = AccumulatedBet.objects.create(
            user=user,
            stake=stake,
            combined_odds=combined_odds,
            transaction_id=transaction_id,
        )

        for leg in legs_info:
            AccumulatedBetLeg.objects.create(
                accumulated_bet=acc,
                selection=leg['selection'],
                market=leg['market'],
                odds_at_bet=leg['odds'],
            )

    return acc


def settle_accumulator_legs(event, winning_selection_name):
    """
    Liquida las piernas de combinadas para el evento dado.
    Se llama desde EventSettleView tras liquidar apuestas simples.
    """
    markets = event.markets.values_list('id', flat=True)
    legs = AccumulatedBetLeg.objects.select_for_update().filter(
        market_id__in=markets,
        settled=False,
        accumulated_bet__status=BetStatus.ACCEPTED,
    ).select_related('accumulated_bet', 'accumulated_bet__user')

    processed_accs = set()

    for leg in legs:
        leg.settled = True
        leg.won = leg.selection.name == winning_selection_name
        leg.save(update_fields=['settled', 'won'])

        acc = leg.accumulated_bet
        if acc.id in processed_accs:
            continue
        processed_accs.add(acc.id)

        all_legs = acc.legs.all()
        settled_legs = [l for l in all_legs if l.settled]
        pending_legs = [l for l in all_legs if not l.settled]

        has_lost = any(l.won is False for l in settled_legs)
        tid = uuid.uuid5(uuid.NAMESPACE_URL, f'acc-settlement:{acc.transaction_id}')

        if has_lost:
            settle_loss(acc.user, acc.stake, transaction_id=tid)
            acc.status = BetStatus.SETTLED_LOST
            for leg in pending_legs:
                leg.settled = True
                leg.won = False
                leg.save(update_fields=['settled', 'won'])
        elif not pending_legs:
            settle_win(acc.user, acc.stake, acc.combined_odds, transaction_id=tid)
            acc.status = BetStatus.SETTLED_WON
        else:
            continue

        acc.save(update_fields=['status'])
