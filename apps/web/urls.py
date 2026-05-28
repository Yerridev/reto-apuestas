from django.urls import path

from apps.web import views

urlpatterns = [
    path('', views.home, name='web-home'),
    path('login/', views.login_view, name='web-login'),
    path('logout/', views.logout_view, name='web-logout'),
    path('register/', views.register_view, name='web-register'),
    path('bet/<int:selection_id>/', views.bet_view, name='web-bet'),
    path('wallet/', views.wallet_view, name='web-wallet'),
    path('historial/', views.historial_view, name='web-historial'),
    path('dashboard/', views.dashboard_view, name='web-dashboard'),
    path('perfil/', views.perfil_view, name='web-perfil'),
]
