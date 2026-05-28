from django.urls import path

from apps.betting import views

urlpatterns = [
    path('bets/', views.BetCreateView.as_view(), name='bet-create'),
    path('events/<int:pk>/settle/', views.EventSettleView.as_view(), name='event-settle'),
]
