from pathlib import Path
from urllib.parse import unquote, urlparse


def parse_allowed_hosts(value: str):
    return [host.strip() for host in value.split(",") if host.strip()]


def build_database_config(database_url: str, base_dir):
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(base_dir) / "db.sqlite3",
        }

    parsed = urlparse(database_url)
    if parsed.scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
    if parsed.scheme == "sqlite":
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": parsed.path,
        }
    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")


def build_security_config(debug: bool):
    if debug:
        return {
            "SESSION_COOKIE_SECURE": False,
            "CSRF_COOKIE_SECURE": False,
            "SECURE_SSL_REDIRECT": False,
            "SECURE_PROXY_SSL_HEADER": None,
            "SECURE_HSTS_SECONDS": 0,
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
            "SECURE_HSTS_PRELOAD": False,
        }
    return {
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_SSL_REDIRECT": True,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https"),
        "SECURE_HSTS_SECONDS": 31536000,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
        "SECURE_HSTS_PRELOAD": True,
    }
