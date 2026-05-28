from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.betting.models import AccumulatedBet, AccumulatedBetLeg, Bet, Event, Market, Selection
from apps.users.choices import AccountStatus


class AccumulatedBetLegSerializer(serializers.ModelSerializer):
    selection_name = serializers.CharField(source='selection.name', read_only=True)
    event_name = serializers.CharField(source='market.event.name', read_only=True)

    class Meta:
        model = AccumulatedBetLeg
        fields = ['id', 'selection', 'selection_name', 'market', 'event_name', 'odds_at_bet', 'settled', 'won']


class AccumulatedBetSerializer(serializers.ModelSerializer):
    legs = AccumulatedBetLegSerializer(many=True, read_only=True)
    combined_odds = serializers.DecimalField(max_digits=18, decimal_places=4, read_only=True)
    transaction_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = AccumulatedBet
        fields = ['id', 'stake', 'combined_odds', 'status', 'transaction_id', 'created_at', 'legs']


class AccumulatedBetCreateSerializer(serializers.Serializer):
    selections = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Selection.objects.select_related('market__event')),
        min_length=2,
    )
    stake = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal('0.0001'))

    def validate_selections(self, selections):
        seen_markets = {}
        for sel in selections:
            market = sel.market
            if market.id in seen_markets:
                raise serializers.ValidationError(
                    f'No puedes combinar dos selecciones del mismo mercado ({market.name}).'
                )
            seen_markets[market.id] = sel

            # Permitir PROGRAMADO o EN_VIVO
            if market.event.status not in [Event.Status.PROGRAMADO, Event.Status.EN_VIVO]:
                raise serializers.ValidationError(f'El evento "{market.event.name}" no está disponible para apuestas.')
            
            # Para PROGRAMADO: no puede haber iniciado
            if market.event.status == Event.Status.PROGRAMADO and market.event.starts_at <= timezone.now():
                raise serializers.ValidationError(f'El evento "{market.event.name}" ya inició.')
            
            # Para EN_VIVO: se permite aunque haya iniciado
            
            if market.status != Market.Status.ABIERTO:
                raise serializers.ValidationError(f'El mercado "{market.name}" no está abierto.')

        return selections

    def validate_stake(self, stake):
        if stake > settings.MAX_BET_STAKE:
            raise serializers.ValidationError('El monto supera el limite maximo por apuesta.')
        return stake

    def validate(self, data):
        user = self.context['request'].user
        if user.account_status != AccountStatus.VERIFICADO:
            raise serializers.ValidationError('Tu cuenta debe estar verificada para apostar.')
        return data


class BetCreateSerializer(serializers.Serializer):
    selection = serializers.PrimaryKeyRelatedField(queryset=Selection.objects.select_related('market__event'))
    stake = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal('0.0001'))

    def validate_selection(self, selection):
        market = selection.market
        event = market.event

        # Permitir PROGRAMADO o EN_VIVO
        if event.status not in [Event.Status.PROGRAMADO, Event.Status.EN_VIVO]:
            raise serializers.ValidationError('El evento no está disponible para apuestas.')
        
        # Para PROGRAMADO: no puede haber iniciado
        if event.status == Event.Status.PROGRAMADO and event.starts_at <= timezone.now():
            raise serializers.ValidationError('El evento ya inició.')
        
        # Para EN_VIVO: se permite aunque haya iniciado (es el punto de las apuestas en vivo)
        
        if market.status != Market.Status.ABIERTO:
            raise serializers.ValidationError('El mercado no está abierto.')

        return selection

    def validate_stake(self, stake):
        if stake > settings.MAX_BET_STAKE:
            raise serializers.ValidationError('El monto supera el límite máximo por apuesta.')
        return stake


class CashoutSerializer(serializers.Serializer):
    odds_actual = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal('0.0001'))


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
