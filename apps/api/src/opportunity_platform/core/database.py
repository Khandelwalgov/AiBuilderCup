"""Connection policy, without network access or diagnostic credential exposure."""

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def validate_neon_url(value, direct=False):
    try:
        url = make_url(value)
        if (
            url.drivername != "postgresql+psycopg"
            or not url.host
            or not url.host.endswith(".neon.tech")
            or not url.username
            or not url.password
            or not url.database
            or url.query.get("sslmode") not in {"require", "verify-full"}
            or "host" in url.query
            or "hostaddr" in url.query
            or "service" in url.query
            or (direct and "-pooler." in url.host)
        ):
            raise ValueError()
    except (ValueError, TypeError, ArgumentError):
        raise ValueError(
            "Use an SSL-enabled Neon psycopg URL; schema jobs require a direct endpoint"
        ) from None
    return url


def connect_args(provider):
    result = {"connect_timeout": 10}
    if provider == "neon":
        # Transaction pooler compatible; no server-side prepared-statement state.
        result["prepare_threshold"] = None
    return result
