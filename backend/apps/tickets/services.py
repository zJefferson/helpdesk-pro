"""
Regras de negócio que ALTERAM chamados.

Cada função faz a alteração e grava o histórico na mesma transação:
ou tudo é salvo, ou nada é salvo (RN17).
"""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from .models import HistoryAction, Priority, Ticket, TicketHistory
from .permissions import editable_fields

FIELD_LABELS = {
    "title": "título",
    "description": "descrição",
    "category": "categoria",
    "priority": "prioridade",
}


def _readable(field, value):
    """Converte o valor para texto legível, que é o que fica gravado no histórico (RN16)."""
    if value is None:
        return ""
    if field == "priority":
        return Priority(value).label
    return str(value)  # Category.__str__ devolve o nome


@transaction.atomic
def create_ticket(*, actor, **data):
    # RN03/RN04: o solicitante é sempre quem está logado; status inicial é Aberto.
    ticket = Ticket.objects.create(requester=actor, **data)
    TicketHistory.objects.create(
        ticket=ticket, actor=actor, action=HistoryAction.CREATED, new_value=ticket.title
    )
    return ticket


@transaction.atomic
def update_ticket(ticket, *, actor, data):
    # Trava a linha no banco para evitar que duas edições simultâneas se atropelem.
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)

    forbidden = sorted(set(data) - editable_fields(actor, ticket))
    if forbidden:
        names = ", ".join(FIELD_LABELS.get(f, f) for f in forbidden)
        raise PermissionDenied(f"Seu perfil não pode alterar: {names}.")

    changed = []
    for field, new_value in data.items():
        old_value = getattr(ticket, field)
        if old_value == new_value:
            continue  # enviar o mesmo valor não gera histórico
        TicketHistory.objects.create(
            ticket=ticket,
            actor=actor,
            action=HistoryAction.UPDATED,
            field=field,
            old_value=_readable(field, old_value),
            new_value=_readable(field, new_value),
        )
        setattr(ticket, field, new_value)
        changed.append(field)

    if changed:
        ticket.save(update_fields=[*changed, "updated_at"])
    return ticket
