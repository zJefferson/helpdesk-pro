from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrador"
    TECHNICIAN = "TECHNICIAN", "Técnico"
    REQUESTER = "REQUESTER", "Solicitante"


def normalize_email(email):
    """E-mails são comparados sem diferenciar maiúsculas: guardamos tudo em minúsculas."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    """
    Cria usuários usando o e-mail como login (o User padrão do Django usa `username`).

    `set_password` gera o hash da senha — a senha em texto puro nunca é salva.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        user = self.model(email=normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)

        if extra_fields["is_staff"] is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")
        if extra_fields["role"] != Role.ADMIN:
            raise ValueError("Superusuário precisa ter o perfil ADMIN.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Usuário do sistema. Faz login com e-mail e tem um perfil (`role`)."""

    username = None  # removemos o campo herdado: o login é pelo e-mail
    email = models.EmailField("e-mail", unique=True)
    first_name = models.CharField("nome", max_length=150)
    last_name = models.CharField("sobrenome", max_length=150)
    role = models.CharField("perfil", max_length=20, choices=Role.choices, default=Role.REQUESTER)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]  # pedidos pelo `createsuperuser`

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["first_name", "last_name"]
        constraints = [
            # Garante no banco que "Ana@x.com" e "ana@x.com" não coexistam.
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
        ]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_technician(self):
        return self.role == Role.TECHNICIAN

    @property
    def is_requester(self):
        return self.role == Role.REQUESTER
