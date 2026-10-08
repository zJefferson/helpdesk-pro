import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.models import Role, User
from conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


def test_project_uses_custom_user_model():
    assert get_user_model() is User


def test_password_is_stored_as_hash_never_plain_text(requester):
    requester.refresh_from_db()

    assert requester.password != TEST_PASSWORD
    assert requester.password.startswith("pbkdf2_sha256$")
    assert requester.check_password(TEST_PASSWORD)


def test_new_user_is_requester_by_default():
    user = User.objects.create_user(
        email="novo@example.com", password=TEST_PASSWORD, first_name="Novo", last_name="Usuário"
    )

    assert user.role == Role.REQUESTER
    assert user.is_requester
    assert not user.is_staff
    assert not user.is_superuser


def test_email_is_required():
    with pytest.raises(ValueError, match="e-mail"):
        User.objects.create_user(email="", password=TEST_PASSWORD)


def test_email_is_normalized_to_lowercase():
    user = User.objects.create_user(email="  Ana.Silva@Example.COM ", password=TEST_PASSWORD)

    assert user.email == "ana.silva@example.com"


def test_email_is_unique_ignoring_case(make_user):
    make_user(email="ana@example.com")

    with pytest.raises(IntegrityError):
        make_user(email="ANA@example.com")


def test_superuser_is_admin_with_staff_access():
    admin = User.objects.create_superuser(email="admin@example.com", password=TEST_PASSWORD)

    assert admin.role == Role.ADMIN
    assert admin.is_admin
    assert admin.is_staff
    assert admin.is_superuser


def test_superuser_cannot_have_non_admin_role():
    with pytest.raises(ValueError, match="ADMIN"):
        User.objects.create_superuser(
            email="admin@example.com", password=TEST_PASSWORD, role=Role.TECHNICIAN
        )
