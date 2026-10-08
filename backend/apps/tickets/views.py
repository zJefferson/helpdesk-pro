from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.filters import StableOrderingFilter
from apps.core.permissions import IsTechnicianOrAdmin

from . import selectors, services
from .filters import TicketFilter, TicketSearchFilter
from .models import Ticket
from .permissions import TicketPermission
from .serializers import (
    AssignSerializer,
    CommentSerializer,
    StatusChangeSerializer,
    TicketHistorySerializer,
    TicketSerializer,
)


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

    # Filtros, busca e ordenação da listagem (?status=..., ?search=..., ?ordering=...).
    filter_backends = [DjangoFilterBackend, TicketSearchFilter, StableOrderingFilter]
    filterset_class = TicketFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "priority", "status", "id"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return selectors.visible_tickets(self.request.user)

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

    @extend_schema(methods=["get"], responses=CommentSerializer(many=True))
    @extend_schema(methods=["post"], request=CommentSerializer, responses={201: CommentSerializer})
    @action(detail=True, methods=["get", "post"], pagination_class=None)
    def comments(self, request, pk=None):
        """Lista (sem notas internas para o solicitante) ou adiciona comentários."""
        ticket = self.get_object()

        if request.method == "GET":
            comments = selectors.visible_comments(request.user, ticket)
            return Response(CommentSerializer(comments, many=True).data)

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.add_comment(ticket, author=request.user, **serializer.validated_data)
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=TicketHistorySerializer(many=True))
    @action(detail=True, pagination_class=None)
    def history(self, request, pk=None):
        """Histórico de alterações do chamado, do mais antigo para o mais recente."""
        ticket = self.get_object()
        entries = selectors.ticket_history(ticket)
        return Response(TicketHistorySerializer(entries, many=True).data)
