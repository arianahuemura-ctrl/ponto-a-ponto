"""Configuração isolada para demonstração temporária por túnel local."""
import re
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403

DEBUG = False
SECRET_KEY = os.environ.get("PAP_PUBLIC_SECRET_KEY", "")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 10:
    raise ImproperlyConfigured("PAP_PUBLIC_SECRET_KEY deve conter uma chave aleatória de pelo menos 50 caracteres.")
PUBLIC_HOST = os.environ.get("PAP_PUBLIC_HOST", "").lower()
if PUBLIC_HOST and (len(PUBLIC_HOST) > 253 or not re.fullmatch(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+", PUBLIC_HOST
)):
    raise ImproperlyConfigured("PAP_PUBLIC_HOST deve ser um domínio exato, sem esquema, porta, caminho ou curinga.")
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "[::1]"] + ([PUBLIC_HOST] if PUBLIC_HOST else [])
PUBLIC_BASE_URL = "https://" + PUBLIC_HOST if PUBLIC_HOST else "http://127.0.0.1:8001"
CSRF_TRUSTED_ORIGINS = ["https://" + PUBLIC_HOST] if PUBLIC_HOST else []
ROOT_URLCONF = "mbm.public_urls"
WSGI_APPLICATION = "mbm.public_wsgi.application"
MIDDLEWARE = [
    "mbm.public_boundary.PublicBoundary",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
] + [m for m in MIDDLEWARE if m != "django.middleware.security.SecurityMiddleware"]
# Sirva somente assets do Vite, nunca a raiz do projeto nem arquivos .env/SQLite.
STATIC_ROOT = BASE_DIR / "frontend/dist/assets"
STATIC_URL = "/assets/"
WHITENOISE_STATIC_PREFIX = "/assets/"
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_ALLOW_ALL_ORIGINS = False
# Gunicorn valida o endereço do proxy e traduz X-Forwarded-Proto para wsgi.url_scheme.
# Não confiar diretamente em HTTP_X_FORWARDED_PROTO dentro do Django.
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
SECURE_SSL_REDIRECT = False  # O boundary redireciona apenas o domínio público.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "pap_public_session"
CSRF_COOKIE_NAME = "pap_public_csrf"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 0  # Domínio temporário; não persistir HSTS no navegador.
# A base Django existente não recebe sessões, avaliações ou migrações nesta instância.
DATABASES = {"default": {**DATABASES["default"],
    "NAME": Path(DATABASES["default"]["NAME"]).resolve().as_uri() + "?mode=ro",
    "OPTIONS": {"uri": True}}}
