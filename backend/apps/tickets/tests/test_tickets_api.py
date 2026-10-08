"""
Permissões de chamados por perfil e por propriedade do registro.

Todos os testes acessam a API diretamente (como curl/Swagger fariam):
nenhuma proteção depende do frontend.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from apps.tickets.models import Category, HistoryAction, Priority, Status, Ticket, TicketHistory

pytestmark = pytest.mark.django_db

LIST_URL = reverse("ticket-list")


def detail_url(ticket):
    return reverse("ticket-detail", args=[ticket.pk])


def new_ticket_payload(category, **overrides):
    return {
        "title": "Sem acesso à VPN",
        "description": "Desde hoje cedo a VPN recusa minha conexão.",
        "category": category.pk,
        "priority": Priority.HIGH,
        **overrides,
    }


# --- Autenticação -------------------------------------------------------------


def test_anonymous_cannot_access_tickets(api_client, requester, make_ticket):
    ticket = make_ticket(requester)

    assert api_client.get(LIST_URL).status_code == 401
    assert api_client.get(detail_url(ticket)).status_code == 401
    assert api_client.post(LIST_URL, {}, format="json").status_code == 401
    assert api_client.patch(detail_url(ticket), {}, format="json").status_code == 401


# --- Visibilidade (RN01, RN02) ------------------------------------------------


def test_requester_lists_only_own_tickets(client_for, requester, other_requester, make_ticket):
    mine = make_ticket(requester)
    make_ticket(other_requester)

    response = client_for(requester).get(LIST_URL)

    assert response.status_code == 200
    assert [t["id"] for t in response.data["results"]] == [mine.pk]


def test_requester_gets_404_for_ticket_of_another_user(
    client_for, requester, other_requester, make_ticket
):
    others = make_ticket(other_requester)

    client = client_for(requester)

    response = client.get(detail_url(others))
    assert response.status_code == 404
    # A mensagem não pode revelar detalhes internos (ex.: nome do modelo).
    assert response.data["detail"] == "Não encontrado."
    assert client.patch(detail_url(others), {"title": "Invadido"}, format="json").status_code == 404


@pytest.mark.parametrize("role", [Role.TECHNICIAN, Role.ADMIN])
def test_technician_and_admin_see_all_tickets(
    client_for, make_user, requester, other_requester, make_ticket, role
):
    make_ticket(requester)
    make_ticket(other_requester)

    response = client_for(make_user(role=role)).get(LIST_URL)

    assert response.status_code == 200
    assert response.data["count"] == 2


# --- Criação (RN03, RN04, RN05) ----------------------------------------------


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN, Role.ADMIN])
def test_any_role_can_open_ticket_as_requester_of_it(client_for, make_user, category, role):
    user = make_user(role=role)

    response = client_for(user).post(LIST_URL, new_ticket_payload(category), format="json")

    assert response.status_code == 201
    ticket = Ticket.objects.get(pk=response.data["id"])
    assert ticket.requester == user
    assert ticket.status == Status.OPEN
    assert ticket.assignee is None
    assert ticket.history.get().action == HistoryAction.CREATED


@pytest.mark.parametrize(
    "field,value",
    [("requester", 999), ("status", Status.RESOLVED), ("assignee", 1)],
)
def test_create_rejects_fields_controlled_by_backend(client_for, requester, category, field, value):
    payload = new_ticket_payload(category, **{field: value})

    response = client_for(requester).post(LIST_URL, payload, format="json")

    assert response.status_code == 400
    assert field in response.data
    assert not Ticket.objects.exists()


def test_create_rejects_inactive_category(client_for, requester):
    inactive = Category.objects.create(name="Antiga", is_active=False)

    response = client_for(requester).post(LIST_URL, new_ticket_payload(inactive), format="json")

    assert response.status_code == 400
    assert "category" in response.data


def test_create_validates_required_fields_and_lengths(client_for, requester, category):
    client = client_for(requester)

    empty = client.post(LIST_URL, {}, format="json")
    short = client.post(
        LIST_URL, new_ticket_payload(category, title="Oi", description="curta"), format="json"
    )

    assert empty.status_code == 400
    assert {"title", "description", "category"} <= set(empty.data)
    assert short.status_code == 400
    assert {"title", "description"} <= set(short.data)


# --- Edição: solicitante (RN06) -----------------------------------------------


def test_requester_edits_own_open_ticket_and_history_is_recorded(
    client_for, requester, make_ticket
):
    ticket = make_ticket(requester)

    response = client_for(requester).patch(
        detail_url(ticket), {"title": "Impressora do RH não liga"}, format="json"
    )

    assert response.status_code == 200
    ticket.refresh_from_db()
    assert ticket.title == "Impressora do RH não liga"
    entry = TicketHistory.objects.get(ticket=ticket, field="title")
    assert entry.actor == requester
    assert entry.old_value == "Impressora não liga"
    assert entry.new_value == "Impressora do RH não liga"


def test_requester_cannot_edit_ticket_after_it_leaves_open(client_for, requester, make_ticket):
    ticket = make_ticket(requester, status=Status.IN_PROGRESS)

    response = client_for(requester).patch(
        detail_url(ticket), {"title": "Novo título"}, format="json"
    )

    assert response.status_code == 403


def test_requester_cannot_change_priority(client_for, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(requester).patch(
        detail_url(ticket), {"priority": Priority.CRITICAL}, format="json"
    )

    assert response.status_code == 403
    ticket.refresh_from_db()
    assert ticket.priority == Priority.MEDIUM


@pytest.mark.parametrize(
    "payload",
    [{"status": Status.CLOSED}, {"assignee": 1}, {"requester": 1}, {"created_at": "2020-01-01"}],
)
def test_nobody_edits_backend_controlled_fields_via_patch(
    client_for, admin_user, requester, make_ticket, payload
):
    ticket = make_ticket(requester)

    response = client_for(admin_user).patch(detail_url(ticket), payload, format="json")

    assert response.status_code == 400
    ticket.refresh_from_db()
    assert ticket.status == Status.OPEN
    assert ticket.assignee is None


# --- Edição: técnico ----------------------------------------------------------


def test_technician_cannot_edit_ticket_not_assigned_to_them(
    client_for, technician, requester, make_ticket
):
    ticket = make_ticket(requester)

    response = client_for(technician).patch(detail_url(ticket), {"title": "Mudado"}, format="json")

    assert response.status_code == 403


def test_assigned_technician_can_edit_priority(client_for, technician, requester, make_ticket):
    ticket = make_ticket(requester, assignee=technician, status=Status.IN_PROGRESS)

    response = client_for(technician).patch(
        detail_url(ticket), {"priority": Priority.CRITICAL}, format="json"
    )

    assert response.status_code == 200
    entry = TicketHistory.objects.get(ticket=ticket, field="priority")
    assert (entry.old_value, entry.new_value) == ("Média", "Crítica")


def test_technician_cannot_access_admin_only_user_management(client_for, technician):
    assert client_for(technician).get(reverse("user-list")).status_code == 403


# --- Edição: administrador e chamados encerrados (RN11) ------------------------


def test_admin_can_edit_any_active_ticket(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester, status=Status.WAITING_REQUESTER)

    response = client_for(admin_user).patch(
        detail_url(ticket), {"priority": Priority.LOW, "title": "Título revisado"}, format="json"
    )

    assert response.status_code == 200
    assert TicketHistory.objects.filter(ticket=ticket).count() == 2


@pytest.mark.parametrize("final_status", [Status.CLOSED, Status.CANCELLED])
def test_closed_or_cancelled_ticket_is_read_only_even_for_admin(
    client_for, admin_user, requester, make_ticket, final_status
):
    ticket = make_ticket(requester, status=final_status)

    response = client_for(admin_user).patch(detail_url(ticket), {"title": "Mudado"}, format="json")

    assert response.status_code == 403
    assert client_for(admin_user).get(detail_url(ticket)).status_code == 200


def test_sending_same_value_does_not_create_history(client_for, admin_user, requester, make_ticket):
    ticket = make_ticket(requester)

    response = client_for(admin_user).patch(
        detail_url(ticket), {"title": ticket.title}, format="json"
    )

    assert response.status_code == 200
    assert not TicketHistory.objects.filter(ticket=ticket).exists()


@pytest.mark.parametrize("method", ["put", "delete"])
def test_put_and_delete_are_not_allowed(client_for, admin_user, requester, make_ticket, method):
    ticket = make_ticket(requester)

    response = getattr(client_for(admin_user), method)(detail_url(ticket), {}, format="json")

    assert response.status_code == 405
    assert Ticket.objects.filter(pk=ticket.pk).exists()
