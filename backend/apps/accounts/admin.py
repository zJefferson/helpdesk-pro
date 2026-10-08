from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserCreationAdminForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role")


class UserChangeAdminForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    O UserAdmin padrão do Django assume o campo `username`, que removemos.
    Por isso redefinimos formulários, listagem e grupos de campos usando o e-mail.
    """

    form = UserChangeAdminForm
    add_form = UserCreationAdminForm

    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("first_name", "last_name")}),
        ("Perfil e acesso", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")
