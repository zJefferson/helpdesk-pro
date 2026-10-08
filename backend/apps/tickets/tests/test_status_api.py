"""Mudança de status: tabela de transições (RN09), quem pode executar e datas (RN10)."""

import itertools

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from apps.tickets.models import HistoryAction, Status, TicketHistory
from apps.tickets.services import STATUS_TRANSITIONS

pytestmark = pytest.mark.django_db


def status_url(ticket):
    return reverse("ticket-change-status", args=[ticket.pk])


def change(client, ticket, new_status):
    return client.post(status_url(ticket), {"status": new_status}, format="json")


# --- Tabela completa de transições -------------------------------------------

ALL_PAIRS = list(itertools.product(Status.values, Status.values))


@pytest.mark.parametrize("old,new", ALL_PAIRS, ids=[f"{a}->{b}" for a, b in ALL_PAIRS])
def test_transition_table_for_admin(
    client_for, admin_user, requester, technician, make_ticket, old, new
):
    """O admin pode tudo que a tabela permite — e nada além dela."""
    ticket = make_ticket(requester, status=old, assignee=technician)

    response = change(client_for(admin_user), ticket, new)

    ticket.refresh_from_db()
    if (old, new) in STATUS_TRANSITIONS:
        assert response.status_code == 200, response.data
        assert ticket.status == new
    else:
        # Encerrado → 403 (somente leitura); demais transições inválidas → 400.
        expected = 403 if old in (Status.CLOSED, Status.CANCELLED) else 400
        assert response.status_code == expected, response.data
        assert ticket.status == old


# --- Quem pode executar cada transição ----------------------------------------


@pytest.mark.parametrize(
    "old,new",
    [
        (Status.OPEN, Status.IN_PROGRESS),
        (Status.IN_PROGRESS, Status.WAITING_REQUESTER),
        (Status.IN_PROGRESS, Status.RESOLVED),
        (Status.WAITING_REQUESTER, Status.IN_PROGRESS),
    ],
)
def test_assignee_transitions(client_for, requester, technician, make_user, make_ticket, old, new):
    ticket = make_ticket(requester, status=old, assignee=technician)
    other_technician = make_user(role=Role.TECHNICIAN)

    assert change(client_for(requester), ticket, new).status_code == 403
    assert change(client_for(other_technician), ticket, new).status_code == 403
    assert change(client_for(technician), ticket, new).status_code == 200


@pytest.mark.parametrize(
    "old,new",
    [
        (Status.OPEN, Status.CANCELLED),
        (Status.RESOLVED, Status.CLOSED),
        (Status.RESOLVED, Status.IN_PROGRESS),
    ],
)
def test_requester_transitions(client_for, requester, technician, make_ticket, old, new):
    ticket = make_ticket(requester, status=old, assignee=technician)

    # Nem o técnico responsável pode cancelar/fechar/reabrir no lugar do solicitante.
    assert change(client_for(technician), ticket, new).status_code == 403
    assert change(client_for(requester), ticket, new).status_code == 200


def test_requester_cannot_change_status_of_others_ticket(
    client_for, requester, other_requester, make_ticket
):
    ticket = make_ticket(other_requester)

    assert change(client_for(requester), ticket, Status.CANCELLED).status_code == 404


def test_cannot_start_without_assignee(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester)

    response = change(client_for(admin_user), ticket, Status.IN_PROGRESS)

    assert response.status_code == 400
    assert "técnico" in str(response.data["status"])


# --- Validação e autenticação -------------------------------------------------


def test_invalid_status_value_returns_400(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester)

    response = change(client_for(admin_user), ticket, "PAUSADO")

    assert response.status_code == 400
    assert "status" in response.data


def test_same_status_returns_400(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester)

    assert change(client_for(admin_user), ticket, Status.OPEN).status_code == 400


def test_status_change_requires_authentication(api_client, requester, make_ticket):
    ticket = make_ticket(requester)

    assert change(api_client, ticket, Status.CANCELLED).status_code == 401


# --- Datas e histórico (RN10, RN15) -------------------------------------------


def test_full_lifecycle_sets_dates_and_records_history(
    client_for, requester, technician, make_ticket
):
    ticket = make_ticket(requester, assignee=technician)
    tech, req = client_for(technician), client_for(requester)

    assert change(tech, ticket, Status.IN_PROGRESS).status_code == 200
    assert change(tech, ticket, Status.RESOLVED).status_code == 200
    ticket.refresh_from_db()
    assert ticket.resolved_at is not None

    assert change(req, ticket, Status.IN_PROGRESS).status_code == 200  # reabre
    ticket.refresh_from_db()
    assert ticket.resolved_at is None

    assert change(tech, ticket, Status.RESOLVED).status_code == 200
    assert change(req, ticket, Status.CLOSED).status_code == 200
    ticket.refresh_from_db()
    assert ticket.closed_at is not None
    assert ticket.resolved_at is not None

    history = TicketHistory.objects.filter(ticket=ticket, action=HistoryAction.STATUS_CHANGED)
    assert [(h.old_value, h.new_value) for h in history] == [
        ("Aberto", "Em atendimento"),
        ("Em atendimento", "Resolvido"),
        ("Resolvido", "Em atendimento"),
        ("Em atendimento", "Resolvido"),
        ("Resolvido", "Fechado"),
    ]
    assert {h.actor_id for h in history} == {technician.pk, requester.pk}


def test_cancel_sets_closed_at(client_for, requester, make_ticket):
    ticket = make_ticket(requester)

    change(client_for(requester), ticket, Status.CANCELLED)

    ticket.refresh_from_db()
    assert ticket.status == Status.CANCELLED
    assert ticket.closed_at is not None
