import uuid

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.betting.choices import BetStatus
from apps.betting.models import Bet, Event, Market, Selection
from apps.betting.serializers import BetCreateSerializer, BetSerializer, EventSettleSerializer
from apps.users.choices import AccountStatus
from apps.wallet.services import SaldoInsuficiente, reserve_for_bet, settle_loss, settle_win


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
            return Response(BetSerializer(existing_bet).data, status=status.HTTP_200_OK)

        selection = serializer.validated_data['selection']
        stake = serializer.validated_data['stake']

        try:
            with transaction.atomic():
                selection = Selection.objects.select_for_update().select_related('market__event').get(pk=selection.pk)
                validation = BetCreateSerializer(data={'selection': selection.pk, 'stake': stake})
                validation.is_valid(raise_exception=True)

                reserve_for_bet(request.user, stake, transaction_id=transaction_id)
                bet = Bet.objects.create(
                    user=request.user,
                    market=selection.market,
                    selection=selection,
                    stake=stake,
                    odds=selection.odds,
                    transaction_id=transaction_id,
                )
        except SaldoInsuficiente as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(BetSerializer(bet).data, status=status.HTTP_201_CREATED)


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

        return Response(
            {
                'event': event.id,
                'result': serializer.validated_data['result'],
                'settled_won': settled_won,
                'settled_lost': settled_lost,
            }
        )
