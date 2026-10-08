"""Filtros, busca, ordenação e paginação da listagem de chamados (RF16–RF19)."""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.tickets.models import Category, Priority, Status, Ticket

pytestmark = pytest.mark.django_db

LIST_URL = reverse("ticket-list")


def ids(response):
    assert response.status_code == 200, response.data
    return [t["id"] for t in response.data["results"]]


@pytest.fixture
def scenario(requester, other_requester, technician, make_user, make_ticket, category):
    """Cinco chamados com combinações diferentes de status, prioridade, categoria e pessoas."""
    network = Category.objects.create(name="Rede")
    tech2 = make_user(role=Role.TECHNICIAN)
    t = {
        "printer": make_ticket(requester, title="Impressora travando", priority=Priority.LOW),
        "vpn": make_ticket(
            requester,
            title="VPN caindo",
            description="A conexão VPN cai a cada 5 minutos.",
            category=network,
            priority=Priority.CRITICAL,
            status=Status.IN_PROGRESS,
            assignee=technician,
        ),
        "wifi": make_ticket(
            other_requester,
            title="Wi-Fi lento",
            description="Internet muito lenta na sala de reuniões.",
            category=network,
            priority=Priority.HIGH,
            status=Status.WAITING_REQUESTER,
            assignee=tech2,
        ),
        "mouse": make_ticket(other_requester, title="Mouse sem fio", priority=Priority.MEDIUM),
        "closed": make_ticket(
            requester, title="Teclado", status=Status.CLOSED, assignee=technician
        ),
    }
    t["network"], t["tech2"] = network, tech2
    return t


# --- Filtros ---------------------------------------------------------------------


def test_filter_by_single_and_multiple_status(client_for, admin_user, scenario):
    client = client_for(admin_user)

    assert ids(client.get(LIST_URL, {"status": "OPEN"})) == sorted(
        [scenario["printer"].pk, scenario["mouse"].pk], reverse=True
    )
    result = ids(client.get(LIST_URL + "?status=IN_PROGRESS&status=WAITING_REQUESTER"))
    assert set(result) == {scenario["vpn"].pk, scenario["wifi"].pk}


def test_filter_by_priority(client_for, admin_user, scenario):
    result = ids(client_for(admin_user).get(LIST_URL + "?priority=3&priority=4"))

    assert set(result) == {scenario["vpn"].pk, scenario["wifi"].pk}


def test_filter_by_category(client_for, admin_user, scenario):
    result = ids(client_for(admin_user).get(LIST_URL, {"category": scenario["network"].pk}))

    assert set(result) == {scenario["vpn"].pk, scenario["wifi"].pk}


def test_filter_by_requester(client_for, admin_user, other_requester, scenario):
    result = ids(client_for(admin_user).get(LIST_URL, {"requester": other_requester.pk}))

    assert set(result) == {scenario["wifi"].pk, scenario["mouse"].pk}


def test_filter_by_assignee_and_unassigned(client_for, admin_user, technician, scenario):
    client = client_for(admin_user)

    assert set(ids(client.get(LIST_URL, {"assignee": technician.pk}))) == {
        scenario["vpn"].pk,
        scenario["closed"].pk,
    }
    assert set(ids(client.get(LIST_URL, {"unassigned": "true"}))) == {
        scenario["printer"].pk,
        scenario["mouse"].pk,
    }


def test_filters_combine(client_for, admin_user, technician, scenario):
    result = ids(
        client_for(admin_user).get(
            LIST_URL, {"assignee": technician.pk, "status": "IN_PROGRESS", "priority": 4}
        )
    )

    assert result == [scenario["vpn"].pk]


def test_filter_by_creation_date(client_for, admin_user, scenario):
    old = scenario["printer"]
    Ticket.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=30))
    today = timezone.localdate()

    client = client_for(admin_user)
    recent = ids(client.get(LIST_URL, {"created_after": today.isoformat()}))
    older = ids(client.get(LIST_URL, {"created_before": (today - timedelta(days=1)).isoformat()}))

    assert old.pk not in recent
    assert older == [old.pk]


@pytest.mark.parametrize(
    "params",
    [
        {"status": "PAUSADO"},
        {"priority": "9"},
        {"category": "abc"},
        {"created_after": "ontem"},
    ],
)
def test_invalid_filter_values_return_400(client_for, admin_user, scenario, params):
    response = client_for(admin_user).get(LIST_URL, params)

    assert response.status_code == 400


def test_invalid_boolean_filter_is_ignored(client_for, admin_user, scenario):
    # Comportamento padrão do django-filter: valor booleano inválido = filtro não aplicado.
    response = client_for(admin_user).get(LIST_URL, {"unassigned": "talvez"})

    assert response.data["count"] == 5


