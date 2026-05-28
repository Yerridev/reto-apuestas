from django.urls import path

from apps.wallet.views import BalanceView, DepositView, WithdrawView

urlpatterns = [
    path('deposit/', DepositView.as_view(), name='wallet-deposit'),
    path('withdraw/', WithdrawView.as_view(), name='wallet-withdraw'),
    path('balance/', BalanceView.as_view(), name='wallet-balance'),
]
