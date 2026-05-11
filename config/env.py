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

