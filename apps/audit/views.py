from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import verify_chain


class AuditVerifyView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Permite a un admin verificar la integridad completa de la hash chain."""
        return Response(verify_chain())
