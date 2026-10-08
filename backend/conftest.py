"""
Fixtures globais do pytest: ficam disponíveis em todos os testes do projeto.

Uma fixture é uma função que prepara algo que o teste precisa (ex.: um usuário).
Basta colocar o nome dela como parâmetro do teste.
"""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.tickets.models import Category, Ticket

# Senha usada apenas nos testes (o banco de teste é criado e apagado a cada execução).
TEST_PASSWORD = "Senha-de-teste-123"


@pytest.fixture(autouse=True)
def _clear_cache():
    # O limite de tentativas de login é contado no cache; zera entre os testes.
    cache.clear()


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings):
    # O PBKDF2 é lento DE PROPÓSITO (dificulta ataques). Nos testes isso só atrasa,
    # então usamos um hasher rápido. O teste que verifica o PBKDF2 restaura o real.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


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
def other_requester(make_user):
    return make_user(role=Role.REQUESTER)


@pytest.fixture
def technician(make_user):
    return make_user(role=Role.TECHNICIAN)


@pytest.fixture
def admin_user(make_user):
    return make_user(role=Role.ADMIN)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def client_for():
    """client_for(user) devolve um APIClient já autenticado como `user`."""

    def _client_for(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _client_for


@pytest.fixture
def category(db):
    return Category.objects.create(name="Hardware")


@pytest.fixture
def make_ticket(category):
    def _make_ticket(requester, **kwargs):
        kwargs.setdefault("title", "Impressora não liga")
        kwargs.setdefault("description", "A impressora do 2º andar não liga desde ontem.")
        kwargs.setdefault("category", category)
        return Ticket.objects.create(requester=requester, **kwargs)

    return _make_ticket
