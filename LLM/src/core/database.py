import psycopg
from psycopg import Connection

from src.core.config import Settings


class DatabaseConfigurationError(RuntimeError):
    """PostgreSQL 연결 설정이 없을 때 발생한다."""


def connect_database(settings: Settings) -> Connection:
    """설정된 PostgreSQL 연결을 생성한다.

    Args:
        settings: DATABASE_URL과 연결 제한시간을 담은 애플리케이션 설정.

    Returns:
        context manager로 사용할 수 있는 psycopg Connection.

    Raises:
        DatabaseConfigurationError: DATABASE_URL이 설정되지 않았을 때.
        psycopg.Error: PostgreSQL 연결을 생성하지 못했을 때.
    """
    if not settings.database_configured:
        raise DatabaseConfigurationError(
            "Database is not configured. Set DATABASE_URL in LLM/.env or "
            "PostgreSQL fields in the root .env."
        )
    if settings.database_url is not None:
        database_url = settings.database_url.get_secret_value().strip()
        if database_url and not database_url.upper().startswith("YOUR_"):
            return psycopg.connect(
                database_url,
                connect_timeout=settings.database_connect_timeout,
            )

    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=(
            settings.postgres_password.get_secret_value()
            if settings.postgres_password is not None
            else ""
        ),
        connect_timeout=settings.database_connect_timeout,
    )
