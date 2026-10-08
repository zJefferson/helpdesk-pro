"""Atribuição de técnicos (RN07, RN08)."""

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from apps.tickets.models import HistoryAction, Status, TicketHistory

pytestmark = pytest.mark.django_db


def assign_url(ticket):
    return reverse("ticket-assign", args=[ticket.pk])


def assign(client, ticket, assignee_id):
    return client.post(assign_url(ticket), {"assignee_id": assignee_id}, format="json")


# --- Técnico -------------------------------------------------------------------


def test_technician_takes_unassigned_ticket(client_for, technician, requester, make_ticket):
    ticket = make_ticket(requester)

    response = assign(client_for(technician), ticket, technician.pk)

    assert response.status_code == 200
    assert response.data["assignee"]["id"] == technician.pk
    entry = TicketHistory.objects.get(ticket=ticket, action=HistoryAction.ASSIGNED)
    assert (entry.old_value, entry.new_value) == ("", technician.get_full_name())
    assert entry.actor == technician


def test_technician_cannot_assign_to_another_technician(
    client_for, technician, make_user, requester, make_ticket
):
    ticket = make_ticket(requester)
    other = make_user(role=Role.TECHNICIAN)

    response = assign(client_for(technician), ticket, other.pk)

    assert response.status_code == 403
    ticket.refresh_from_db()
    assert ticket.assignee is None


def test_technician_cannot_take_ticket_already_assigned(
    client_for, technician, make_user, requester, make_ticket
):
    owner = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(requester, assignee=owner)

    response = assign(client_for(technician), ticket, technician.pk)

    assert response.status_code == 403
    ticket.refresh_from_db()
    assert ticket.assignee == owner


def test_assigning_same_technician_again_does_not_create_history(
    client_for, technician, requester, make_ticket
):
    ticket = make_ticket(requester, assignee=technician)

    response = assign(client_for(technician), ticket, technician.pk)

    assert response.status_code == 200
    assert not TicketHistory.objects.filter(ticket=ticket).exists()


# --- Administrador ---------------------------------------------------------------


def test_admin_reassigns_ticket(
    client_for, admin_user, technician, make_user, requester, make_ticket
):
    ticket = make_ticket(requester, assignee=technician, status=Status.IN_PROGRESS)
    new_tech = make_user(role=Role.TECHNICIAN)

    response = assign(client_for(admin_user), ticket, new_tech.pk)

    assert response.status_code == 200
    entry = TicketHistory.objects.get(ticket=ticket, action=HistoryAction.ASSIGNED)
    assert entry.old_value == technician.get_full_name()
    assert entry.new_value == new_tech.get_full_name()


@pytest.mark.parametrize("target", ["requester", "admin_user", "inactive", "missing"])
def test_assignee_must_be_active_technician(
    client_for, admin_user, requester, make_user, make_ticket, target
):
    ticket = make_ticket(requester)
    candidates = {
        "requester": requester.pk,
        "admin_user": admin_user.pk,
        "inactive": make_user(role=Role.TECHNICIAN, is_active=False).pk,
        "missing": 999_999,
    }

    response = assign(client_for(admin_user), ticket, candidates[target])

    assert response.status_code == 400
    assert "assignee_id" in response.data


def test_assign_requires_assignee_id(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(admin_user).post(assign_url(ticket), {}, format="json")

    assert response.status_code == 400


# --- Acesso indevido -------------------------------------------------------------


def test_requester_cannot_assign(client_for, requester, technician, make_ticket):
    ticket = make_ticket(requester)

    response = assign(client_for(requester), ticket, technician.pk)

    assert response.status_code == 403


def test_anonymous_cannot_assign(api_client, requester, technician, make_ticket):
    ticket = make_ticket(requester)

    assert assign(api_client, ticket, technician.pk).status_code == 401


@pytest.mark.parametrize("final_status", [Status.CLOSED, Status.CANCELLED])
def test_cannot_assign_closed_ticket(
    client_for, admin_user, technician, requester, make_ticket, final_status
):
    ticket = make_ticket(requester, status=final_status)

    assert assign(client_for(admin_user), ticket, technician.pk).status_code == 403


# --- Lista de técnicos -------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.TECHNICIAN, Role.ADMIN])
def test_technicians_list_only_active_technicians(client_for, make_user, technician, role):
    make_user(role=Role.TECHNICIAN, is_active=False)
    make_user(role=Role.REQUESTER)

    response = client_for(make_user(role=role)).get(reverse("user-technicians"))

    assert response.status_code == 200
    ids = [u["id"] for u in response.data]
    assert technician.pk in ids
    assert len(ids) == (2 if role == Role.TECHNICIAN else 1)  # o próprio técnico também


def test_requester_cannot_list_technicians(client_for, requester):
    assert client_for(requester).get(reverse("user-technicians")).status_code == 403
