import json
from decimal import Decimal

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.betting.models import Event, Selection


class OddsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer para actualizaciones de cuotas en tiempo real.
    
    Clientes se conectan a: ws://host/ws/odds/event/{event_id}/
    Reciben updates cuando las cuotas de un evento cambian.
    """

    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.room_group_name = f'odds-event-{self.event_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Recibe pings del cliente (para mantener la conexión viva).
        En producción, podrías validar que el usuario esté autorizado aquí.
        """
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def odds_update(self, event):
        """
        Manejador que recibe updates del grupo y los envía al cliente.
        Llamado cuando se hace broadcast('odds_update', {...}) en el grupo.
        """
        await self.send(text_data=json.dumps({
            'type': 'odds_update',
            'event_id': event['event_id'],
            'selections': event['selections'],
        }))


async def broadcast_odds_update(event_id, selections):
    """
    Utility para hacer broadcast de actualización de cuotas.
    Llamar desde las views cuando se actualicen cuotas.
    
    Args:
        event_id: ID del evento
        selections: List de dicts con {id, name, odds}
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    room_group_name = f'odds-event-{event_id}'

    await channel_layer.group_send(
        room_group_name,
        {
            'type': 'odds.update',
            'event_id': event_id,
            'selections': selections,
        },
    )
