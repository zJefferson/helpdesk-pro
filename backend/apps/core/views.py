import logging

from django.db import DatabaseError, connection
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Informa se a API está no ar e se consegue falar com o banco de dados.

    É público (sem login) porque é usado pelo Docker e pela plataforma de deploy
    para saber se a aplicação está saudável. Não expõe nenhum dado sensível.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: inline_serializer(
                "HealthCheck",
                fields={"status": serializers.CharField(), "database": serializers.CharField()},
            ),
            503: OpenApiResponse(description="Banco de dados indisponível."),
        }
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            logger.exception("Health check: falha ao conectar no banco de dados")
            return Response(
                {"status": "error", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})
