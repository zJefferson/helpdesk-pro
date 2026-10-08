from rest_framework.filters import OrderingFilter


class StableOrderingFilter(OrderingFilter):
    """
    Ordenação com desempate pelo id.

    Se vários registros têm o mesmo valor (ex.: mesma prioridade), o banco pode devolvê-los
    em ordem diferente a cada consulta — e um item pode aparecer em duas páginas ou em
    nenhuma. Acrescentar o `id` no final torna a ordem sempre a mesma.
    """

    def get_ordering(self, request, queryset, view):
        ordering = list(super().get_ordering(request, queryset, view) or [])
        if not any(field.lstrip("-") == "id" for field in ordering):
            ordering.append("-id")
        return ordering
