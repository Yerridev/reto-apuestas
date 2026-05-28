from django.urls import path

from apps.audit.views import AuditVerifyView

urlpatterns = [
    path('audit/verify/', AuditVerifyView.as_view(), name='audit-verify'),
]
