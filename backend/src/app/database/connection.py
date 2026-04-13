from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.app.config.settings import settings


def get_engine() -> Engine:
    return create_engine(settings.db_url, pool_pre_ping=True)


def health_check() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
