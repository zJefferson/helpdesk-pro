"""Testes de inicialização: garantem que o projeto está configurado corretamente."""

from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection

from apps.accounts.models import User


def test_database_is_postgresql():
    # Regra do projeto: não trocar PostgreSQL por SQLite.
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


@pytest.mark.django_db
def test_can_read_and_write_database(requester):
    assert User.objects.filter(pk=requester.pk).exists()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)


@pytest.mark.django_db
def test_no_pending_model_changes_without_migration():
    # Falha se alguém alterar um model e esquecer de rodar `makemigrations`.
    out = StringIO()
    call_command("makemigrations", "--check", "--dry-run", stdout=out)
    assert "No changes detected" in out.getvalue()


def test_django_system_check_passes():
    call_command("check", fail_level="WARNING")


def test_drf_requires_authentication_by_default():
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]
