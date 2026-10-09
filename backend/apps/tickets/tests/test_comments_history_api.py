"""Comentários (RN12–RN14) e histórico (RN15–RN18)."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.tickets.models import Comment, HistoryAction, Status

pytestmark = pytest.mark.django_db


def comments_url(ticket):
    return reverse("ticket-comments", args=[ticket.pk])


def history_url(ticket):
    return reverse("ticket-history", args=[ticket.pk])


# --- Comentários: criação ---------------------------------------------------------


def test_requester_comments_on_own_ticket(client_for, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(requester).post(
        comments_url(ticket), {"body": "Alguma novidade?"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["author"]["id"] == requester.pk
    assert response.data["is_internal"] is False


def test_requester_cannot_comment_on_others_ticket(
    client_for, requester, other_requester, make_ticket
):
    ticket = make_ticket(other_requester)

    response = client_for(requester).post(comments_url(ticket), {"body": "Oi"}, format="json")

    assert response.status_code == 404
    assert not Comment.objects.exists()


def test_requester_cannot_create_internal_note(client_for, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(requester).post(
        comments_url(ticket), {"body": "Nota secreta", "is_internal": True}, format="json"
    )

    assert response.status_code == 403
    assert not Comment.objects.exists()


def test_technician_creates_internal_note_on_any_ticket(
    client_for, technician, requester, make_ticket
):
    ticket = make_ticket(requester)  # nem precisa ser o responsável

    response = client_for(technician).post(
        comments_url(ticket),
        {"body": "Verificar cabo de rede.", "is_internal": True},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["is_internal"] is True


@pytest.mark.parametrize("body", ["", "   "])
def test_comment_body_cannot_be_empty(client_for, requester, make_ticket, body):
    ticket = make_ticket(requester)

    response = client_for(requester).post(comments_url(ticket), {"body": body}, format="json")

    assert response.status_code == 400
    assert "body" in response.data


def test_comment_body_max_length(client_for, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(requester).post(comments_url(ticket), {"body": "x" * 5001}, format="json")

    assert response.status_code == 400


def test_comment_cannot_set_author(client_for, requester, other_requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(requester).post(
        comments_url(ticket), {"body": "Oi", "author": other_requester.pk}, format="json"
    )

    assert response.status_code == 400


@pytest.mark.parametrize("final_status", [Status.CLOSED, Status.CANCELLED])
def test_cannot_comment_on_closed_ticket(client_for, requester, make_ticket, final_status):
    ticket = make_ticket(requester, status=final_status)

    response = client_for(requester).post(comments_url(ticket), {"body": "Oi"}, format="json")

    assert response.status_code == 403


def test_comment_requires_authentication(api_client, requester, make_ticket):
    ticket = make_ticket(requester)

    assert api_client.get(comments_url(ticket)).status_code == 401
    assert api_client.post(comments_url(ticket), {"body": "Oi"}, format="json").status_code == 401


def test_comment_updates_ticket_activity_date(client_for, requester, make_ticket):
    ticket = make_ticket(requester)
    before = ticket.updated_at

    client_for(requester).post(comments_url(ticket), {"body": "Oi"}, format="json")

    ticket.refresh_from_db()
    assert ticket.updated_at > before


# --- Comentários: leitura -----------------------------------------------------------


@pytest.fixture
def ticket_with_comments(requester, technician, make_ticket):
    ticket = make_ticket(requester)
    Comment.objects.create(ticket=ticket, author=requester, body="Público 1")
    Comment.objects.create(ticket=ticket, author=technician, body="Interna", is_internal=True)
    Comment.objects.create(ticket=ticket, author=technician, body="Público 2")
    return ticket


def test_requester_does_not_see_internal_notes(client_for, requester, ticket_with_comments):
    response = client_for(requester).get(comments_url(ticket_with_comments))

    assert response.status_code == 200
    assert [c["body"] for c in response.data] == ["Público 1", "Público 2"]


def test_technician_sees_all_comments_in_order(client_for, technician, ticket_with_comments):
    response = client_for(technician).get(comments_url(ticket_with_comments))

    assert [c["body"] for c in response.data] == ["Público 1", "Interna", "Público 2"]


def test_comments_list_query_count_does_not_grow(client_for, technician, ticket_with_comments):
    """Evita N+1: com 3 ou 13 comentários, o número de consultas é o mesmo."""
    client = client_for(technician)
    with CaptureQueriesContext(connection) as few:
        client.get(comments_url(ticket_with_comments))

    for i in range(10):
        Comment.objects.create(ticket=ticket_with_comments, author=technician, body=f"Extra {i}")
    with CaptureQueriesContext(connection) as many:
        client.get(comments_url(ticket_with_comments))

    assert len(many) == len(few)


# --- Histórico ------------------------------------------------------------------


def test_history_records_full_flow_with_actor_and_date(client_for, requester, technician, category):
    req, tech = client_for(requester), client_for(technician)

    created = req.post(
        reverse("ticket-list"),
        {
            "title": "Mouse quebrado",
            "description": "O botão esquerdo parou.",
            "category": category.pk,
        },
        format="json",
    )
    url = reverse("ticket-detail", args=[created.data["id"]])
    ticket_id = created.data["id"]
    req.patch(url, {"title": "Mouse com defeito"}, format="json")
    tech.post(
        reverse("ticket-assign", args=[ticket_id]), {"assignee_id": technician.pk}, format="json"
    )
    tech.post(
        reverse("ticket-change-status", args=[ticket_id]), {"status": "IN_PROGRESS"}, format="json"
    )

    response = req.get(reverse("ticket-history", args=[ticket_id]))

    assert response.status_code == 200
    rows = [(h["action"], h["field"], h["old_value"], h["new_value"]) for h in response.data]
    assert rows == [
        (HistoryAction.CREATED, "", "", "Mouse quebrado"),
        (HistoryAction.UPDATED, "title", "Mouse quebrado", "Mouse com defeito"),
        (HistoryAction.ASSIGNED, "assignee", "", technician.get_full_name()),
        (HistoryAction.STATUS_CHANGED, "status", "Aberto", "Em atendimento"),
    ]
    assert [h["actor"]["id"] for h in response.data] == [
        requester.pk,
        requester.pk,
        technician.pk,
        technician.pk,
    ]
    assert all(h["created_at"] for h in response.data)
    assert response.data[0]["action_display"] == "Criado"


def test_requester_cannot_see_history_of_others_ticket(
    client_for, requester, other_requester, make_ticket
):
    ticket = make_ticket(other_requester)

    assert client_for(requester).get(history_url(ticket)).status_code == 404


def test_history_is_read_only(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(admin_user).post(history_url(ticket), {}, format="json")

    assert response.status_code == 405


def test_history_requires_authentication(api_client, requester, make_ticket):
    ticket = make_ticket(requester)

    assert api_client.get(history_url(ticket)).status_code == 401
