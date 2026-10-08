"""
Campo `permissions` do chamado: informa à interface quais ações mostrar.

O teste mais importante é o de consistência: toda transição anunciada precisa ser aceita
pela API, e toda transição NÃO anunciada precisa ser recusada.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from apps.tickets.models import Status

pytestmark = pytest.mark.django_db


def detail(client, ticket):
    response = client.get(reverse("ticket-detail", args=[ticket.pk]))
    assert response.status_code == 200
    return response.data["permissions"]


def test_requester_permissions_on_open_ticket(client_for, requester, make_ticket):
    perms = detail(client_for(requester), make_ticket(requester))

    assert perms == {
        "editable_fields": ["category", "description", "title"],
        "status_transitions": [Status.CANCELLED],
        "can_assign": False,
        "can_take": False,
        "can_comment": True,
        "can_comment_internal": False,
    }


def test_technician_on_unassigned_ticket_can_only_take(
    client_for, technician, requester, make_ticket
):
    perms = detail(client_for(technician), make_ticket(requester))

    assert perms["can_take"] is True
    assert perms["can_assign"] is False
    assert perms["editable_fields"] == []
    assert perms["status_transitions"] == []  # precisa assumir antes de iniciar
    assert perms["can_comment_internal"] is True


def test_assigned_technician_permissions(client_for, technician, requester, make_ticket):
    ticket = make_ticket(requester, assignee=technician, status=Status.IN_PROGRESS)

    perms = detail(client_for(technician), ticket)

    assert perms["editable_fields"] == ["category", "description", "priority", "title"]
    assert set(perms["status_transitions"]) == {Status.WAITING_REQUESTER, Status.RESOLVED}
    assert perms["can_take"] is False


def test_closed_ticket_has_no_actions(client_for, admin_user, requester, make_ticket):
    perms = detail(client_for(admin_user), make_ticket(requester, status=Status.CLOSED))

    assert not any(perms.values())


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN, Role.ADMIN])
@pytest.mark.parametrize(
    "status",
    [Status.OPEN, Status.IN_PROGRESS, Status.WAITING_REQUESTER, Status.RESOLVED],
)
def test_announced_transitions_match_what_the_api_accepts(
    client_for, make_user, requester, technician, make_ticket, role, status
):
    user = requester if role == Role.REQUESTER else make_user(role=role)
    if role == Role.TECHNICIAN:
        user = technician  # o técnico responsável
    client = client_for(user)

    for target in Status.values:
        ticket = make_ticket(requester, status=status, assignee=technician)
        announced = target in detail(client, ticket)["status_transitions"]

        response = client.post(
            reverse("ticket-change-status", args=[ticket.pk]), {"status": target}, format="json"
        )

        assert (response.status_code == 200) == announced, (role, status, target, response.data)
