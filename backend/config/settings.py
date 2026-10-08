"""
Configurações do Django para o HelpDesk Pro.

Todos os valores sensíveis ou que mudam entre ambientes (dev, teste, produção)
vêm de variáveis de ambiente. Veja o arquivo `.env.example` na raiz do projeto.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Lê o .env da raiz do projeto quando existir (ex.: rodando fora do Docker).
# No Docker, as variáveis já chegam pelo `env_file` do docker-compose.
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceiros
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",  # guarda refresh tokens invalidados (logout)
    "drf_spectacular",
    "django_filters",
    # Apps do projeto
    "apps.core",
    "apps.accounts",
    "apps.tickets",
]

# Usuário customizado (login por e-mail + perfil). Precisa existir ANTES da primeira migration.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco de dados: lido de DATABASE_URL, ex.: postgres://usuario:senha@db:5432/helpdesk
DATABASES = {"default": env.db("DATABASE_URL")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internacionalização: interface em pt-BR; datas salvas em UTC e exibidas no fuso local.
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework: "seguro por padrão" — todo endpoint exige login,
# a menos que a view libere explicitamente (como o health check e o login).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    # Limite de tentativas de login por IP: só aplicado nas views que declaram `throttle_scope`.
    "DEFAULT_THROTTLE_RATES": {"login": env("LOGIN_THROTTLE_RATE", default="10/min")},
}

# JWT: access curto (vai em toda requisição) e refresh mais longo (só renova o access).
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,  # cada renovação gera um refresh novo...
    "BLACKLIST_AFTER_ROTATION": True,  # ...e invalida o antigo
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Documentação OpenAPI/Swagger (drf-spectacular).
SPECTACULAR_SETTINGS = {
    "TITLE": "HelpDesk Pro API",
    "DESCRIPTION": "API de gestão de chamados de suporte técnico de TI.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,  # separa schemas de entrada e saída (campos read-only)
}
