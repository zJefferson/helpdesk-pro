from rest_framework import serializers

from apps.accounts.serializers import UserSummarySerializer
from apps.core.serializers import RejectReadOnlyFieldsMixin

from .models import Category, Ticket


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
