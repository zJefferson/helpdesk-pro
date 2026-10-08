from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .selectors import dashboard_summary
from .serializers import DashboardSummarySerializer


class DashboardSummaryView(APIView):
    """Indicadores calculados sobre os chamados visíveis ao usuário logado."""

    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request):
        return Response(DashboardSummarySerializer(dashboard_summary(request.user)).data)
