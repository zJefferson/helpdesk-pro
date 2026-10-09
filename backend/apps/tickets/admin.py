from django.contrib import admin

from .models import Category, Comment, Ticket, TicketHistory


class ReadOnlyAdminMixin:
    """
    Somente consulta no Django Admin.

    Chamados, comentários e histórico só podem mudar pela API, que aplica as regras de
    negócio (transições de status, quem pode atribuir...) e grava o histórico. Editar pelo
    admin pularia essas regras; excluir um chamado apagaria junto todo o seu histórico.
    """

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


class CommentInline(ReadOnlyAdminMixin, admin.TabularInline):
    """Comentários são imutáveis (RN14)."""

    model = Comment
    extra = 0
    fields = ("created_at", "author", "is_internal", "body")
    readonly_fields = fields


class TicketHistoryInline(ReadOnlyAdminMixin, admin.TabularInline):
    """O histórico é imutável (RN17)."""

    model = TicketHistory
    extra = 0
    fields = ("created_at", "actor", "action", "field", "old_value", "new_value")
    readonly_fields = fields


@admin.register(Ticket)
class TicketAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "category", "requester", "assignee")
    list_filter = ("status", "priority", "category")
    search_fields = ("=id", "title", "description")  # "=id": busca exata pelo número
    list_select_related = ("category", "requester", "assignee")
    inlines = [CommentInline, TicketHistoryInline]


@admin.register(TicketHistory)
class TicketHistoryAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("ticket", "action", "field", "actor", "created_at")
    list_filter = ("action",)
    list_select_related = ("ticket", "actor")
