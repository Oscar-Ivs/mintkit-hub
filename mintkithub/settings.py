import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Core security / env
# -------------------------

# Use env var on Heroku (set it in Config Vars). Fallback is only for local dev.

# True on Heroku dynos
ON_HEROKU = "DYNO" in os.environ

# Security settings
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "G4GryHSukz7jaFX_JNpHYO8cjtnd8hwKVBuOq60JP2uj2DCQB5ZwLGtIp7ljoMTJod8",
)

# DEBUG:
# - On Heroku: default False (and keep it False)
# - Locally: default True (unless explicitly set)
def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")

DEBUG = env_bool("DEBUG", default=(not ON_HEROKU))


# Allowed hosts (comma-separated in env)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

# Local dev always allowed so 127.0.0.1 works without extra setup
if DEBUG:
    ALLOWED_HOSTS += ["127.0.0.1", "localhost"]

# If running on Heroku and ALLOWED_HOSTS is missing, don't hard-crash
# (still recommended to set ALLOWED_HOSTS properly in Config Vars)
if ON_HEROKU and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [".herokuapp.com"]


# CSRF trusted origins (needed once you use HTTPS domains / custom domains)
# Comma-separated: "https://app.herokuapp.com,https://www.example.com"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Sensible default for Heroku if not explicitly set
if ON_HEROKU and not CSRF_TRUSTED_ORIGINS:
    for host in ALLOWED_HOSTS:
        if host.startswith("."):
            CSRF_TRUSTED_ORIGINS.append(f"https://{host[1:]}")
        else:
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")


# If behind a proxy (Heroku), let Django know HTTPS is forwarded correctly
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# These should be True on Heroku (prod) and False locally
SESSION_COOKIE_SECURE = ON_HEROKU and not DEBUG
CSRF_COOKIE_SECURE = ON_HEROKU and not DEBUG

# Optional: force HTTPS in prod (recommended once everything is stable)
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)


# -------------------------
# Auth redirects
# -------------------------
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "login"


# -------------------------
# Apps / middleware
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Cloudinary (MEDIA uploads)
    "cloudinary_storage",
    "cloudinary",

    # Project apps
    "core",
    "accounts.apps.AccountsConfig",
    "storefronts",
    "subscriptions",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mintkithub.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mintkithub.wsgi.application"


# -------------------------
# Database
# -------------------------
# Uses DATABASE_URL on Heroku automatically; falls back to sqlite locally.
# If Heroku breaks only when DEBUG=False, try setting DATABASE_SSL_REQUIRE=False in Config Vars.
DATABASE_SSL_REQUIRE = env_bool("DATABASE_SSL_REQUIRE", default=ON_HEROKU)

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        ssl_require=DATABASE_SSL_REQUIRE,
    )
}


# -------------------------
# Password validation
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# -------------------------
# i18n
# -------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# -------------------------
# Static / media
# -------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise storage (compression + hashed filenames for long-term caching)
STORAGES = {
    # Media uploads (profile pics, storefront logos)
    "default": {
        "BACKEND": "django_cloudinary_storage.storage.MediaCloudinaryStorage"
        if ON_HEROKU
        else "django.core.files.storage.FileSystemStorage",
    },
    # Static files
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
