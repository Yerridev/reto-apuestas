from django.urls import path

from apps.betting import views

urlpatterns = [
    path('bets/', views.BetCreateView.as_view(), name='bet-create'),
    path('bets/<int:pk>/cashout/', views.BetCashoutView.as_view(), name='bet-cashout'),
    path('events/<int:pk>/settle/', views.EventSettleView.as_view(), name='event-settle'),
    path('events/<int:event_id>/odds/', views.EventOddsView.as_view(), name='event-odds'),
    path('events/<int:event_id>/suspend-market/', views.SuspendMarketView.as_view(), name='event-suspend-market'),
    path('accumulated/', views.AccumulatedBetCreateView.as_view(), name='accumulated-create'),
    path('accumulated/list/', views.AccumulatedBetListView.as_view(), name='accumulated-list'),
]
