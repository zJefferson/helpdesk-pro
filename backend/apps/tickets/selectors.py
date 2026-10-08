"""
Consultas de leitura. A regra de VISIBILIDADE dos chamados mora aqui, em um só lugar (RN01).

Toda view que lista ou busca chamados parte de `visible_tickets(user)`. Por isso,
um solicitante que tenta abrir o chamado de outra pessoa recebe 404 — para ele,
aquele registro simplesmente não existe (RN02).

`select_related` traz os dados relacionados (categoria, usuários) na MESMA consulta,
evitando o problema "N+1" (uma consulta extra para cada item da lista).
"""

from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from .models import Priority, Status, Ticket


def visible_tickets(user):
    queryset = Ticket.objects.select_related("category", "requester", "assignee")
    if user.is_admin or user.is_technician:
        return queryset
    return queryset.filter(requester=user)


def visible_comments(user, ticket):
    """RN13: notas internas nunca aparecem para o solicitante."""
    queryset = ticket.comments.select_related("author")
    if user.is_requester:
        queryset = queryset.filter(is_internal=False)
    return queryset


def ticket_history(ticket):
    return ticket.history.select_related("actor")


ACTIVE_STATUSES = [Status.OPEN, Status.IN_PROGRESS, Status.WAITING_REQUESTER]


def dashboard_summary(user):
    """
    Indicadores do dashboard (RF20), sempre sobre os chamados que o usuário pode ver (RN23).

    Usa agregações no banco (COUNT/AVG com filtro) em vez de trazer os chamados para o
    Python: são 2 consultas, não importa quantos chamados existam.
    """
    tickets = visible_tickets(user).select_related(None)
    since = timezone.now() - timedelta(days=30)
    resolved_recently = Q(resolved_at__gte=since)

    counts = tickets.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status__in=ACTIVE_STATUSES)),
        unassigned=Count("id", filter=Q(status__in=ACTIVE_STATUSES, assignee__isnull=True)),
        assigned_to_me=Count("id", filter=Q(status__in=ACTIVE_STATUSES, assignee=user)),
        resolved_last_30_days=Count("id", filter=resolved_recently),
        avg_resolution=Avg(F("resolved_at") - F("created_at"), filter=resolved_recently),
        **{f"status_{value}": Count("id", filter=Q(status=value)) for value in Status.values},
        **{f"priority_{value}": Count("id", filter=Q(priority=value)) for value in Priority.values},
    )
    by_category = (
        tickets.filter(status__in=ACTIVE_STATUSES)
        .values("category_id", "category__name")
        .annotate(count=Count("id"))
        .order_by("-count", "category__name")
    )

    avg = counts["avg_resolution"]
    return {
        "total": counts["total"],
        "open": counts["open"],
        "unassigned": counts["unassigned"],
        "assigned_to_me": counts["assigned_to_me"],
        "resolved_last_30_days": counts["resolved_last_30_days"],
        "avg_resolution_hours": round(avg.total_seconds() / 3600, 1) if avg else None,
        "by_status": [
            {"status": s.value, "label": s.label, "count": counts[f"status_{s.value}"]}
            for s in Status
        ],
        "by_priority": [
            {"priority": p.value, "label": p.label, "count": counts[f"priority_{p.value}"]}
            for p in Priority
        ],
        "open_by_category": [
            {"id": row["category_id"], "name": row["category__name"], "count": row["count"]}
            for row in by_category
        ],
    }
