from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import IsAdmin, IsTechnicianOrAdmin

from .models import Role, User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MeSerializer,
    UserSerializer,
    UserSummarySerializer,
)


class LoginView(TokenObtainPairView):
    """Recebe e-mail e senha e devolve os tokens `access` e `refresh`."""

    serializer_class = LoginSerializer

    # Limita tentativas por IP (ex.: 5/min) para dificultar ataques de força bruta.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    """Invalida o refresh token (blacklist). O access expira sozinho em poucos minutos."""

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """Consulta e edição (apenas nome) do usuário autenticado."""

    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(viewsets.ModelViewSet):
    """
    Gestão de usuários — somente administradores.

    Não há DELETE: usuários são desativados (`is_active=false`), nunca apagados (RN20).
    """

    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.order_by("first_name", "last_name", "id")
    http_method_names = ["get", "post", "patch", "head", "options"]

    @extend_schema(responses=UserSummarySerializer(many=True))
    @action(detail=False, permission_classes=[IsTechnicianOrAdmin], pagination_class=None)
    def technicians(self, request):
        """Técnicos ativos — usado para escolher o responsável de um chamado."""
        technicians = self.get_queryset().filter(role=Role.TECHNICIAN, is_active=True)
        return Response(UserSummarySerializer(technicians, many=True).data)
