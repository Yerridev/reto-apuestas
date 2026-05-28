from django.urls import path

from apps.users import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('limits/', views.UpdateLimitsView.as_view(), name='auth-limits'),
    path('self-exclusion/', views.SelfExclusionView.as_view(), name='auth-self-exclusion'),
    path('verify-account/', views.VerifyAccountView.as_view(), name='auth-verify-account'),
]
