from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallet.serializers import BalanceSerializer, DepositSerializer, WithdrawSerializer
from apps.wallet.services import SaldoInsuficiente, deposit, get_balance, get_or_create_wallet, withdraw


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


class WithdrawView(APIView):
    """
    POST /api/wallet/withdraw/
    Retira fichas virtuales del wallet del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        idempotency_key = serializer.validated_data.get('idempotency_key')
        if not idempotency_key:
            idempotency_key = request.headers.get('Idempotency-Key') or None

        try:
            transaction_id = withdraw(request.user, amount, transaction_id=idempotency_key)
        except (SaldoInsuficiente, ValueError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        balance = get_balance(request.user)
        return Response(
            {
                'transaction_id': str(transaction_id),
                'amount': str(amount),
                'balance': str(balance),
                'message': 'Retiro virtual realizado correctamente.',
            },
            status=status.HTTP_201_CREATED,
        )
