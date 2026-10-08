from django.contrib import admin

from .models import Category, Comment, Ticket, TicketHistory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "body", "is_internal", "created_at")
    readonly_fields = ("created_at",)


class TicketHistoryInline(admin.TabularInline):
    """O histórico é imutável (RN17): no admin ele aparece apenas para leitura."""

    model = TicketHistory
    extra = 0
    fields = ("created_at", "actor", "action", "field", "old_value", "new_value")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "category", "requester", "assignee")
    list_filter = ("status", "priority", "category")
    search_fields = ("=id", "title", "description")  # "=id": busca exata pelo número
    list_select_related = ("category", "requester", "assignee")
    raw_id_fields = ("requester",)
    readonly_fields = ("created_at", "updated_at", "resolved_at", "closed_at")
    inlines = [CommentInline, TicketHistoryInline]


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "action", "field", "actor", "created_at")
    list_filter = ("action",)
    list_select_related = ("ticket", "actor")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
