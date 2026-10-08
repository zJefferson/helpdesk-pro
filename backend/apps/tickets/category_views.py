from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated

from apps.core.permissions import IsAdmin

from .models import Category
from .serializers import CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Leitura para todos os usuários logados; escrita só para administradores (RN19).
    Não há DELETE: categorias são desativadas (RN20). Só o admin vê as inativas.
    """

    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    pagination_class = None  # lista curta, usada em selects do formulário
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        queryset = Category.objects.order_by("name")
        if not self.request.user.is_admin:
            queryset = queryset.filter(is_active=True)
        return queryset
