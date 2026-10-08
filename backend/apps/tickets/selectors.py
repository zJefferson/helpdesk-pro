"""
Consultas de leitura. A regra de VISIBILIDADE dos chamados mora aqui, em um só lugar (RN01).

Toda view que lista ou busca chamados parte de `visible_tickets(user)`. Por isso,
um solicitante que tenta abrir o chamado de outra pessoa recebe 404 — para ele,
aquele registro simplesmente não existe (RN02).

`select_related` traz os dados relacionados (categoria, usuários) na MESMA consulta,
evitando o problema "N+1" (uma consulta extra para cada item da lista).
"""

from .models import Ticket


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
