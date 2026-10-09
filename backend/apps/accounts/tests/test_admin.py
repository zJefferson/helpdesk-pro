import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.tickets.models import Comment, Status, Ticket, TicketHistory
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
        "admin:tickets_category_add",
        "admin:tickets_ticket_changelist",
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


# --- Chamados no Django Admin: somente leitura -----------------------------------
# Status, responsável, comentários e histórico só mudam pela API, que aplica as regras de
# negócio e grava o histórico. O admin serve para consulta (e para usuários/categorias).


def test_ticket_cannot_be_created_in_django_admin(admin_client):
    assert admin_client.get(reverse("admin:tickets_ticket_add")).status_code == 403


def test_ticket_detail_is_view_only_in_django_admin(
    admin_client, requester, technician, make_ticket
):
    ticket = make_ticket(requester)
    url = reverse("admin:tickets_ticket_change", args=[ticket.pk])

    page = admin_client.get(url)
    attempt = admin_client.post(
        url, {"title": "Mudado", "status": Status.CLOSED, "assignee": technician.pk}
    )

    assert page.status_code == 200
    assert b'name="status"' not in page.content  # campo não editável
    assert attempt.status_code == 403
    ticket.refresh_from_db()
    assert ticket.status == Status.OPEN
    assert ticket.assignee is None


def test_ticket_cannot_be_deleted_in_django_admin(admin_client, requester, make_ticket):
    ticket = make_ticket(requester)
    TicketHistory.objects.create(ticket=ticket, actor=requester, action="CREATED")

    response = admin_client.post(
        reverse("admin:tickets_ticket_delete", args=[ticket.pk]), {"post": "yes"}
    )

    assert response.status_code == 403
    assert Ticket.objects.filter(pk=ticket.pk).exists()
    assert TicketHistory.objects.filter(ticket=ticket).exists()


def test_comments_cannot_be_edited_in_django_admin(admin_client, requester, make_ticket):
    ticket = make_ticket(requester)
    Comment.objects.create(ticket=ticket, author=requester, body="Original")

    page = admin_client.get(reverse("admin:tickets_ticket_change", args=[ticket.pk]))

    assert b"Original" in page.content
    assert b'name="comments-0-body"' not in page.content
