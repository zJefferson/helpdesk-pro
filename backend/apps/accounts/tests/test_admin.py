import pytest
from django.urls import reverse

from apps.accounts.models import User
from conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = User.objects.create_superuser(email="admin@example.com", password=TEST_PASSWORD)
    client.force_login(admin)
    return client


@pytest.mark.parametrize(
    "url_name",
    [
        "admin:accounts_user_changelist",
        "admin:accounts_user_add",
        "admin:tickets_category_changelist",
        "admin:tickets_ticket_changelist",
        "admin:tickets_ticket_add",
        "admin:tickets_tickethistory_changelist",
    ],
)
def test_admin_pages_load(admin_client, url_name):
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 200


def test_admin_requires_staff_login(client, requester):
    client.force_login(requester)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 302  # redireciona para o login do admin
