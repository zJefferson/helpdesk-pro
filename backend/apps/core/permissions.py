"""
Permissões por perfil, reutilizáveis em qualquer view do DRF.

Lembrete: permissões SEMPRE no backend. O frontend esconder um botão é só conveniência;
quem garante a segurança é a API, mesmo quando acessada por curl ou Swagger.
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "Apenas administradores podem executar esta ação."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)
