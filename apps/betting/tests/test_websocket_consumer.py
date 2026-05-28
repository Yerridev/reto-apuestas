"""
Tests del consumer WebSocket OddsConsumer (Paso C).

Cubre:
- Conexión y desconexión básica
- Ping → pong
- Recepción de odds_update desde el grupo del canal
- Payload malformado no rompe la conexión
- Múltiples clientes en el mismo evento reciben el broadcast
- Cliente en evento distinto NO recibe el broadcast
"""
import json
from decimal import Decimal

import pytest
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.utils import timezone

from apps.betting.consumers import OddsConsumer, broadcast_odds_update
from apps.betting.models import Event, Market, Selection
from config.asgi import application


# ── helpers ───────────────────────────────────────────────────────────────────


async def make_communicator(event_id: int) -> WebsocketCommunicator:
    communicator = WebsocketCommunicator(
        application,
        f'/ws/odds/event/{event_id}/',
    )
    connected, _ = await communicator.connect()
    assert connected, f'No se pudo conectar al WS para evento {event_id}'
    return communicator


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def evento(db):
    event = Event.objects.create(
        name='WS Test Event',
        sport='futbol',
        status=Event.Status.EN_VIVO,
        starts_at=timezone.now() - timezone.timedelta(minutes=5),
    )
    market = Market.objects.create(
        event=event, name='Resultado', market_type=Market.Type.UNO_X_DOS,
    )
    Selection.objects.create(market=market, name='local', odds=Decimal('2.1000'))
    Selection.objects.create(market=market, name='empate', odds=Decimal('3.4000'))
    Selection.objects.create(market=market, name='visitante', odds=Decimal('3.8000'))
    return event


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_conecta_y_desconecta(evento):
    """El consumer acepta la conexión y cierra limpio."""
    communicator = await make_communicator(evento.id)
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ping_retorna_pong(evento):
    """Enviar {type: ping} → recibir {type: pong}."""
    communicator = await make_communicator(evento.id)

    await communicator.send_json_to({'type': 'ping'})
    response = await communicator.receive_json_from()

    assert response == {'type': 'pong'}
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_recibe_odds_update_broadcast(evento):
    """
    Al hacer broadcast_odds_update, el cliente conectado al evento
    recibe el mensaje con type='odds_update'.
    """
    communicator = await make_communicator(evento.id)

    selections_payload = [
        {'id': 1, 'name': 'local', 'odds': '2.3000'},
        {'id': 2, 'name': 'empate', 'odds': '3.1000'},
        {'id': 3, 'name': 'visitante', 'odds': '4.0000'},
    ]
    await broadcast_odds_update(evento.id, selections_payload)

    message = await communicator.receive_json_from(timeout=3)

    assert message['type'] == 'odds_update'
    assert message['event_id'] == evento.id
    assert message['selections'] == selections_payload

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_payload_malformado_no_cierra_conexion(evento):
    """Texto que no es JSON válido no debe cerrar la conexión."""
    communicator = await make_communicator(evento.id)

    await communicator.send_to(text_data='esto no es json{{{')

    # La conexión sigue viva — confirmamos con un ping
    await communicator.send_json_to({'type': 'ping'})
    response = await communicator.receive_json_from(timeout=3)
    assert response['type'] == 'pong'

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_multiples_clientes_mismo_evento_reciben_broadcast(evento):
    """Dos clientes conectados al mismo evento reciben el mismo broadcast."""
    c1 = await make_communicator(evento.id)
    c2 = await make_communicator(evento.id)

    payload = [{'id': 1, 'name': 'local', 'odds': '1.9000'}]
    await broadcast_odds_update(evento.id, payload)

    msg1 = await c1.receive_json_from(timeout=3)
    msg2 = await c2.receive_json_from(timeout=3)

    assert msg1['type'] == 'odds_update'
    assert msg2['type'] == 'odds_update'
    assert msg1['selections'] == payload
    assert msg2['selections'] == payload

    await c1.disconnect()
    await c2.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_cliente_otro_evento_no_recibe_broadcast(evento, db):
    """Un cliente conectado a otro evento no recibe el broadcast."""
    otro_evento = await Event.objects.acreate(
        name='Otro evento WS',
        sport='futbol',
        status=Event.Status.EN_VIVO,
        starts_at=timezone.now() - timezone.timedelta(minutes=2),
    )

    c_target = await make_communicator(evento.id)
    c_other = await make_communicator(otro_evento.id)

    payload = [{'id': 1, 'name': 'local', 'odds': '2.0000'}]
    await broadcast_odds_update(evento.id, payload)

    # c_target debe recibir
    msg = await c_target.receive_json_from(timeout=3)
    assert msg['type'] == 'odds_update'

    # c_other no debe recibir nada
    assert await c_other.receive_nothing(timeout=1)

    await c_target.disconnect()
    await c_other.disconnect()
