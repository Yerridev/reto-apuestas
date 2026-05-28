import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def reopen_market_task(self, market_id: int):
    """
    Reabre un mercado suspendido (vuelve a ABIERTO).
    Se programa con un countdown desde SuspendMarketView.
    """
    from apps.betting.models import Market

    try:
        with transaction.atomic():
            market = Market.objects.select_for_update().get(pk=market_id)
            if market.status == Market.Status.SUSPENDIDO:
                market.status = Market.Status.ABIERTO
                market.save(update_fields=['status'])
                logger.info('market_reopened', extra={'market_id': market_id})
            else:
                logger.info(
                    'market_reopen_skipped',
                    extra={'market_id': market_id, 'status': market.status},
                )
    except Market.DoesNotExist:
        logger.warning('market_reopen_not_found', extra={'market_id': market_id})
    except Exception as exc:
        logger.error('market_reopen_error', extra={'market_id': market_id, 'error': str(exc)})
        raise self.retry(exc=exc)
