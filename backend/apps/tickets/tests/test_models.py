import pytest
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError

from apps.tickets.models import (
    Category,
    Comment,
    HistoryAction,
    Priority,
    Status,
    Ticket,
    TicketHistory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return Category.objects.create(name="Hardware")


@pytest.fixture
def ticket(category, requester):
    return Ticket.objects.create(
        title="Impressora não liga",
        description="A impressora do 2º andar não liga desde ontem.",
        category=category,
        requester=requester,
    )


def test_new_ticket_defaults(ticket):
    assert ticket.status == Status.OPEN
    assert ticket.priority == Priority.MEDIUM
    assert ticket.assignee is None
    assert ticket.resolved_at is None
    assert ticket.closed_at is None
    assert ticket.created_at is not None


def test_priority_orders_by_severity_not_alphabetically(category, requester):
    for priority in (Priority.HIGH, Priority.LOW, Priority.CRITICAL, Priority.MEDIUM):
        Ticket.objects.create(
            title=f"Chamado {priority.label}",
            description="Descrição suficientemente longa.",
            category=category,
            requester=requester,
            priority=priority,
        )

    ordered = list(Ticket.objects.order_by("-priority").values_list("priority", flat=True))

    assert ordered == [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]


def test_ticket_field_length_validation(category, requester):
    ticket = Ticket(title="Oi", description="curta", category=category, requester=requester)

    with pytest.raises(ValidationError) as exc:
        ticket.full_clean()

    assert "title" in exc.value.message_dict
    assert "description" in exc.value.message_dict


def test_category_with_tickets_cannot_be_deleted(ticket, category):
    with pytest.raises(ProtectedError):
        category.delete()


def test_user_with_tickets_cannot_be_deleted(ticket, requester):
    with pytest.raises(ProtectedError):
        requester.delete()


def test_comments_and_history_are_linked_to_ticket(ticket, requester, technician):
    Comment.objects.create(ticket=ticket, author=requester, body="Alguma novidade?")
    Comment.objects.create(ticket=ticket, author=technician, body="Verificando.", is_internal=True)
    TicketHistory.objects.create(ticket=ticket, actor=requester, action=HistoryAction.CREATED)

    assert ticket.comments.count() == 2
    assert ticket.comments.filter(is_internal=True).count() == 1
    assert ticket.history.get().action == HistoryAction.CREATED


def test_string_representations(ticket, category):
    assert str(ticket) == f"#{ticket.pk} Impressora não liga"
    assert str(category) == "Hardware"
