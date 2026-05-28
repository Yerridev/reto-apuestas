import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.betting.choices import BetStatus
from apps.betting.models import AccumulatedBet, Bet, Event, Market, Selection
from apps.betting.serializers import (
    AccumulatedBetCreateSerializer,
    AccumulatedBetSerializer,
    BetCreateSerializer,
    BetSerializer,
    CashoutSerializer,
    EventSettleSerializer,
)
from apps.betting.services import CashoutNoPermitido, cashout, place_accumulator, settle_accumulator_legs
from apps.betting.tasks import reopen_market_task
from apps.users.choices import AccountStatus
from apps.wallet.services import SaldoInsuficiente, reserve_for_bet, settle_loss, settle_win

RESPONSIBLE_GAMBLING_MESSAGE = (
    'Juega con responsabilidad. Si crees que tienes un problema, usa la opción de autoexclusión.'
)
PLATFORM_NOTICE = 'Plataforma educativa con moneda virtual. No constituye una casa de apuestas.'


def _bet_response_data(bet):
    data = BetSerializer(bet).data
    data['responsible_gambling_message'] = RESPONSIBLE_GAMBLING_MESSAGE
    data['platform_notice'] = PLATFORM_NOTICE
    return data


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class BetCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.account_status != AccountStatus.VERIFICADO:
            return Response(
                {'detail': 'Tu cuenta debe estar verificada y habilitada para apostar.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BetCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        idempotency_key = request.headers.get('Idempotency-Key')
        try:
            transaction_id = uuid.UUID(idempotency_key) if idempotency_key else uuid.uuid4()
        except ValueError:
            return Response(
                {'detail': 'Idempotency-Key debe ser un UUID valido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing_bet = Bet.objects.filter(transaction_id=transaction_id, user=request.user).first()
        if existing_bet:
            return Response(_bet_response_data(existing_bet), status=status.HTTP_200_OK)

        selection = serializer.validated_data['selection']
        stake = serializer.validated_data['stake']
        odds_expected = serializer.validated_data.get('odds_expected')

        try:
            with transaction.atomic():
                selection = Selection.objects.select_for_update().select_related('market__event').get(pk=selection.pk)
                validation = BetCreateSerializer(data={'selection': selection.pk, 'stake': stake})
                validation.is_valid(raise_exception=True)

                # Re-cotización: si el cliente envió odds_expected y las actuales difieren → 409
                if odds_expected is not None and selection.odds != odds_expected:
                    return Response(
                        {
                            'detail': 'Las cuotas han cambiado. Por favor, confirme con las nuevas cuotas.',
                            'odds_expected': str(odds_expected),
                            'odds_current': str(selection.odds),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                reserve_for_bet(request.user, stake, transaction_id=transaction_id)
                bet = Bet.objects.create(
                    user=request.user,
                    market=selection.market,
                    selection=selection,
                    stake=stake,
                    odds=selection.odds,
                    ip_address=_get_client_ip(request),
                    transaction_id=transaction_id,
                )
        except SaldoInsuficiente as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_bet_response_data(bet), status=status.HTTP_201_CREATED)


class BetCashoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = CashoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bet = get_object_or_404(Bet.objects.select_related('user', 'market'), pk=pk)
        if bet.user_id != request.user.id:
            return Response({'detail': 'La apuesta no pertenece al usuario autenticado.'}, status=status.HTTP_403_FORBIDDEN)

        idempotency_key = request.headers.get('Idempotency-Key')
        try:
            transaction_id = uuid.UUID(idempotency_key) if idempotency_key else uuid.uuid4()
        except ValueError:
            return Response({'detail': 'Idempotency-Key debe ser un UUID valido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cashout_value, balance = cashout(
                bet,
                serializer.validated_data['odds_actual'],
                transaction_id=transaction_id,
            )
        except (CashoutNoPermitido, ValueError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        bet.refresh_from_db()
        return Response(
            {
                'bet_id': bet.id,
                'cashout_value': str(cashout_value),
                'balance': str(balance),
                'status': bet.status,
            },
            status=status.HTTP_200_OK,
        )


class EventSettleView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        serializer = EventSettleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        winning_selection_name = serializer.winning_selection_name

        settled_won = 0
        settled_lost = 0

        try:
            with transaction.atomic():
                event = Event.objects.select_for_update().get(pk=pk)
                bets = (
                    Bet.objects.select_for_update()
                    .select_related('selection', 'user')
                    .filter(market__event=event, status=BetStatus.ACCEPTED)
                )

                for bet in bets:
                    settlement_tid = uuid.uuid5(uuid.NAMESPACE_URL, f'bet-settlement:{bet.transaction_id}')
                    if bet.selection.name == winning_selection_name:
                        settle_win(bet.user, bet.stake, bet.odds, transaction_id=settlement_tid)
                        bet.status = BetStatus.SETTLED_WON
                        settled_won += 1
                    else:
                        settle_loss(bet.user, bet.stake, transaction_id=settlement_tid)
                        bet.status = BetStatus.SETTLED_LOST
                        settled_lost += 1
                    bet.save(update_fields=['status'])

                Market.objects.filter(event=event).update(status=Market.Status.LIQUIDADO)
                event.status = Event.Status.FINALIZADO
                event.save(update_fields=['status'])
        except Event.DoesNotExist:
            return Response({'detail': 'Evento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        settle_accumulator_legs(event, winning_selection_name)

        return Response(
            {
                'event': event.id,
                'result': serializer.validated_data['result'],
                'settled_won': settled_won,
                'settled_lost': settled_lost,
            }
        )


class AccumulatedBetCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AccumulatedBetCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        idempotency_key = request.headers.get('Idempotency-Key')
        try:
            transaction_id = uuid.UUID(idempotency_key) if idempotency_key else uuid.uuid4()
        except ValueError:
            return Response(
                {'detail': 'Idempotency-Key debe ser un UUID valido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            acc = place_accumulator(
                request.user,
                [{'selection': s} for s in serializer.validated_data['selections']],
                serializer.validated_data['stake'],
                transaction_id=transaction_id,
            )
        except (SaldoInsuficiente, ValueError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AccumulatedBetSerializer(acc).data, status=status.HTTP_201_CREATED)


class AccumulatedBetListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accumulators = AccumulatedBet.objects.filter(user=request.user).prefetch_related(
            'legs__selection', 'legs__market__event',
        ).order_by('-created_at')
        return Response(AccumulatedBetSerializer(accumulators, many=True).data)


class SuspendMarketView(APIView):
    """
    POST /api/events/<event_id>/suspend-market/
    Body: { "market_id": <int>, "duration_seconds": <int> }

    Admin suspende un mercado in-play (gol, expulsión, etc.).
    Programa automáticamente su reapertura con Celery.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, event_id):
        market_id = request.data.get('market_id')
        duration = request.data.get('duration_seconds', 30)

        if not market_id:
            return Response(
                {'detail': 'market_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            duration = int(duration)
            if duration <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'detail': 'duration_seconds debe ser un entero positivo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                market = (
                    Market.objects
                    .select_for_update()
                    .get(pk=market_id, event_id=event_id)
                )
                if market.status not in (Market.Status.ABIERTO, Market.Status.SUSPENDIDO):
                    return Response(
                        {'detail': f'No se puede suspender un mercado en estado "{market.status}".'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                market.status = Market.Status.SUSPENDIDO
                market.save(update_fields=['status'])
        except Market.DoesNotExist:
            return Response(
                {'detail': 'Mercado no encontrado para este evento.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        reopen_market_task.apply_async(
            args=[market_id],
            countdown=duration,
        )

        return Response(
            {
                'market_id': market_id,
                'status': Market.Status.SUSPENDIDO,
                'reopen_in_seconds': duration,
            },
            status=status.HTTP_200_OK,
        )


class EventOddsView(APIView):
    """
    GET /api/events/{event_id}/odds/
    
    Retorna las cuotas actuales de un evento.
    Usado para polling como fallback del WebSocket.
    """
    permission_classes = []  # Público, sin autenticación

    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        
        markets = event.markets.all().prefetch_related('selections').values_list('id', 'name')
        selections_data = {}
        
        for market_id, market_name in markets:
            selections = Selection.objects.filter(market_id=market_id).values('id', 'name', 'odds')
            selections_data[market_id] = {
                'market_name': market_name,
                'selections': list(selections),
            }
        
        return Response({
            'event_id': event.id,
            'event_name': event.name,
            'status': event.status,
            'starts_at': event.starts_at,
            'markets': selections_data,
            'timestamp': __import__('django.utils.timezone', fromlist=['now']).now().isoformat(),
        }, status=status.HTTP_200_OK)

