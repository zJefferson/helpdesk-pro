"""
Consultas de leitura. A regra de VISIBILIDADE dos chamados mora aqui, em um só lugar (RN01).

Toda view que lista ou busca chamados parte de `visible_tickets(user)`. Por isso,
um solicitante que tenta abrir o chamado de outra pessoa recebe 404 — para ele,
aquele registro simplesmente não existe (RN02).
"""

from .models import Ticket


def visible_tickets(user):
    queryset = Ticket.objects.select_related("category", "requester", "assignee")
    if user.is_admin or user.is_technician:
        return queryset
    return queryset.filter(requester=user)
