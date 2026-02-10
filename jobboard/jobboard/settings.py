"""
Django settings for jobboard project.
"""
from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-)zsdz&31r_s%w#_^vsl^g+u8+f%!u*5xe1vbb$6iukfk-ka1l-")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"

_default_allowed_hosts = ["127.0.0.1", "localhost", "testserver"]
ALLOWED_HOSTS = (
    os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if os.getenv("DJANGO_ALLOWED_HOSTS")
    else _default_allowed_hosts
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "jobs",
    "resumes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "jobboard.urls"

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
                "accounts.context_processors.notifications_nav",
            ],
        },
    }
]

WSGI_APPLICATION = "jobboard.wsgi.application"

# -----------------------------
# Database (PostgreSQL)
# -----------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.postgresql").strip()
if DB_ENGINE in {"sqlite", "sqlite3", "django.db.backends.sqlite3"}:
    raise ImproperlyConfigured("SQLite is disabled for this project. Please configure PostgreSQL in .env.")
if DB_ENGINE != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Only PostgreSQL is supported. Set DB_ENGINE=django.db.backends.postgresql")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "jobboard_db"),
        "USER": os.getenv("DB_USER", "job_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", "YourStrongPassHere"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# -----------------------------
# Custom User Model (Phase 3)
# -----------------------------
AUTH_USER_MODEL = "accounts.User"

# -----------------------------
# Session management (Phase 3)
# -----------------------------
# 1 hour default session age (can be overridden)
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "3600"))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SMS_ACTIVATION_TTL_SECONDS = int(os.getenv("SMS_ACTIVATION_TTL_SECONDS", "600"))

# -----------------------------
# Password validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------
# Email (Phase 4 - Activation)
# -----------------------------
# For development: print emails in the console.
# For real SMTP, set EMAIL_BACKEND + EMAIL_HOST/... via env.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@jobboard.local")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "0") == "1"

# -----------------------------
# Logging (Phase 3)
# -----------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
SMS_DEMO_LOG = LOG_DIR / "sms_demo.log"
EMAIL_DEMO_LOG = LOG_DIR / "email_demo.log"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "file": {
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "jobboard.log"),
            "formatter": "standard",
            "level": "INFO",
        },
    },
    "root": {"handlers": ["console", "file"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
