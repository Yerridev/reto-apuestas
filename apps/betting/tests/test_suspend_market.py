"""
Tests para suspensión automática de mercado in-play.

Cubre:
- Admin puede suspender un mercado abierto
- El mercado queda en estado SUSPENDIDO
- Se rechaza apostar en mercado suspendido
- No se puede suspender un mercado liquidado
- Usuario normal no puede suspender
- Evento 404 si market_id no corresponde al evento
- reopen_market_task reabre el mercado correctamente
- reopen_market_task no hace nada si el mercado ya no está SUSPENDIDO
"""
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.betting.models import Event, Market, Selection
from apps.betting.tasks import reopen_market_task
from apps.users.choices import AccountStatus
from apps.wallet.services import deposit, get_or_create_wallet

User = get_user_model()


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def admin(db):
    u = User.objects.create_user(
        email='admin-suspend@fairbet.pe', password='Test1234!',
        dni='102687740', first_name='Admin', last_name='S',
        birth_date='1990-01-01', account_status=AccountStatus.VERIFICADO,
        is_staff=True, is_superuser=True,
    )
    return u


@pytest.fixture
def usuario(db):
    u = User.objects.create_user(
        email='user-suspend@fairbet.pe', password='Test1234!',
        dni='123456781', first_name='User', last_name='S',
        birth_date='1995-01-01', account_status=AccountStatus.VERIFICADO,
    )
    get_or_create_wallet(u)
    deposit(u, Decimal('200.0000'))
    return u


@pytest.fixture
def evento_en_vivo(db):
    event = Event.objects.create(
        name='Partido en vivo',
        sport='futbol',
        status=Event.Status.EN_VIVO,
        starts_at=timezone.now() - timezone.timedelta(minutes=10),
    )
    market = Market.objects.create(
        event=event, name='Resultado', market_type=Market.Type.UNO_X_DOS,
    )
    Selection.objects.create(market=market, name='local', odds=Decimal('2.1000'))
    Selection.objects.create(market=market, name='empate', odds=Decimal('3.4000'))
    Selection.objects.create(market=market, name='visitante', odds=Decimal('3.8000'))
    return event, market


def auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── Paso A: suspensión de mercado ─────────────────────────────────────────────


@pytest.mark.django_db
def test_admin_suspende_mercado_abierto(admin, evento_en_vivo):
    """Admin puede suspender un mercado abierto; Celery queda encolado."""
    event, market = evento_en_vivo
    url = reverse('event-suspend-market', kwargs={'event_id': event.id})

    with patch('apps.betting.views.reopen_market_task.apply_async') as mock_task:
        response = auth(admin).post(url, {
            'market_id': market.id,
            'duration_seconds': 30,
        }, format='json')

    assert response.status_code == 200
    assert response.data['status'] == Market.Status.SUSPENDIDO
    assert response.data['reopen_in_seconds'] == 30

    market.refresh_from_db()
    assert market.status == Market.Status.SUSPENDIDO

    mock_task.assert_called_once_with(args=[market.id], countdown=30)


@pytest.mark.django_db
def test_admin_suspende_usa_duracion_default(admin, evento_en_vivo):
    """Sin duration_seconds, se usa el default (30s)."""
    event, market = evento_en_vivo
    url = reverse('event-suspend-market', kwargs={'event_id': event.id})

    with patch('apps.betting.views.reopen_market_task.apply_async'):
        response = auth(admin).post(url, {'market_id': market.id}, format='json')

    assert response.status_code == 200
    assert response.data['reopen_in_seconds'] == 30


@pytest.mark.django_db
def test_usuario_normal_no_puede_suspender(usuario, evento_en_vivo):
    """Usuario sin permisos de staff recibe 403."""
    event, market = evento_en_vivo
    url = reverse('event-suspend-market', kwargs={'event_id': event.id})

    response = auth(usuario).post(url, {'market_id': market.id}, format='json')

    assert response.status_code == 403
    market.refresh_from_db()
    assert market.status == Market.Status.ABIERTO


@pytest.mark.django_db
def test_no_se_puede_suspender_mercado_liquidado(admin, evento_en_vivo):
    """Un mercado ya liquidado no puede suspenderse."""
    event, market = evento_en_vivo
    market.status = Market.Status.LIQUIDADO
    market.save(update_fields=['status'])

    url = reverse('event-suspend-market', kwargs={'event_id': event.id})
    response = auth(admin).post(url, {'market_id': market.id}, format='json')

    assert response.status_code == 400
    assert 'liquidado' in response.data['detail'].lower()


@pytest.mark.django_db
def test_market_id_no_pertenece_al_evento(admin, evento_en_vivo):
    """market_id de otro evento retorna 404."""
    event, market = evento_en_vivo

    otro_evento = Event.objects.create(
        name='Otro partido', sport='futbol',
        starts_at=timezone.now() + timezone.timedelta(days=1),
    )
    otro_market = Market.objects.create(
        event=otro_evento, name='Resultado', market_type=Market.Type.UNO_X_DOS,
    )

    url = reverse('event-suspend-market', kwargs={'event_id': event.id})
    response = auth(admin).post(url, {'market_id': otro_market.id}, format='json')

    assert response.status_code == 404


@pytest.mark.django_db
def test_apuesta_rechazada_en_mercado_suspendido(usuario, evento_en_vivo):
    """Apostar en mercado suspendido retorna 400."""
    event, market = evento_en_vivo
    market.status = Market.Status.SUSPENDIDO
    market.save(update_fields=['status'])

    selection = market.selections.get(name='local')
    response = auth(usuario).post(reverse('bet-create'), {
        'selection': selection.id,
        'stake': '20.0000',
    }, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert response.status_code == 400


@pytest.mark.django_db
def test_duration_seconds_invalido(admin, evento_en_vivo):
    """duration_seconds negativo o cero retorna 400."""
    event, market = evento_en_vivo
    url = reverse('event-suspend-market', kwargs={'event_id': event.id})

    for bad_val in [0, -5, 'abc']:
        response = auth(admin).post(url, {
            'market_id': market.id,
            'duration_seconds': bad_val,
        }, format='json')
        assert response.status_code == 400, f'Esperaba 400 con duration={bad_val}'


# ── Task reopen_market_task ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_reopen_market_task_reabre_mercado_suspendido(evento_en_vivo):
    """El task cambia SUSPENDIDO → ABIERTO."""
    event, market = evento_en_vivo
    market.status = Market.Status.SUSPENDIDO
    market.save(update_fields=['status'])

    reopen_market_task(market.id)

    market.refresh_from_db()
    assert market.status == Market.Status.ABIERTO


@pytest.mark.django_db
def test_reopen_market_task_no_toca_mercado_abierto(evento_en_vivo):
    """Si el mercado ya fue reabierto manualmente, el task no hace nada dañino."""
    event, market = evento_en_vivo
    assert market.status == Market.Status.ABIERTO

    reopen_market_task(market.id)

    market.refresh_from_db()
    assert market.status == Market.Status.ABIERTO


@pytest.mark.django_db
def test_reopen_market_task_market_inexistente_no_explota():
    """market_id que no existe no lanza excepción no manejada."""
    reopen_market_task(99999)  # solo loguea warning, no crash
