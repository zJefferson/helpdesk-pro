from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import UserSummarySerializer
from apps.core.serializers import RejectReadOnlyFieldsMixin

from .models import Category, Comment, Status, Ticket, TicketHistory


class TicketSerializer(RejectReadOnlyFieldsMixin, serializers.ModelSerializer):
    """
    Entrada/saída de chamados. Campos read-only (status, solicitante, responsável, datas)
    são definidos pelo backend; enviá-los gera 400.
    """

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    requester = UserSummarySerializer(read_only=True)
    assignee = UserSummarySerializer(read_only=True)

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
        ]
        read_only_fields = ["status", "created_at", "updated_at", "resolved_at", "closed_at"]

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
