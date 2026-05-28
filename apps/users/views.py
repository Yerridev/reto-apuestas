from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.users.serializers import (
    DepositLimitSerializer,
    RegisterSerializer,
    SelfExclusionSerializer,
    UserDetailSerializer,
    VerifyAccountSerializer,
)


#class RegisterThrottle(AnonRateThrottle):
#   scope = 'auth_register'


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    #throttle_classes = [RegisterThrottle]


class MeView(generics.RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UpdateLimitsView(generics.CreateAPIView):
    serializer_class = DepositLimitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UserDetailSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


class SelfExclusionView(generics.CreateAPIView):
    serializer_class = SelfExclusionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        exclusion = serializer.save()
        return Response(
            {'detail': 'Autoexclusion registrada.', 'exclusion_id': exclusion.id},
            status=status.HTTP_201_CREATED,
        )


class VerifyAccountView(generics.CreateAPIView):
    serializer_class = VerifyAccountSerializer
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'detail': 'Cuenta verificada correctamente.',
                'user_id': user.id,
                'account_status': user.account_status,
            },
            status=status.HTTP_200_OK,
        )
