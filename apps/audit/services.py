from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.audit.models import AuditLog, SuspiciousActivity, compute_hash
from apps.betting.choices import BetStatus
from apps.betting.models import Bet, Event, Market
from apps.wallet.models import AccountType, Direction, LedgerEntry


def verify_chain():
    """
    Recorre toda la cadena de auditoria en orden cronologico y valida
    que cada registro apunte correctamente al hash anterior.
    """
    previous_hash = '0'

    for index, record in enumerate(AuditLog.objects.order_by('created_at', 'id'), start=1):
        expected_hash = compute_hash(previous_hash, record.payload)
        if record.prev_hash != previous_hash or record.hash != expected_hash:
            return {
                'valid': False,
                'broken_at': index,
                'expected_hash': expected_hash,
                'found_hash': record.hash,
            }
        previous_hash = record.hash

    return {
        'valid': True,
        'total_records': AuditLog.objects.count(),
    }


def flag_fast_bets(user):
    since = timezone.now() - timedelta(seconds=60)
    count = Bet.objects.filter(user=user, created_at__gte=since).count()
    if count <= 5:
        return None

    return SuspiciousActivity.objects.create(
        user=user,
        rule_triggered='apuestas_rapidas',
        detail={'bets_last_60_seconds': count},
    )


def flag_deposit_cashout(entry):
    if entry.account.type != AccountType.WALLET_USUARIO or entry.direction != Direction.CREDIT:
        return None
    if not entry.account.user_id:
        return None

    description = entry.description.lower()
    is_deposit = 'dep' in description
    is_cashout = 'cashout' in description
    if not (is_deposit or is_cashout):
        return None

    since = entry.created_at - timedelta(minutes=5)
    base = LedgerEntry.objects.filter(
        account__user=entry.account.user,
        account__type=AccountType.WALLET_USUARIO,
        direction=Direction.CREDIT,
        created_at__gte=since,
        created_at__lte=entry.created_at,
    )
    counterpart = base.filter(description__icontains='cashout' if is_deposit else 'dep').first()
    if not counterpart:
        return None

    return SuspiciousActivity.objects.create(
        user=entry.account.user,
        rule_triggered='deposito_cashout',
        detail={
            'ledger_entry_id': entry.id,
            'counterpart_entry_id': counterpart.id,
            'window_minutes': 5,
        },
    )


def dashboard_metrics():
    won = Bet.objects.filter(status=BetStatus.SETTLED_WON)
    lost = Bet.objects.filter(status=BetStatus.SETTLED_LOST)

    lost_stakes = lost.aggregate(total=Coalesce(Sum('stake'), Decimal('0.0000')))['total']
    paid_payouts = sum(
        (bet.stake * bet.odds).quantize(Decimal('0.0001')) for bet in won
    , Decimal('0.0000'))
    ggr = (lost_stakes - paid_payouts).quantize(Decimal('0.0001'))

    exposure = []
    events = Event.objects.filter(status__in=[Event.Status.PROGRAMADO, Event.Status.EN_VIVO]).prefetch_related(
        'markets__selections',
    )
    for event in events:
        selections = []
        for market in event.markets.filter(status=Market.Status.ABIERTO):
            for selection in market.selections.all():
                amount = sum(
                    (bet.stake * bet.odds).quantize(Decimal('0.0001'))
                    for bet in Bet.objects.filter(selection=selection, status=BetStatus.ACCEPTED)
                , Decimal('0.0000'))
                selections.append({'selection': selection.name, 'exposure': str(amount.quantize(Decimal('0.0001')))})
        if selections:
            exposure.append({'event_id': event.id, 'event': event.name, 'selections': selections})

    User = get_user_model()
    status_counts = Bet.objects.values('status').annotate(total=Count('id'))
    counts = {item['status']: item['total'] for item in status_counts}
    return {
        'ggr': str(ggr),
        'total_bets': Bet.objects.count(),
        'total_bets_won': counts.get(BetStatus.SETTLED_WON, 0),
        'total_bets_lost': counts.get(BetStatus.SETTLED_LOST, 0),
        'total_bets_pending': counts.get(BetStatus.ACCEPTED, 0),
        'active_users': User.objects.filter(is_active=True).count(),
        'exposure_by_event': exposure,
    }
