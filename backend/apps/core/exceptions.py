from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    Igual ao tratador padrão do DRF, mas padroniza o 404.

    O Django gera mensagens como "No Ticket matches the given query.", que revelam
    o nome interno do modelo e vêm em inglês. Trocamos por "Não encontrado.".
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    return drf_exception_handler(exc, context)
