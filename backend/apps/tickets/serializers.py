from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import UserSummarySerializer
from apps.core.serializers import RejectReadOnlyFieldsMixin

from . import services
from .models import Category, Comment, Status, Ticket, TicketHistory


class TicketPermissionsSerializer(serializers.Serializer):
    """Ações que o usuário logado pode executar no chamado (só para a interface)."""

    editable_fields = serializers.ListField(child=serializers.CharField())
    status_transitions = serializers.ListField(child=serializers.ChoiceField(Status.choices))
    can_assign = serializers.BooleanField()
    can_take = serializers.BooleanField()
    can_comment = serializers.BooleanField()
    can_comment_internal = serializers.BooleanField()


class TicketSerializer(RejectReadOnlyFieldsMixin, serializers.ModelSerializer):
    """
    Entrada/saída de chamados. Campos read-only (status, solicitante, responsável, datas)
    são definidos pelo backend; enviá-los gera 400.
    """

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    requester = UserSummarySerializer(read_only=True)
    assignee = UserSummarySerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_name",
            "priority",
            "status",
            "requester",
            "assignee",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
            "permissions",
        ]
        read_only_fields = ["status", "created_at", "updated_at", "resolved_at", "closed_at"]

    @extend_schema_field(TicketPermissionsSerializer)
    def get_permissions(self, ticket):
        # Só faz sentido para quem está logado; sem request (ex.: testes de unidade) fica vazio.
        request = self.context.get("request")
        if request is None:
            return None
        return services.available_actions(request.user, ticket)

    def validate_category(self, category):
        # RN05: só categorias ativas podem ser escolhidas.
        if not category.is_active:
            raise serializers.ValidationError("Esta categoria está inativa.")
        return category


class AssignSerializer(serializers.Serializer):
    """Entrada de POST /tickets/{id}/assign/. Só aceita técnicos ativos (RN08)."""

    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.TECHNICIAN, is_active=True),
        error_messages={"does_not_exist": "Informe o id de um técnico ativo."},
    )


class StatusChangeSerializer(serializers.Serializer):
    """Entrada de POST /tickets/{id}/status/. A transição é validada em services.py."""

    status = serializers.ChoiceField(choices=Status.choices)


class CommentSerializer(RejectReadOnlyFieldsMixin, serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)
    body = serializers.CharField(max_length=5000)  # vazio ou só espaços → 400

    class Meta:
        model = Comment
        fields = ["id", "author", "body", "is_internal", "created_at"]
        read_only_fields = ["created_at"]


class TicketHistorySerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = TicketHistory
        fields = [
            "id",
            "action",
            "action_display",
            "field",
            "old_value",
            "new_value",
            "actor",
            "created_at",
        ]
        read_only_fields = fields


class CategorySerializer(RejectReadOnlyFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "is_active"]


# --- Dashboard (somente saída; usado para validar o formato e documentar no Swagger) ---


class StatusCountSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Status.choices)
    label = serializers.CharField()
    count = serializers.IntegerField()


class PriorityCountSerializer(serializers.Serializer):
    priority = serializers.IntegerField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class CategoryCountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class DashboardSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    open = serializers.IntegerField(help_text="Abertos, em atendimento ou aguardando.")
    unassigned = serializers.IntegerField(help_text="Ativos sem técnico responsável.")
    assigned_to_me = serializers.IntegerField(help_text="Ativos atribuídos ao usuário logado.")
    resolved_last_30_days = serializers.IntegerField()
    avg_resolution_hours = serializers.FloatField(allow_null=True)
    by_status = StatusCountSerializer(many=True)
    by_priority = PriorityCountSerializer(many=True)
    open_by_category = CategoryCountSerializer(many=True)
