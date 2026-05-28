from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from apps.audit.models import SuspiciousActivity
from apps.audit.serializers import SuspiciousActivitySerializer
from apps.audit.services import dashboard_metrics, verify_chain


class AuditVerifyView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Permite a un admin verificar la integridad completa de la hash chain."""
        return Response(verify_chain())


class SuspiciousActivityListView(ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = SuspiciousActivitySerializer
    queryset = SuspiciousActivity.objects.select_related('user').order_by('-created_at')


class DashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(dashboard_metrics())
