import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
from .environment import load_environment
load_environment(BASE_DIR)
SPTRANS_PLANNER = os.environ.get('SPTRANS_PLANNER', 'connections')
SPTRANS_CONNECTION_API_BUDGET = float(os.environ.get('SPTRANS_CONNECTION_API_BUDGET', '20'))
SPTRANS_TOKEN = os.environ.get('SPTRANS_TOKEN', '')
SPTRANS_DATABASE = os.environ.get('SPTRANS_DATABASE', str(BASE_DIR / 'sptrans.sqlite3'))
sys.path.insert(0, str(BASE_DIR))
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-mbm-local")
if not DEBUG and SECRET_KEY == "dev-only-mbm-local":
    raise RuntimeError("Defina DJANGO_SECRET_KEY ao desativar DEBUG.")
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]"
).split(",")
# Permite identificar a origem nas consultas ao mapa sem enviar caminho ou parâmetros.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
ROOT_URLCONF = "mbm.urls"
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "transit",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
STATIC_URL = "/static/"
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
OSM_USER_AGENT = os.environ.get(
    "OSM_USER_AGENT", "MauaBusMap/0.2 (local academic prototype)"
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("MBM_DATABASE", str(BASE_DIR / "db.sqlite3")),
    }
}
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

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
            ]
        },
    }
]
