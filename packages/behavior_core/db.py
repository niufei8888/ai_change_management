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
    """Make sure the code's BASELINE_V1 exists in the table and is the active one.

    Idempotent and additive: nothing is ever deleted. It re-seeds rather than
    early-returning on "some version exists" because editing a prompt constant
    changes config_hash, and an active row whose hash matches no config in the
    source is the exact kind of invisible drift this product exists to remove.
    Older rows stay as archived history.
    """
    from sqlmodel import select

    from behavior_core.models import Version

    wanted = BASELINE_V1.config_hash()
    with get_session() as session:
        rows = session.exec(select(Version)).all()
        existing = next((row for row in rows if row.config_hash == wanted), None)
        if existing is not None and existing.status == "active":
            return

        for row in rows:
            if row.status == "active":
                row.status = "archived"

        if existing is not None:
            existing.status = "active"
        else:
            session.add(
                Version(
                    label="v1-baseline",
                    config_hash=wanted,
                    config=BASELINE_V1.model_dump(),
                    status="active",
                    note="Seeded from BASELINE_V1 in packages/behavior_core/config.py",
                )
            )
        session.commit()
