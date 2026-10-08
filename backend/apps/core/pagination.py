from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Paginação padrão: ?page=2&page_size=50 (máximo de 100 itens por página)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
