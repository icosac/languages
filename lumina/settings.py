import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me")
DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "")
DEBUG = os.getenv("DEBUG", "0") == "1"


def env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",") if host.strip()]

INVITE_ONLY_SIGNUP = env_bool("INVITE_ONLY_SIGNUP", True)
INVITE_EXPIRY_HOURS = int(os.getenv("INVITE_EXPIRY_HOURS", "168"))
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://localhost:8000")

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY") or os.getenv("OVERLEAF_EMAIL_SMTP_USER", "")
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET") or os.getenv("OVERLEAF_EMAIL_SMTP_PASS", "")
MAILJET_SENDER_EMAIL = os.getenv("MAILJET_SENDER_EMAIL", "")
MAILJET_SENDER_NAME = os.getenv("MAILJET_SENDER_NAME", "Lumina Lexicon")
ADMIN_ACCESS_EMAIL = os.getenv("ADMIN_ACCESS_EMAIL", "enricosaccon96@gmail.com")
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "")
ADMIN_ACCESS_TOTP_SECRET = os.getenv("ADMIN_ACCESS_TOTP_SECRET", "").strip()
ADMIN_ACCESS_TOTP_WINDOW = int(os.getenv("ADMIN_ACCESS_TOTP_WINDOW", "1"))
ADMIN_ACCESS_TOKEN_HOURS = int(os.getenv("ADMIN_ACCESS_TOKEN_HOURS", "1"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini").strip()
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").strip()

csrf_trusted_origins_env = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if csrf_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in csrf_trusted_origins_env.split(",")
        if origin.strip()
    ]
else:
    CSRF_TRUSTED_ORIGINS = []
    for host in ALLOWED_HOSTS:
        if host in {"localhost", "127.0.0.1"}:
            continue
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
    CSRF_TRUSTED_ORIGINS.extend(["http://localhost:8000", "http://127.0.0.1:8000"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
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

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ROOT_URLCONF = "lumina.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],
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

WSGI_APPLICATION = "lumina.wsgi.application"

db_name = os.getenv("DB_NAME", "").strip()
db_user = os.getenv("DB_USER", "").strip()
db_password = os.getenv("DB_PASSWORD", "")
db_host = os.getenv("DB_HOST", "").strip()

if db_name and db_user and db_password and db_host:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "core" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
