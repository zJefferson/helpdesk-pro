"""
Modelos do domínio de chamados.

Aqui ficam apenas a ESTRUTURA dos dados e validações simples de campo.
As regras de negócio (quem pode editar, transições de status, gravação do histórico)
serão implementadas em `services.py` nas próximas etapas.
"""

from django.conf import settings
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

from apps.accounts.models import Role


class Priority(models.IntegerChoices):
    # Inteiros (e não texto) para a ordenação funcionar: Crítica > Alta > Média > Baixa.
    LOW = 1, "Baixa"
    MEDIUM = 2, "Média"
    HIGH = 3, "Alta"
    CRITICAL = 4, "Crítica"


class Status(models.TextChoices):
    OPEN = "OPEN", "Aberto"
    IN_PROGRESS = "IN_PROGRESS", "Em atendimento"
    WAITING_REQUESTER = "WAITING_REQUESTER", "Aguardando solicitante"
    RESOLVED = "RESOLVED", "Resolvido"
    CLOSED = "CLOSED", "Fechado"
    CANCELLED = "CANCELLED", "Cancelado"


class HistoryAction(models.TextChoices):
    CREATED = "CREATED", "Criado"
    UPDATED = "UPDATED", "Atualizado"
    STATUS_CHANGED = "STATUS_CHANGED", "Status alterado"
    ASSIGNED = "ASSIGNED", "Atribuído"


class Category(models.Model):
    name = models.CharField("nome", max_length=80, unique=True)
    description = models.TextField("descrição", blank=True)
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    title = models.CharField("título", max_length=150, validators=[MinLengthValidator(5)])
    description = models.TextField(
        "descrição", validators=[MinLengthValidator(10), MaxLengthValidator(5000)]
    )
    # PROTECT: o banco recusa apagar uma categoria/usuário que ainda tenha chamados.
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="tickets", verbose_name="categoria"
    )
    priority = models.PositiveSmallIntegerField(
        "prioridade", choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.OPEN)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_tickets",
        verbose_name="solicitante",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tickets",
        verbose_name="responsável",
        null=True,
        blank=True,
        limit_choices_to={"role": Role.TECHNICIAN, "is_active": True},
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    resolved_at = models.DateTimeField("resolvido em", null=True, blank=True)
    closed_at = models.DateTimeField("fechado em", null=True, blank=True)

    class Meta:
        verbose_name = "chamado"
        verbose_name_plural = "chamados"
        ordering = ["-created_at"]
        # Índices nos campos mais usados em filtros e ordenações (RNF10).
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_at"]),
        ]
        # Obs.: `requester` e `assignee` (ForeignKeys) já ganham índice automaticamente.

    def __str__(self):
        return f"#{self.pk} {self.title}"


class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments", verbose_name="chamado"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="comments",
        verbose_name="autor",
    )
    body = models.TextField("texto", validators=[MaxLengthValidator(5000)])
    is_internal = models.BooleanField("nota interna", default=False)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "comentário"
        verbose_name_plural = "comentários"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comentário de {self.author} em #{self.ticket_id}"


class TicketHistory(models.Model):
    """Registro imutável de uma alteração em um chamado (quem, o quê, quando)."""

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="history", verbose_name="chamado"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_changes",
        verbose_name="autor da alteração",
    )
    action = models.CharField("ação", max_length=20, choices=HistoryAction.choices)
    field = models.CharField("campo", max_length=50, blank=True)
    # Valores gravados como texto legível no momento da alteração (RN16).
    old_value = models.TextField("valor anterior", blank=True)
    new_value = models.TextField("valor novo", blank=True)
    created_at = models.DateTimeField("data", auto_now_add=True)

    class Meta:
        verbose_name = "histórico do chamado"
        verbose_name_plural = "históricos dos chamados"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"#{self.ticket_id} {self.get_action_display()} {self.field}".strip()
