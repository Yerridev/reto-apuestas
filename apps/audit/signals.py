from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.audit.models import AuditLog
from apps.audit.services import flag_deposit_cashout, flag_fast_bets
from apps.betting.models import Bet
from apps.wallet.models import LedgerEntry


@receiver(post_save, sender=LedgerEntry)
def audit_ledger_entry(sender, instance, created, **kwargs):
    """Registra en auditoria cada nueva entrada contable creada en wallet."""
    if not created:
        return

    AuditLog.objects.create(
        event_type='wallet.ledgerentry.created',
        payload={
            'account_id': instance.account_id,
            'amount': str(instance.amount),
            'direction': instance.direction,
            'transaction_id': str(instance.transaction_id),
        },
    )
    flag_deposit_cashout(instance)


@receiver(post_save, sender=Bet)
def audit_bet_status_change(sender, instance, created, **kwargs):
    """Audita la creacion de apuestas y sus cambios de estado validos."""
    if created:
        AuditLog.objects.create(
            event_type='bet.created',
            payload={
                'bet_id': instance.id,
                'user_id': instance.user_id,
                'market_id': instance.market_id,
                'selection_id': instance.selection_id,
                'stake': str(instance.stake),
                'odds': str(instance.odds),
                'status': instance.status,
                'transaction_id': str(instance.transaction_id),
            },
        )
        flag_fast_bets(instance.user)
        return

    original_status = getattr(instance, '_original_status', instance.status)
    if instance.status == original_status:
        return

    AuditLog.objects.create(
        event_type='bet.status_changed',
        payload={
            'bet_id': instance.id,
            'old_status': original_status,
            'new_status': instance.status,
            'transaction_id': str(instance.transaction_id),
        },
    )
