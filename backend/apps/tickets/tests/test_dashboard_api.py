"""Dashboard (RF20, RN23): números corretos e sempre restritos ao que o usuário pode ver."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.tickets.models import Category, Priority, Status, Ticket

pytestmark = pytest.mark.django_db

URL = reverse("dashboard_summary")


def counts_by(items, key):
    return {item[key]: item["count"] for item in items}


@pytest.fixture
def data(requester, other_requester, technician, make_ticket):
    network = Category.objects.create(name="Rede")
    now = timezone.now()
    make_ticket(requester, priority=Priority.HIGH)  # aberto, sem responsável
    make_ticket(requester, status=Status.IN_PROGRESS, assignee=technician, category=network)
    make_ticket(other_requester, status=Status.WAITING_REQUESTER, assignee=technician)
    make_ticket(other_requester, priority=Priority.CRITICAL)  # aberto, sem responsável
    resolved = make_ticket(requester, status=Status.RESOLVED, assignee=technician)
    # Resolvido 4 horas depois de criado:
    Ticket.objects.filter(pk=resolved.pk).update(
        created_at=now - timedelta(hours=5), resolved_at=now - timedelta(hours=1)
    )
    make_ticket(requester, status=Status.CLOSED)


def test_admin_sees_global_numbers(client_for, admin_user, data):
    response = client_for(admin_user).get(URL)

    assert response.status_code == 200
    d = response.data
    assert d["total"] == 6
    assert d["open"] == 4
    assert d["unassigned"] == 2
    assert d["assigned_to_me"] == 0
    assert d["resolved_last_30_days"] == 1
    assert d["avg_resolution_hours"] == 4.0
    assert counts_by(d["by_status"], "status") == {
        "OPEN": 2,
        "IN_PROGRESS": 1,
        "WAITING_REQUESTER": 1,
        "RESOLVED": 1,
        "CLOSED": 1,
        "CANCELLED": 0,
    }
    assert counts_by(d["by_priority"], "priority") == {1: 0, 2: 4, 3: 1, 4: 1}
    assert counts_by(d["open_by_category"], "name") == {"Hardware": 3, "Rede": 1}


def test_technician_sees_assigned_to_me(client_for, technician, data):
    d = client_for(technician).get(URL).data

    assert d["total"] == 6
    assert d["assigned_to_me"] == 2  # em atendimento + aguardando (o resolvido não conta)


def test_requester_sees_only_own_numbers(client_for, requester, data):
    d = client_for(requester).get(URL).data

    assert d["total"] == 4
    assert d["open"] == 2
    assert d["unassigned"] == 1
    assert counts_by(d["by_priority"], "priority")[Priority.CRITICAL] == 0  # é de outra pessoa


def test_empty_database_returns_zeros(client_for, admin_user):
    d = client_for(admin_user).get(URL).data

    assert d["total"] == 0
    assert d["avg_resolution_hours"] is None
    assert d["open_by_category"] == []
    assert all(item["count"] == 0 for item in d["by_status"])


def test_old_resolutions_are_not_in_30_day_metrics(client_for, admin_user, requester, make_ticket):
    old = make_ticket(requester, status=Status.RESOLVED)
    Ticket.objects.filter(pk=old.pk).update(resolved_at=timezone.now() - timedelta(days=45))

    d = client_for(admin_user).get(URL).data

    assert d["resolved_last_30_days"] == 0
    assert d["avg_resolution_hours"] is None


def test_dashboard_uses_constant_number_of_queries(
    client_for, admin_user, data, requester, make_ticket
):
    client = client_for(admin_user)
    with CaptureQueriesContext(connection) as few:
        client.get(URL)
    for _ in range(20):
        make_ticket(requester)
    with CaptureQueriesContext(connection) as many:
        client.get(URL)

    assert len(few) == len(many) == 2


def test_dashboard_requires_authentication(api_client, db):
    assert api_client.get(URL).status_code == 401
