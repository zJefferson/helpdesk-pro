from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.urls import reverse


@pytest.mark.django_db
def test_health_returns_ok_when_database_is_available(client):
    # O `client` não está logado: o health check precisa ser público.
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


@pytest.mark.django_db
def test_health_returns_503_when_database_is_unavailable(client):
    with patch("apps.core.views.connection.cursor", side_effect=DatabaseError):
        response = client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
