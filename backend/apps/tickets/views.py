from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from . import services
from .models import Ticket
from .permissions import TicketPermission
from .selectors import visible_tickets
from .serializers import TicketSerializer


class TicketViewSet(viewsets.ModelViewSet):
    """
    Chamados visíveis ao usuário logado.

    - Solicitante: só os próprios; chamado alheio retorna 404.
    - Técnico e administrador: todos.
    - Edição: conforme `permissions.editable_fields`. Não há DELETE.
    """

    serializer_class = TicketSerializer
    queryset = Ticket.objects.none()  # só para a documentação; o real vem de get_queryset()
    permission_classes = [IsAuthenticated, TicketPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return visible_tickets(self.request.user)

    def perform_create(self, serializer):
        serializer.instance = services.create_ticket(
            actor=self.request.user, **serializer.validated_data
        )

    def perform_update(self, serializer):
        serializer.instance = services.update_ticket(
            serializer.instance, actor=self.request.user, data=serializer.validated_data
        )
