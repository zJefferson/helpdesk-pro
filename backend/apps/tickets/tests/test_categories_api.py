"""API de categorias (Etapa 5)."""

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from apps.tickets.models import Category

pytestmark = pytest.mark.django_db

LIST_URL = reverse("category-list")


def detail_url(category):
    return reverse("category-detail", args=[category.pk])


@pytest.fixture
def categories(db):
    return {
        "hardware": Category.objects.create(name="Hardware"),
        "rede": Category.objects.create(name="Rede"),
        "antiga": Category.objects.create(name="Antiga", is_active=False),
    }


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN])
def test_non_admin_lists_only_active_categories(client_for, make_user, categories, role):
    response = client_for(make_user(role=role)).get(LIST_URL)

    assert response.status_code == 200
    assert [c["name"] for c in response.data] == ["Hardware", "Rede"]


def test_non_admin_cannot_see_inactive_category_detail(client_for, requester, categories):
    assert client_for(requester).get(detail_url(categories["antiga"])).status_code == 404


def test_admin_lists_all_categories(client_for, admin_user, categories):
    response = client_for(admin_user).get(LIST_URL)

    assert [c["name"] for c in response.data] == ["Antiga", "Hardware", "Rede"]


def test_anonymous_cannot_list_categories(api_client, categories):
    assert api_client.get(LIST_URL).status_code == 401


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN])
def test_non_admin_cannot_create_or_edit(client_for, make_user, categories, role):
    client = client_for(make_user(role=role))

    assert client.post(LIST_URL, {"name": "Nova"}, format="json").status_code == 403
    response = client.patch(detail_url(categories["rede"]), {"name": "X"}, format="json")
    assert response.status_code == 403


def test_admin_creates_and_deactivates_category(client_for, admin_user, categories):
    client = client_for(admin_user)

    created = client.post(LIST_URL, {"name": "Acessos", "description": "Senhas"}, format="json")
    deactivated = client.patch(detail_url(categories["rede"]), {"is_active": False}, format="json")

    assert created.status_code == 201
    assert deactivated.status_code == 200
    categories["rede"].refresh_from_db()
    assert not categories["rede"].is_active


def test_category_name_must_be_unique(client_for, admin_user, categories):
    response = client_for(admin_user).post(LIST_URL, {"name": "Hardware"}, format="json")

    assert response.status_code == 400
    assert "name" in response.data


def test_categories_cannot_be_deleted(client_for, admin_user, categories):
    assert client_for(admin_user).delete(detail_url(categories["rede"])).status_code == 405
