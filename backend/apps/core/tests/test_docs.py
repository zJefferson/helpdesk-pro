import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_openapi_schema_is_public_and_lists_auth_endpoints(client):
    response = client.get(reverse("schema"))

    assert response.status_code == 200
    content = response.content.decode()
    for path in ("/api/v1/auth/token/", "/api/v1/auth/me/", "/api/v1/tickets/"):
        assert path in content


@pytest.mark.django_db
def test_swagger_ui_is_available(client):
    assert client.get(reverse("swagger-ui")).status_code == 200
