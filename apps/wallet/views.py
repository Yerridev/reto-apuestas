from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallet.serializers import BalanceSerializer, DepositSerializer
from apps.wallet.services import deposit, get_balance, get_or_create_wallet


class DepositView(APIView):
    """
    POST /api/wallet/deposit/
    Recarga fichas virtuales al wallet del usuario autenticado.
    Acepta Idempotency-Key en el header para evitar depósitos duplicados.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        idempotency_key = serializer.validated_data.get('idempotency_key')

        # También se puede pasar el idempotency key por header
        if not idempotency_key:
            idempotency_key = request.headers.get('Idempotency-Key') or None

        get_or_create_wallet(request.user)
        transaction_id = deposit(request.user, amount, transaction_id=idempotency_key)

        balance = get_balance(request.user)
        return Response(
            {
                'transaction_id': str(transaction_id),
                'amount': str(amount),
                'balance': str(balance),
                'message': 'Fichas acreditadas correctamente.',
            },
            status=status.HTTP_201_CREATED,
        )


class BalanceView(APIView):
    """
    GET /api/wallet/balance/
    Retorna el saldo actual del wallet del usuario autenticado.
    El saldo se calcula en tiempo real desde las entradas del ledger.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_or_create_wallet(request.user)
        balance = get_balance(request.user)
        serializer = BalanceSerializer({'balance': balance, 'currency': 'fichas'})
        return Response(serializer.data)