def test_filters_never_bypass_visibility(client_for, requester, other_requester, scenario):
    """Solicitante filtrando pelos chamados de outra pessoa recebe lista vazia."""
    client = client_for(requester)

    assert ids(client.get(LIST_URL, {"requester": other_requester.pk})) == []
    assert ids(client.get(LIST_URL, {"search": str(scenario["wifi"].pk)})) == []
    assert set(ids(client.get(LIST_URL))) == {
        scenario["printer"].pk,
        scenario["vpn"].pk,
        scenario["closed"].pk,
    }


# --- Busca -----------------------------------------------------------------------


def test_search_in_title_and_description_case_insensitive(client_for, admin_user, scenario):
    client = client_for(admin_user)

    assert ids(client.get(LIST_URL, {"search": "TRAVANDO"})) == [scenario["printer"].pk]
    # "reuniões" só aparece na descrição do chamado de Wi-Fi.
    assert ids(client.get(LIST_URL, {"search": "REUNIÕES"})) == [scenario["wifi"].pk]


def test_search_by_ticket_number(client_for, admin_user, scenario):
    client = client_for(admin_user)
    pk = scenario["mouse"].pk

    assert pk in ids(client.get(LIST_URL, {"search": str(pk)}))
    assert pk in ids(client.get(LIST_URL, {"search": f"#{pk}"}))


def test_search_without_results(client_for, admin_user, scenario):
    response = client_for(admin_user).get(LIST_URL, {"search": "inexistente"})

    assert response.data["count"] == 0
    assert response.data["results"] == []


# --- Ordenação -------------------------------------------------------------------


def test_default_ordering_is_newest_first(client_for, admin_user, scenario):
    result = ids(client_for(admin_user).get(LIST_URL))

    assert result == sorted(result, reverse=True)


def test_order_by_priority_desc(client_for, admin_user, scenario):
    response = client_for(admin_user).get(LIST_URL, {"ordering": "-priority"})

    priorities = [t["priority"] for t in response.data["results"]]
    assert priorities == sorted(priorities, reverse=True)
    assert priorities[0] == Priority.CRITICAL


def test_ordering_by_unknown_field_is_ignored(client_for, admin_user, scenario):
    """Campos fora de `ordering_fields` são ignorados (não dá para ordenar por senha etc.)."""
    response = client_for(admin_user).get(LIST_URL, {"ordering": "requester__password"})

    assert response.status_code == 200
    result = ids(response)
    assert result == sorted(result, reverse=True)  # caiu na ordenação padrão


# --- Paginação -------------------------------------------------------------------


def test_pagination_metadata_and_pages(client_for, admin_user, requester, make_ticket):
    for i in range(25):
        make_ticket(requester, title=f"Chamado número {i}")
    client = client_for(admin_user)

    first = client.get(LIST_URL)
    second = client.get(first.data["next"])

    assert first.data["count"] == 25
    assert len(first.data["results"]) == 20  # tamanho padrão
    assert first.data["previous"] is None
    assert len(second.data["results"]) == 5
    assert second.data["next"] is None
    all_ids = ids(first) + ids(second)
    assert len(set(all_ids)) == 25  # nenhum repetido, nenhum perdido


def test_page_size_param_and_maximum(client_for, admin_user, requester, make_ticket):
    for i in range(5):
        make_ticket(requester, title=f"Chamado número {i}")
    client = client_for(admin_user)

    assert len(client.get(LIST_URL, {"page_size": 2}).data["results"]) == 2
    # Pedir mais que o máximo (100) é limitado silenciosamente.
    assert len(client.get(LIST_URL, {"page_size": 1000}).data["results"]) == 5


def test_stable_pagination_with_ties(client_for, admin_user, requester, make_ticket):
    """Muitos chamados com a mesma prioridade: as páginas não repetem nem perdem itens."""
    for i in range(30):
        make_ticket(requester, title=f"Empate {i}", priority=Priority.HIGH)
    client = client_for(admin_user)

    pages = [
        ids(client.get(LIST_URL, {"ordering": "priority", "page_size": 7, "page": n}))
        for n in range(1, 6)
    ]

    flat = [pk for page in pages for pk in page]
    assert len(flat) == 30
    assert len(set(flat)) == 30


def test_page_out_of_range_returns_404(client_for, admin_user, scenario):
    assert client_for(admin_user).get(LIST_URL, {"page": 99}).status_code == 404


def test_list_query_count_does_not_grow_with_results(
    client_for, admin_user, requester, technician, make_ticket
):
    """Evita N+1: a listagem faz o mesmo número de consultas com 2 ou 20 chamados."""
    client = client_for(admin_user)
    for _ in range(2):
        make_ticket(requester, assignee=technician)
    with CaptureQueriesContext(connection) as few:
        client.get(LIST_URL)

    for _ in range(18):
        make_ticket(requester, assignee=technician)
    with CaptureQueriesContext(connection) as many:
        client.get(LIST_URL)

    assert len(many) == len(few) == 2  # 1 COUNT (paginação) + 1 SELECT com JOINs
