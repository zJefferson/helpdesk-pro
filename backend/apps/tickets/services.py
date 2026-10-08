"""
Regras de negócio que ALTERAM chamados.

Cada função faz a alteração e grava o histórico na mesma transação:
ou tudo é salvo, ou nada é salvo (RN17).
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Comment, HistoryAction, Priority, Status, Ticket, TicketHistory
from .permissions import FINAL_STATUSES, editable_fields

# Quem pode executar cada transição de status (RN09). Administrador pode todas.
ASSIGNEE = "assignee"  # o técnico responsável pelo chamado
REQUESTER = "requester"  # o solicitante dono do chamado

STATUS_TRANSITIONS = {
    (Status.OPEN, Status.IN_PROGRESS): ASSIGNEE,
    (Status.OPEN, Status.CANCELLED): REQUESTER,
    (Status.IN_PROGRESS, Status.WAITING_REQUESTER): ASSIGNEE,
    (Status.IN_PROGRESS, Status.RESOLVED): ASSIGNEE,
    (Status.WAITING_REQUESTER, Status.IN_PROGRESS): ASSIGNEE,
    (Status.RESOLVED, Status.CLOSED): REQUESTER,  # solicitante confirma a solução
    (Status.RESOLVED, Status.IN_PROGRESS): REQUESTER,  # solicitante reabre
}

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


def _can_act_as(user, ticket, who):
    if user.is_admin:
        return True
    if who == ASSIGNEE:
        return ticket.assignee_id == user.pk
    return ticket.requester_id == user.pk


@transaction.atomic
def change_status(ticket, *, actor, new_status):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    old_status = ticket.status

    if new_status == old_status:
        raise ValidationError({"status": "O chamado já está neste status."})

    who = STATUS_TRANSITIONS.get((old_status, new_status))
    if who is None:
        raise ValidationError(
            {
                "status": f"Transição de '{Status(old_status).label}' para "
                f"'{Status(new_status).label}' não é permitida."
            }
        )
    if not _can_act_as(actor, ticket, who):
        raise PermissionDenied(
            f"Você não pode mudar este chamado para '{Status(new_status).label}'."
        )
    if old_status == Status.OPEN and new_status == Status.IN_PROGRESS and not ticket.assignee_id:
        raise ValidationError({"status": "Atribua um técnico antes de iniciar o atendimento."})

    # RN10: datas de resolução e fechamento acompanham o status.
    now = timezone.now()
    if new_status == Status.RESOLVED:
        ticket.resolved_at = now
    elif old_status == Status.RESOLVED and new_status == Status.IN_PROGRESS:
        ticket.resolved_at = None  # reaberto: a resolução anterior não vale mais
    if new_status in FINAL_STATUSES:
        ticket.closed_at = now

    ticket.status = new_status
    ticket.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])
    TicketHistory.objects.create(
        ticket=ticket,
        actor=actor,
        action=HistoryAction.STATUS_CHANGED,
        field="status",
        old_value=Status(old_status).label,
        new_value=Status(new_status).label,
    )
    return ticket


@transaction.atomic
def assign_ticket(ticket, *, actor, assignee):
    """
    RN07: técnico só pode ASSUMIR (atribuir a si mesmo) um chamado sem responsável.
    RN08: administrador atribui/reatribui a qualquer técnico ativo.
    (Que `assignee` é um técnico ativo, o serializer já validou.)
    """
    # `of=("self",)`: trava só a linha do chamado, não a do usuário responsável.
    ticket = (
        Ticket.objects.select_for_update(of=("self",)).select_related("assignee").get(pk=ticket.pk)
    )

    if actor.is_technician:
        if assignee.pk != actor.pk:
            raise PermissionDenied("Técnicos só podem assumir chamados para si mesmos.")
        if ticket.assignee_id and ticket.assignee_id != actor.pk:
            raise PermissionDenied("Este chamado já tem um responsável.")

    if ticket.assignee_id == assignee.pk:
        return ticket  # nada mudou: não gera histórico

    old_name = ticket.assignee.get_full_name() if ticket.assignee else ""
    ticket.assignee = assignee
    ticket.save(update_fields=["assignee", "updated_at"])
    TicketHistory.objects.create(
        ticket=ticket,
        actor=actor,
        action=HistoryAction.ASSIGNED,
        field="assignee",
        old_value=old_name,
        new_value=assignee.get_full_name(),
    )
    return ticket


@transaction.atomic
def add_comment(ticket, *, author, body, is_internal=False):
    """
    RN12: quem enxerga o chamado pode comentar (a visibilidade já foi checada na view).
    RN13: só técnico/admin criam notas internas.
    """
    if is_internal and author.is_requester:
        raise PermissionDenied("Solicitantes não podem criar notas internas.")

    comment = Comment.objects.create(
        ticket=ticket, author=author, body=body, is_internal=is_internal
    )
    # Um comentário é "atividade" no chamado: atualiza a data para a ordenação por recentes.
    Ticket.objects.filter(pk=ticket.pk).update(updated_at=comment.created_at)
    return comment


def available_actions(user, ticket):
    """
    O que `user` pode fazer em `ticket`, calculado com as MESMAS regras usadas na validação.

    O frontend usa isto só para decidir quais botões mostrar. Toda ação continua sendo
    validada de novo no backend quando é executada.
    """
    if ticket.status in FINAL_STATUSES:
        return {
            "editable_fields": [],
            "status_transitions": [],
            "can_assign": False,
            "can_take": False,
            "can_comment": False,
            "can_comment_internal": False,
        }

    transitions = [
        new
        for (old, new), who in STATUS_TRANSITIONS.items()
        if old == ticket.status
        and _can_act_as(user, ticket, who)
        and not (new == Status.IN_PROGRESS and old == Status.OPEN and not ticket.assignee_id)
    ]
    return {
        "editable_fields": sorted(editable_fields(user, ticket)),
        "status_transitions": transitions,
        "can_assign": user.is_admin,
        "can_take": user.is_technician and ticket.assignee_id is None,
        "can_comment": True,
        "can_comment_internal": not user.is_requester,
    }
