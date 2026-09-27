import os
import sys

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = True if os.getenv("DEBUG") == "True" else False

# Хосты читаются из окружения: при DEBUG=False пустой список сделал бы
# сайт недоступным (DisallowedHost на каждый запрос).
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "clients",
    "texts",
    "bulkmailing",
    "statistics",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.BlockedUserMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
    "config.middleware.ClientCacheMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_USER"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST"),
        "PORT": os.getenv("DATABASE_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND") or ("config.email.RecordingSMTPBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT") or "587")
EMAIL_USE_TLS = True if os.getenv("EMAIL_USE_TLS") == "True" else False
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = (
    os.getenv("DEFAULT_FROM_EMAIL") or EMAIL_HOST_USER or "webmaster@localhost"
)

AUTH_USER_MODEL = "users.CustomUser"

AUTHENTICATION_BACKENDS = [
    "users.backends.EmailBackend",
]

LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "/"

CACHES = {
    "default": {
        "BACKEND": "config.cache.ResilientRedisCache",
        "LOCATION": os.getenv("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", default="prmessenger"),
    }
}

if "test" in sys.argv:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "prmessenger-test",
    }

STATISTICS_CACHE_SECONDS = 60

CACHE_EQUIV_TTL = True
