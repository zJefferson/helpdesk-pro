"""
Fixtures globais do pytest: ficam disponíveis em todos os testes do projeto.

Uma fixture é uma função que prepara algo que o teste precisa (ex.: um usuário).
Basta colocar o nome dela como parâmetro do teste.
"""

import pytest

from apps.accounts.models import Role, User

# Senha usada apenas nos testes (o banco de teste é criado e apagado a cada execução).
TEST_PASSWORD = "Senha-de-teste-123"


@pytest.fixture
def make_user(db):
    """Fábrica de usuários: make_user(role=Role.TECHNICIAN, email="x@y.com")."""
    counter = {"n": 0}

    def _make_user(role=Role.REQUESTER, **kwargs):
        counter["n"] += 1
        kwargs.setdefault("email", f"user{counter['n']}@example.com")
        kwargs.setdefault("first_name", "Usuário")
        kwargs.setdefault("last_name", str(counter["n"]))
        return User.objects.create_user(password=TEST_PASSWORD, role=role, **kwargs)

    return _make_user


@pytest.fixture
def requester(make_user):
    return make_user(role=Role.REQUESTER)


@pytest.fixture
def technician(make_user):
    return make_user(role=Role.TECHNICIAN)
