"""
Quem pode ALTERAR um chamado, e quais campos (RN06 e RN11).

| Quem                               | Campos que pode editar                      |
|------------------------------------|---------------------------------------------|
| Administrador                      | título, descrição, categoria, prioridade    |
| Técnico responsável pelo chamado   | título, descrição, categoria, prioridade    |
| Solicitante dono, status = Aberto  | título, descrição, categoria                |
| Qualquer um, chamado fechado/canc. | nenhum                                      |

Status e responsável NÃO são editados por aqui: terão endpoints próprios em etapas futuras.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Status

FINAL_STATUSES = frozenset({Status.CLOSED, Status.CANCELLED})
STAFF_EDITABLE_FIELDS = frozenset({"title", "description", "category", "priority"})
REQUESTER_EDITABLE_FIELDS = frozenset({"title", "description", "category"})


def editable_fields(user, ticket):
    """Retorna o conjunto de campos que `user` pode alterar em `ticket` (vazio = nenhum)."""
    if ticket.status in FINAL_STATUSES:
        return frozenset()
    if user.is_admin:
        return STAFF_EDITABLE_FIELDS
    if user.is_technician and ticket.assignee_id == user.pk:
        return STAFF_EDITABLE_FIELDS
    if ticket.requester_id == user.pk and ticket.status == Status.OPEN:
        return REQUESTER_EDITABLE_FIELDS
    return frozenset()


class TicketPermission(BasePermission):
    """
    Permissão por objeto: leitura é liberada para quem enxerga o chamado
    (a visibilidade já foi aplicada no queryset); escrita depende de `editable_fields`.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.status in FINAL_STATUSES:
            self.message = "Chamados fechados ou cancelados não podem ser alterados."
            return False
        self.message = "Você não tem permissão para alterar este chamado."
        return bool(editable_fields(request.user, obj))
