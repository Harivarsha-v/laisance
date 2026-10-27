"""Settings. Everything secret or environment-specific comes from environment variables
(see .env.example); nothing confidential lives in the repository."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # local development only; production sets real env vars


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


# Change this one line to rebrand the whole store.
BRAND_NAME = "L’Aisance"
CURRENCY_SYMBOL = "$"

DEBUG = env_bool("DEBUG", False)
SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Set the SECRET_KEY environment variable (see .env.example).")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):  # set automatically on Render
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS") + [f"https://{h}" for h in ALLOWED_HOSTS if "." in h and not h[0].isdigit()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "store",
]

MIDDLEWARE = [
    "store.middleware.RequestLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "store.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "store.middleware.MaintenanceModeMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "store.middleware.CurrencyMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.store_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQL: SQLite locally, Postgres (or any DATABASE_URL) in production
DATABASES = {
    "default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600)
}

# MongoDB: chat logs and feedback from the assistant
MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DB = os.environ.get("MONGODB_DB", "laisance")
MONGODB_TIMEOUT_MS = int(os.environ.get("MONGODB_TIMEOUT_MS", "2500"))

# Third-party exchange-rate API (time-limited, with fallback rates)
CURRENCY_API_URL = os.environ.get("CURRENCY_API_URL", "https://api.frankfurter.app/latest")
CURRENCY_API_KEY = os.environ.get("CURRENCY_API_KEY", "")  # optional, sent as a header if the provider needs one
CURRENCY_API_TIMEOUT = float(os.environ.get("CURRENCY_API_TIMEOUT", "2.5"))
CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "CHF": "CHF ", "JPY": "¥"}

MAINTENANCE_MODE = env_bool("MAINTENANCE_MODE", False)  # serves the 503 page everywhere except /health/ and /admin/

# requests per minute per visitor on the AI endpoints before a 429
AI_RATE_LIMIT = int(os.environ.get("AI_RATE_LIMIT", "20"))

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

CART_SESSION_KEY = "cart"
CSRF_FAILURE_VIEW = "store.views_care.csrf_failure"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
# CSRF_COOKIE_HTTPONLY stays False: site.js reads the token for fetch() POSTs (Django's documented AJAX pattern)
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440  # 2.5 MB request bodies

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REDIRECT_EXEMPT = [r"^health/?$", r"^health\.json$"]

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
        "requests_file": {
            "class": "logging.handlers.RotatingFileHandler", "formatter": "plain",
            "filename": LOG_DIR / "requests.log", "maxBytes": 2_000_000, "backupCount": 3,
        },
    },
    "loggers": {
        "laisance.requests": {"handlers": ["console", "requests_file"], "level": "INFO", "propagate": False},
        "laisance": {"handlers": ["console"], "level": "INFO"},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.server": {"handlers": [], "propagate": False},  # our request logger replaces runserver's
    },
}
