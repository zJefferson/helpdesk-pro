"""
Testes da auditoria de segurança: tentativas de burlar autenticação e autorização.

Cada teste descreve um ataque e verifica que a API resiste a ele.
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

ME = reverse("me")


def bearer(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# --- Força bruta no login ------------------------------------------------------


@pytest.mark.parametrize("url_name", ["token_obtain", "session_login"])
def test_login_throttle_cannot_be_bypassed_with_x_forwarded_for(api_client, requester, url_name):
    """O atacante troca o cabeçalho X-Forwarded-For a cada tentativa para parecer outro IP."""
    limit = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].split("/")[0])
    url = reverse(url_name)
    statuses = [
        api_client.post(
            url,
            {"email": requester.email, "password": "errada"},
            format="json",
            HTTP_X_FORWARDED_FOR=f"10.0.0.{i}",
        ).status_code
        for i in range(limit + 3)
    ]

    assert statuses[-1] == 429, statuses


# --- CSRF nos endpoints de sessão (cookie) ---------------------------------------


@pytest.mark.parametrize("url_name", ["session_login", "session_logout", "session_refresh"])
def test_session_endpoints_reject_html_form_posts(api_client, requester, url_name):
    """
    Um site malicioso pode enviar um <form> para a nossa API (application/x-www-form-urlencoded)
    sem passar pelo CORS. Aceitar formulários permitiria "login CSRF" (logar a vítima na conta
    do atacante). Exigir JSON obriga o navegador a fazer preflight, que é bloqueado.
    """
    response = api_client.post(
        reverse(url_name), {"email": requester.email, "password": TEST_PASSWORD}, format="multipart"
    )

    assert response.status_code == 415
    assert (
        settings.REFRESH_COOKIE_NAME not in response.cookies
        or not response.cookies[settings.REFRESH_COOKIE_NAME].value
    )


# --- Tokens adulterados, expirados ou de usuário desativado ------------------------


def test_tampered_token_signature_is_rejected(requester):
    token = str(AccessToken.for_user(requester))
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-4]}AAAA"

    assert bearer(tampered).get(ME).status_code == 401


def test_token_with_alg_none_is_rejected(requester):
    """Ataque clássico: token sem assinatura ("alg": "none")."""
    import base64
    import json

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    payload = {"token_type": "access", "user_id": str(requester.pk), "exp": 9999999999, "jti": "x"}
    unsigned = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(payload)}."

    assert bearer(unsigned).get(ME).status_code == 401


def test_expired_access_token_is_rejected(requester):
    token = AccessToken.for_user(requester)
    token.set_exp(lifetime=-timedelta(seconds=1))

    assert bearer(str(token)).get(ME).status_code == 401


def test_refresh_token_cannot_be_used_as_access(requester):
    refresh = RefreshToken.for_user(requester)

    assert bearer(str(refresh)).get(ME).status_code == 401


def test_access_token_stops_working_when_user_is_deactivated(requester):
    access = str(AccessToken.for_user(requester))
    requester.is_active = False
    requester.save()

    assert bearer(access).get(ME).status_code == 401


# --- Troca de senha encerra as outras sessões --------------------------------------


def test_password_change_revokes_existing_refresh_tokens(api_client, client_for, requester):
    """
    Se a conta foi invadida, trocar a senha precisa expulsar o invasor:
    os refresh tokens emitidos antes da troca devem parar de funcionar.
    """
    stolen = api_client.post(
        reverse("token_obtain"),
        {"email": requester.email, "password": TEST_PASSWORD},
        format="json",
    ).data["refresh"]

    response = client_for(requester).post(
        reverse("change_password"),
        {"current_password": TEST_PASSWORD, "new_password": "Nova-senha-forte-456"},
        format="json",
    )
    assert response.status_code == 204

    reuse = APIClient().post(reverse("token_refresh"), {"refresh": stolen}, format="json")
    assert reuse.status_code == 401


def test_password_change_also_revokes_rotated_browser_session(client_for, requester):
    """O cookie do navegador é rotacionado a cada renovação; o token mais novo também cai."""
    browser = APIClient()
    browser.post(
        reverse("session_login"),
        {"email": requester.email, "password": TEST_PASSWORD},
        format="json",
    )
    assert browser.post(reverse("session_refresh")).status_code == 200  # cookie rotacionado

    client_for(requester).post(
        reverse("change_password"),
        {"current_password": TEST_PASSWORD, "new_password": "Nova-senha-forte-456"},
        format="json",
    )

    assert browser.post(reverse("session_refresh")).status_code == 401


def test_password_change_does_not_affect_other_users(
    api_client, client_for, requester, other_requester
):
    other_refresh = api_client.post(
        reverse("token_obtain"),
        {"email": other_requester.email, "password": TEST_PASSWORD},
        format="json",
    ).data["refresh"]

    client_for(requester).post(
        reverse("change_password"),
        {"current_password": TEST_PASSWORD, "new_password": "Nova-senha-forte-456"},
        format="json",
    )

    reuse = APIClient().post(reverse("token_refresh"), {"refresh": other_refresh}, format="json")
    assert reuse.status_code == 200
