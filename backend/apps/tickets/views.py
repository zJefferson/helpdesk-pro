from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsTechnicianOrAdmin

from . import services
from .models import Ticket
from .permissions import TicketPermission
from .selectors import visible_tickets
from .serializers import AssignSerializer, StatusChangeSerializer, TicketSerializer


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

    def _reload(self, ticket):
        # Busca de novo com select_related: a resposta usa categoria, solicitante e
        # responsável, e assim tudo vem em 1 consulta em vez de várias.
        return self.get_queryset().get(pk=ticket.pk)

    def perform_create(self, serializer):
        ticket = services.create_ticket(actor=self.request.user, **serializer.validated_data)
        serializer.instance = self._reload(ticket)

    def perform_update(self, serializer):
        ticket = services.update_ticket(
            serializer.instance, actor=self.request.user, data=serializer.validated_data
        )
        serializer.instance = self._reload(ticket)

    @extend_schema(request=AssignSerializer, responses=TicketSerializer)
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsTechnicianOrAdmin, TicketPermission],
    )
    def assign(self, request, pk=None):
        """Atribui um técnico. Técnico só pode assumir para si um chamado sem responsável."""
        ticket = self.get_object()  # aplica visibilidade (404) e TicketPermission (403)
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.assign_ticket(
            ticket, actor=request.user, assignee=serializer.validated_data["assignee_id"]
        )
        return Response(TicketSerializer(self._reload(ticket)).data)

    @extend_schema(request=StatusChangeSerializer, responses=TicketSerializer)
    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, pk=None):
        """Muda o status seguindo a tabela de transições permitidas (RN09)."""
        ticket = self.get_object()
        serializer = StatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.change_status(
            ticket, actor=request.user, new_status=serializer.validated_data["status"]
        )
        return Response(TicketSerializer(self._reload(ticket)).data)
