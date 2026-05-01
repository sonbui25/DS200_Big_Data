from src.app.database.connection import get_engine, health_check
from src.app.database.models import metadata


def bootstrap_schema() -> None:
    engine = get_engine()
    metadata.create_all(bind=engine)


if __name__ == "__main__":
    health_check()
    bootstrap_schema()
    print("Database bootstrap completed.")
