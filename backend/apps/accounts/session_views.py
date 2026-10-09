"""
Autenticação para o NAVEGADOR (frontend React).

Diferença para /auth/token/ (usado por Swagger, curl e outros clientes de API):
o refresh token NUNCA aparece no corpo da resposta. Ele vai num cookie:

- HttpOnly  → o JavaScript da página não consegue ler o cookie (um XSS não rouba o refresh);
- SameSite=Strict → o navegador não envia o cookie em requisições vindas de outros sites
  (proteção contra CSRF);
- Secure    → só trafega por HTTPS (ligado fora do modo DEBUG);
- Path      → o cookie só é enviado para /api/v1/auth/session/, e não para toda a API.

O access token (15 min) é devolvido no corpo e o frontend o guarda apenas EM MEMÓRIA.
"""

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer

COOKIE_PATH = "/api/v1/auth/session/"

AccessResponse = inline_serializer("SessionAccess", fields={"access": serializers.CharField()})


def _set_refresh_cookie(response, refresh):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Strict",
        path=COOKIE_PATH,
    )


def _delete_refresh_cookie(response):
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=COOKIE_PATH, samesite="Strict")


def _unauthorized(detail):
    response = Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)
    _delete_refresh_cookie(response)
    return response


class SessionAPIView(APIView):
    """Base dos endpoints de sessão: públicos, sem autenticação por cabeçalho."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request):
        # Sem isso, o DRF converte "credenciais inválidas" (401) em 403.
        return 'Bearer realm="api"'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Força a leitura do corpo mesmo em endpoints sem dados (refresh/logout): assim um
        # <form> enviado por outro site é recusado com 415 antes de qualquer efeito.
        request.data  # noqa: B018


class SessionLoginView(SessionAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: AccessResponse})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)  # credenciais erradas → 401
        tokens = serializer.validated_data
        response = Response({"access": tokens["access"]})
        _set_refresh_cookie(response, tokens["refresh"])
        return response


class SessionRefreshView(SessionAPIView):
    """Gera um novo access a partir do cookie. Também rotaciona o refresh (novo cookie)."""

    @extend_schema(
        request=None,
        responses={200: AccessResponse, 401: OpenApiResponse(description="Sessão expirada.")},
    )
    def post(self, request):
        refresh = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not refresh:
            return _unauthorized("Sessão não encontrada.")
        serializer = TokenRefreshSerializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError, AuthenticationFailed:  # expirado, na blacklist ou usuário inativo
            return _unauthorized("Sessão expirada. Faça login novamente.")
        response = Response({"access": serializer.validated_data["access"]})
        _set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response


class SessionLogoutView(SessionAPIView):
    """Invalida o refresh do cookie e apaga o cookie. Funciona mesmo com o access expirado."""

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        refresh = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass  # já inválido: basta apagar o cookie
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _delete_refresh_cookie(response)
        return response
