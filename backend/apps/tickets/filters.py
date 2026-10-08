"""
Filtros e busca da listagem de chamados (RF16–RF18).

Os filtros são aplicados SOBRE `visible_tickets(user)`: um solicitante que filtra por
`requester=<outro usuário>` recebe lista vazia — nunca os chamados de outra pessoa.
"""

import django_filters
from rest_framework.filters import SearchFilter

from .models import Priority, Status, Ticket


class TicketFilter(django_filters.FilterSet):
    # Aceitam vários valores: ?status=OPEN&status=IN_PROGRESS
    status = django_filters.MultipleChoiceFilter(choices=Status.choices)
    priority = django_filters.MultipleChoiceFilter(choices=Priority.choices)
    # Filtros por id: ?category=3, ?requester=5, ?assignee=7
    category = django_filters.NumberFilter(field_name="category")
    requester = django_filters.NumberFilter(field_name="requester")
    assignee = django_filters.NumberFilter(field_name="assignee")
    # ?unassigned=true → chamados sem técnico (a "fila")
    unassigned = django_filters.BooleanFilter(field_name="assignee", lookup_expr="isnull")
    # ?created_after=2026-10-01&created_before=2026-10-31 (datas no fuso local)
    created_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Ticket
        fields = []  # todos declarados acima


class TicketSearchFilter(SearchFilter):
    """
    ?search=impressora procura no título e na descrição.
    Se o termo for um número (ex.: 42 ou #42), também encontra o chamado com esse id.
    """

    def filter_queryset(self, request, queryset, view):
        result = super().filter_queryset(request, queryset, view)
        terms = self.get_search_terms(request)
        if len(terms) == 1:
            number = terms[0].lstrip("#")
            if number.isdigit():
                result = result | queryset.filter(pk=int(number))
        return result
