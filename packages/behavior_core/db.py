import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from behavior_core import models  # noqa: F401  (import registers the tables)
from behavior_core.config import BASELINE_V1

DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parents[2] / "data" / "app.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(conn, _record):
    # WAL matters even though we ship a single process: running the chatbot and
    # the console as separate processes stays a supported deployment (TO-21).
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def get_session() -> Session:
    return Session(engine)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    seed_baseline()


def seed_baseline() -> None:
    from sqlmodel import select

    from behavior_core.models import Version

    with get_session() as session:
        if session.exec(select(Version)).first():
            return
        session.add(
            Version(
                label="v1-baseline",
                config_hash=BASELINE_V1.config_hash(),
                config=BASELINE_V1.model_dump(),
                status="active",
                note="Initial baseline",
            )
        )
        session.commit()
