from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.betting.models import Bet, Event, Market, Selection


class BetCreateSerializer(serializers.Serializer):
    selection = serializers.PrimaryKeyRelatedField(queryset=Selection.objects.select_related('market__event'))
    stake = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal('0.0001'))

    def validate_selection(self, selection):
        market = selection.market
        event = market.event

        if event.status != Event.Status.PROGRAMADO:
            raise serializers.ValidationError('El evento no esta programado para recibir apuestas.')
        if event.starts_at <= timezone.now():
            raise serializers.ValidationError('El evento ya inicio.')
        if market.status != Market.Status.ABIERTO:
            raise serializers.ValidationError('El mercado no esta abierto.')

        return selection


class BetSerializer(serializers.ModelSerializer):
    selection = serializers.PrimaryKeyRelatedField(read_only=True)
    market = serializers.PrimaryKeyRelatedField(read_only=True)
    transaction_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Bet
        fields = [
            'id',
            'market',
            'selection',
            'stake',
            'odds',
            'status',
            'transaction_id',
            'created_at',
        ]
        read_only_fields = fields


class EventSettleSerializer(serializers.Serializer):
    RESULT_GANA_LOCAL = 'gana_local'
    RESULT_EMPATE = 'empate'
    RESULT_GANA_VISITANTE = 'gana_visitante'

    RESULT_TO_SELECTION = {
        RESULT_GANA_LOCAL: 'local',
        RESULT_EMPATE: 'empate',
        RESULT_GANA_VISITANTE: 'visitante',
    }

    result = serializers.ChoiceField(
        choices=[
            (RESULT_GANA_LOCAL, 'Gana local'),
            (RESULT_EMPATE, 'Empate'),
            (RESULT_GANA_VISITANTE, 'Gana visitante'),
        ]
    )

    @property
    def winning_selection_name(self):
        return self.RESULT_TO_SELECTION[self.validated_data['result']]
