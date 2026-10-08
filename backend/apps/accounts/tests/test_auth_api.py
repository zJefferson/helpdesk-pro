"""Testes do fluxo de autenticação JWT: login, /me, refresh, logout e troca de senha."""

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

LOGIN_URL = reverse("token_obtain")
REFRESH_URL = reverse("token_refresh")
LOGOUT_URL = reverse("logout")
ME_URL = reverse("me")
CHANGE_PASSWORD_URL = reverse("change_password")


def login(api_client, email, password=TEST_PASSWORD):
    return api_client.post(LOGIN_URL, {"email": email, "password": password}, format="json")


# --- Login -------------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN, Role.ADMIN])
def test_login_returns_tokens_for_every_role(api_client, make_user, role):
    user = make_user(role=role)

    response = login(api_client, user.email)

    assert response.status_code == 200
    assert set(response.data) == {"access", "refresh"}


def test_login_is_case_insensitive_on_email(api_client, requester):
    response = login(api_client, f"  {requester.email.upper()} ")

    assert response.status_code == 200


def test_login_with_wrong_password_returns_401(api_client, requester):
    response = login(api_client, requester.email, "senha-errada")

    assert response.status_code == 401
    assert "access" not in response.data
    assert response.data["detail"] == "E-mail ou senha inválidos."


def test_login_with_unknown_email_returns_401(api_client, db):
    response = login(api_client, "ninguem@example.com")

    assert response.status_code == 401


def test_inactive_user_cannot_login(api_client, requester):
    requester.is_active = False
    requester.save()

    response = login(api_client, requester.email)

    assert response.status_code == 401


def test_login_requires_email_and_password(api_client, db):
    response = api_client.post(LOGIN_URL, {}, format="json")

    assert response.status_code == 400
    assert {"email", "password"} <= set(response.data)


def test_login_is_rate_limited(api_client, requester, settings):
    limit = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].split("/")[0])
    for _ in range(limit):
        login(api_client, requester.email, "senha-errada")

    response = login(api_client, requester.email)

    assert response.status_code == 429


# --- /me ---------------------------------------------------------------------


def test_me_requires_authentication(api_client, db):
    response = api_client.get(ME_URL)

    assert response.status_code == 401


def test_me_rejects_invalid_token(api_client, db):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer token-falso")

    response = api_client.get(ME_URL)

    assert response.status_code == 401


def test_me_with_real_jwt_returns_user_without_password(api_client, technician):
    access = login(api_client, technician.email).data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get(ME_URL)

    assert response.status_code == 200
    assert response.data["email"] == technician.email
    assert response.data["role"] == Role.TECHNICIAN
    assert "password" not in response.data


def test_user_can_update_own_name(client_for, requester):
    response = client_for(requester).patch(ME_URL, {"first_name": "Maria"}, format="json")

    assert response.status_code == 200
    requester.refresh_from_db()
    assert requester.first_name == "Maria"


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN])
def test_user_cannot_promote_self_to_admin(client_for, make_user, role):
    user = make_user(role=role)

    response = client_for(user).patch(ME_URL, {"role": Role.ADMIN}, format="json")

    assert response.status_code == 400
    assert "role" in response.data
    user.refresh_from_db()
    assert user.role == role


@pytest.mark.parametrize(
    "payload",
    [{"is_staff": True}, {"is_superuser": True}, {"is_active": False}, {"email": "x@y.com"}],
)
def test_user_cannot_change_protected_fields_via_me(client_for, requester, payload):
    response = client_for(requester).patch(ME_URL, payload, format="json")

    assert response.status_code == 400
    requester.refresh_from_db()
    assert not requester.is_staff
    assert not requester.is_superuser
    assert requester.is_active


def test_put_on_me_is_not_allowed(client_for, requester):
    response = client_for(requester).put(ME_URL, {"first_name": "X"}, format="json")

    assert response.status_code == 405


# --- Refresh e logout --------------------------------------------------------


def test_refresh_returns_new_access_and_rotates_refresh(api_client, requester):
    tokens = login(api_client, requester.email).data

    response = api_client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")

    assert response.status_code == 200
    assert response.data["access"]
    assert response.data["refresh"] != tokens["refresh"]

    # Com a rotação, o refresh antigo não serve mais.
    reused = api_client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")
    assert reused.status_code == 401


def test_logout_blacklists_refresh_token(api_client, requester):
    tokens = login(api_client, requester.email).data
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

    assert response.status_code == 204
    after = api_client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")
    assert after.status_code == 401


def test_logout_requires_authentication(api_client, requester):
    tokens = login(api_client, requester.email).data

    response = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

    assert response.status_code == 401


def test_logout_rejects_invalid_token(client_for, requester):
    response = client_for(requester).post(LOGOUT_URL, {"refresh": "lixo"}, format="json")

    assert response.status_code == 400


def test_user_cannot_logout_another_user(api_client, client_for, requester, other_requester):
    victim_tokens = login(api_client, other_requester.email).data

    response = client_for(requester).post(
        LOGOUT_URL, {"refresh": victim_tokens["refresh"]}, format="json"
    )

    assert response.status_code == 400
    still_valid = api_client.post(REFRESH_URL, {"refresh": victim_tokens["refresh"]}, format="json")
    assert still_valid.status_code == 200


# --- Troca de senha ----------------------------------------------------------


def test_change_password_success(api_client, client_for, requester):
    new_password = "Nova-senha-forte-456"

    response = client_for(requester).post(
        CHANGE_PASSWORD_URL,
        {"current_password": TEST_PASSWORD, "new_password": new_password},
        format="json",
    )

    assert response.status_code == 204
    assert login(api_client, requester.email, new_password).status_code == 200
    assert login(api_client, requester.email, TEST_PASSWORD).status_code == 401


def test_change_password_requires_correct_current_password(client_for, requester):
    response = client_for(requester).post(
        CHANGE_PASSWORD_URL,
        {"current_password": "errada", "new_password": "Nova-senha-forte-456"},
        format="json",
    )

    assert response.status_code == 400
    assert "current_password" in response.data


@pytest.mark.parametrize("weak", ["123", "12345678", "password"])
def test_change_password_rejects_weak_password(client_for, requester, weak):
    response = client_for(requester).post(
        CHANGE_PASSWORD_URL,
        {"current_password": TEST_PASSWORD, "new_password": weak},
        format="json",
    )

    assert response.status_code == 400
    assert "new_password" in response.data
