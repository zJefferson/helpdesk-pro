"""Gestão de usuários: somente administradores (RN19, RN20, RN21)."""

import pytest
from django.urls import reverse

from apps.accounts.models import Role, User

pytestmark = pytest.mark.django_db

LIST_URL = reverse("user-list")


def detail_url(user):
    return reverse("user-detail", args=[user.pk])


NEW_USER = {
    "email": "Novo.Tecnico@Example.com",
    "first_name": "Novo",
    "last_name": "Técnico",
    "role": Role.TECHNICIAN,
    "password": "Senha-forte-789",
}


# --- Acesso indevido ---------------------------------------------------------


def test_anonymous_cannot_list_users(api_client, db):
    assert api_client.get(LIST_URL).status_code == 401


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN])
def test_non_admin_cannot_list_create_or_edit_users(client_for, make_user, role):
    user = make_user(role=role)
    client = client_for(user)

    assert client.get(LIST_URL).status_code == 403
    assert client.post(LIST_URL, NEW_USER, format="json").status_code == 403
    assert client.get(detail_url(user)).status_code == 403
    # Nem pela rota de usuários dá para se promover.
    response = client.patch(detail_url(user), {"role": Role.ADMIN}, format="json")
    assert response.status_code == 403
    user.refresh_from_db()
    assert user.role == role


# --- Administrador -----------------------------------------------------------


def test_admin_lists_users_paginated(client_for, admin_user, requester, technician):
    response = client_for(admin_user).get(LIST_URL)

    assert response.status_code == 200
    assert response.data["count"] == 3
    assert all("password" not in item for item in response.data["results"])


def test_admin_creates_user_with_hashed_password(client_for, admin_user):
    response = client_for(admin_user).post(LIST_URL, NEW_USER, format="json")

    assert response.status_code == 201
    assert "password" not in response.data
    user = User.objects.get(pk=response.data["id"])
    assert user.email == "novo.tecnico@example.com"
    assert user.role == Role.TECHNICIAN
    assert user.password != NEW_USER["password"]
    assert user.check_password(NEW_USER["password"])


def test_create_user_requires_password(client_for, admin_user):
    payload = {k: v for k, v in NEW_USER.items() if k != "password"}

    response = client_for(admin_user).post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert "password" in response.data


@pytest.mark.parametrize("weak", ["123", "12345678", "novotecnico"])
def test_create_user_rejects_weak_password(client_for, admin_user, weak):
    response = client_for(admin_user).post(LIST_URL, {**NEW_USER, "password": weak}, format="json")

    assert response.status_code == 400
    assert "password" in response.data


def test_create_user_rejects_duplicate_email_ignoring_case(client_for, admin_user, requester):
    payload = {**NEW_USER, "email": requester.email.upper()}

    response = client_for(admin_user).post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert "email" in response.data


def test_create_user_rejects_invalid_role(client_for, admin_user):
    response = client_for(admin_user).post(
        LIST_URL, {**NEW_USER, "role": "SUPERHERO"}, format="json"
    )

    assert response.status_code == 400
    assert "role" in response.data


def test_admin_changes_role_and_deactivates_other_user(client_for, admin_user, requester):
    response = client_for(admin_user).patch(
        detail_url(requester), {"role": Role.TECHNICIAN, "is_active": False}, format="json"
    )

    assert response.status_code == 200
    requester.refresh_from_db()
    assert requester.role == Role.TECHNICIAN
    assert not requester.is_active


def test_admin_cannot_remove_own_admin_role(client_for, admin_user):
    response = client_for(admin_user).patch(
        detail_url(admin_user), {"role": Role.REQUESTER}, format="json"
    )

    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.role == Role.ADMIN


def test_admin_cannot_deactivate_self(client_for, admin_user):
    response = client_for(admin_user).patch(
        detail_url(admin_user), {"is_active": False}, format="json"
    )

    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.is_active


def test_password_cannot_be_changed_through_users_endpoint(client_for, admin_user, requester):
    response = client_for(admin_user).patch(
        detail_url(requester), {"password": "Outra-senha-forte-1"}, format="json"
    )

    assert response.status_code == 400


def test_users_cannot_be_deleted(client_for, admin_user, requester):
    response = client_for(admin_user).delete(detail_url(requester))

    assert response.status_code == 405
    assert User.objects.filter(pk=requester.pk).exists()
