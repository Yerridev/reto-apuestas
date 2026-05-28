from django.urls import path

from apps.audit.views import AuditVerifyView, DashboardView, SuspiciousActivityListView

urlpatterns = [
    path('audit/verify/', AuditVerifyView.as_view(), name='audit-verify'),
    path('audit/suspicious/', SuspiciousActivityListView.as_view(), name='audit-suspicious'),
    path('dashboard/', DashboardView.as_view(), name='api-dashboard'),
]
