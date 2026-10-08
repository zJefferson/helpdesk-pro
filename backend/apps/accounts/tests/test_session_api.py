"""Sessão do navegador: refresh token em cookie HttpOnly (nunca no corpo da resposta)."""

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

LOGIN = reverse("session_login")
REFRESH = reverse("session_refresh")
LOGOUT = reverse("session_logout")
COOKIE = settings.REFRESH_COOKIE_NAME


def login(client, user, password=TEST_PASSWORD):
    return client.post(LOGIN, {"email": user.email, "password": password}, format="json")


def test_login_returns_only_access_and_sets_secure_cookie(api_client, requester):
    response = login(api_client, requester)

    assert response.status_code == 200
    assert set(response.data) == {"access"}  # o refresh NÃO vem no corpo
    cookie = response.cookies[COOKIE]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/api/v1/auth/session/"
    assert int(cookie["max-age"]) == 24 * 60 * 60


def test_access_from_session_login_works_on_api(api_client, requester):
    access = login(api_client, requester).data["access"]

    other = APIClient()
    other.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert other.get(reverse("me")).data["email"] == requester.email


def test_login_with_wrong_password_sets_no_cookie(api_client, requester):
    response = login(api_client, requester, "errada")

    assert response.status_code == 401
    assert COOKIE not in response.cookies


def test_refresh_uses_cookie_and_rotates_it(api_client, requester):
    login(api_client, requester)
    old_cookie = api_client.cookies[COOKIE].value

    response = api_client.post(REFRESH)

    assert response.status_code == 200
    assert set(response.data) == {"access"}
    assert response.cookies[COOKIE].value != old_cookie

    # O cookie antigo (rotacionado) não serve mais.
    stale = APIClient()
    stale.cookies[COOKIE] = old_cookie
    assert stale.post(REFRESH).status_code == 401


def test_refresh_without_cookie_returns_401(api_client, db):
    assert api_client.post(REFRESH).status_code == 401


def test_refresh_with_garbage_cookie_returns_401_and_clears_cookie(api_client, db):
    api_client.cookies[COOKIE] = "lixo"

    response = api_client.post(REFRESH)

    assert response.status_code == 401
    assert response.cookies[COOKIE].value == ""


def test_refresh_fails_after_user_is_deactivated(api_client, requester):
    login(api_client, requester)
    requester.is_active = False
    requester.save()

    assert api_client.post(REFRESH).status_code == 401


def test_logout_blacklists_and_clears_cookie(api_client, requester):
    login(api_client, requester)
    cookie_value = api_client.cookies[COOKIE].value

    response = api_client.post(LOGOUT)

    assert response.status_code == 204
    assert response.cookies[COOKIE].value == ""
    replay = APIClient()
    replay.cookies[COOKIE] = cookie_value
    assert replay.post(REFRESH).status_code == 401


def test_logout_without_session_is_harmless(api_client, db):
    assert api_client.post(LOGOUT).status_code == 204


def test_session_login_is_rate_limited(api_client, requester):
    limit = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].split("/")[0])
    for _ in range(limit):
        login(api_client, requester, "errada")

    assert login(api_client, requester).status_code == 429
