import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# -------------------------
# Helpers
# -------------------------

def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# True on Heroku dynos
ON_HEROKU = "DYNO" in os.environ

# -------------------------
# Core security
# -------------------------

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "G4GryHSukz7jaFX_JNpHYO8cjtnd8hwKVBuOq60JP2uj2DCQB5ZwLGtIp7ljoMTJod8",
)

# DEBUG:
# - On Heroku: default False
# - Locally: default True
DEBUG = env_bool("DEBUG", default=(not ON_HEROKU))

# Allowed hosts (comma-separated in env)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

# Local dev always allowed
if DEBUG:
    ALLOWED_HOSTS += ["127.0.0.1", "localhost"]

# Heroku fallback if ALLOWED_HOSTS is missing
if ON_HEROKU and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [".herokuapp.com"]

# CSRF trusted origins (comma-separated)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# Sensible fallback for Heroku if not explicitly set:
# - only derive from explicit hostnames (skip wildcards like ".herokuapp.com")
if ON_HEROKU and not CSRF_TRUSTED_ORIGINS:
    for host in ALLOWED_HOSTS:
        if host.startswith("."):
            continue
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

# If behind a proxy (Heroku/Cloudflare), let Django know HTTPS is forwarded correctly
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies secure only in production
SESSION_COOKIE_SECURE = ON_HEROKU and not DEBUG
CSRF_COOKIE_SECURE = ON_HEROKU and not DEBUG

# Force HTTPS in production unless explicitly disabled
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=(ON_HEROKU and not DEBUG))

# -------------------------
# Auth redirects
# -------------------------
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "login"

# -------------------------
# Studio bridge config
# -------------------------
STUDIO_API_KEY = os.getenv("STUDIO_API_KEY", "").strip()

SITE_URL = os.getenv("SITE_URL", "https://mintkit.co.uk").rstrip("/")

# -------------------------
# PlanMyBalance (PMB) bridge config
# -------------------------
PMB_API_KEY = os.getenv("PMB_API_KEY", "").strip()

PMB_STRIPE_SECRET_KEY = os.getenv("PMB_STRIPE_SECRET_KEY", "").strip()
PMB_STRIPE_WEBHOOK_SECRET = os.getenv("PMB_STRIPE_WEBHOOK_SECRET", "").strip()

PMB_STRIPE_PRICE_BASIC = os.getenv("PMB_STRIPE_PRICE_BASIC", "").strip()
PMB_STRIPE_PRICE_PRO = os.getenv("PMB_STRIPE_PRICE_PRO", "").strip()
PMB_STRIPE_PRICE_SUPPORTER = os.getenv("PMB_STRIPE_PRICE_SUPPORTER", "").strip()

# Comma-separated full origins, e.g.:
# https://planmybalance.com, https://mathematical-coral-9xd-draft.caffeine.xyz
PMB_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("PMB_ALLOWED_ORIGINS", "").split(",") if o.strip()]


# -------------------------
# Apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # CORS
    "corsheaders",

    # Cloudinary
    "cloudinary_storage",
    "cloudinary",

    # Project apps
    "core",
    "accounts.apps.AccountsConfig",
    "storefronts",
    "subscriptions",
    "studio_bridge",
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # CORS must be placed before CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -------------------------
# CORS (Studio -> Hub)
# -------------------------
CORS_ALLOWED_ORIGINS = [
    "https://mass-crimson-2ia-draft.caffeine.xyz",
    "https://mintkit-smr.caffeine.xyz",
] + PMB_ALLOWED_ORIGINS

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-studio-key",
    "x-pmb-api-key",
]

# -------------------------
# URLs / Templates
# -------------------------
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
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Use Cloudinary for MEDIA only when Cloudinary is configured on Heroku
if ON_HEROKU and os.getenv("CLOUDINARY_URL"):
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# Email (Mailgun SMTP)
# -------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("MAILGUN_SMTP_SERVER", "")
EMAIL_PORT = int(os.getenv("MAILGUN_SMTP_PORT", "587"))
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("MAILGUN_SMTP_LOGIN", "")
EMAIL_HOST_PASSWORD = os.getenv("MAILGUN_SMTP_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "MintKit <no-reply@mg.mintkit.co.uk>",
)

DEFAULT_REPLY_TO_EMAIL = os.getenv(
    "DEFAULT_REPLY_TO_EMAIL",
    "support@mintkit.co.uk",
)

# -------------------------
# Stripe
# -------------------------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

STRIPE_PRICE_BASIC = os.getenv("STRIPE_PRICE_BASIC", "")
STRIPE_PRICE_BASIC_ANNUAL = os.getenv("STRIPE_PRICE_BASIC_ANNUAL", "")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")

# -------------------------
# Stripe (PlanMyBalance / separate Stripe account)
# -------------------------
PMB_STRIPE_SECRET_KEY = os.getenv("PMB_STRIPE_SECRET_KEY", "")
PMB_STRIPE_WEBHOOK_SECRET = os.getenv("PMB_STRIPE_WEBHOOK_SECRET", "")

PMB_STRIPE_PRICE_BASIC = os.getenv("PMB_STRIPE_PRICE_BASIC", "")
PMB_STRIPE_PRICE_PRO = os.getenv("PMB_STRIPE_PRICE_PRO", "")
PMB_STRIPE_PRICE_SUPPORTER = os.getenv("PMB_STRIPE_PRICE_SUPPORTER", "")

PMB_ALLOWED_ORIGINS = os.getenv("PMB_ALLOWED_ORIGINS", "")


# -------------------------
# Logging
# -------------------------
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
