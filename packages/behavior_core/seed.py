"""Load pre-computed demo rows into the database.

This lives in behavior_core rather than in scripts/ because the fixture is nothing
but rows of behavior_core.models -- it is data about this layer's own tables, so it
does not belong to any layer above. The chatbot already depends on behavior_core,
which is what lets its lifespan call load() without reaching across into the
console (AGENTS.md, directory boundaries).

The CLI half -- exporting a fresh fixture, and the staleness warning -- stays in
scripts/seed_demo.py. Exporting needs the golden dataset's hash, which belongs to
the console, and the staleness note is a message for whoever typed the command. On
Render there is nobody reading startup logs, so shipping that print into the
serving path would be writing to no one.
"""

import json
from datetime import datetime
from pathlib import Path

from sqlmodel import SQLModel

from behavior_core.db import engine, get_session, seed_baseline
from behavior_core.models import BenchResult, BenchRun, Conversation, Version

FIXTURE = Path(__file__).resolve().parents[2] / "datasets" / "demo_seed.json"
SEED_PREFIX = "seed-"

# Order matters on load: BenchResult points at BenchRun, and a Conversation names
# a version_id. Nothing enforces it in SQLite, but loading children first would
# still be a lie about the shape of the data.
TABLES = [("versions", Version), ("conversations", Conversation), ("runs", BenchRun),
          ("results", BenchResult)]


def load() -> dict[str, tuple[int, int]]:
    """Insert anything from the fixture that is not already there, by primary key.

    Deliberately not an upsert: if a row already exists, whatever is in the
    database wins. A reviewer who has been clicking around should not have their
    own runs quietly overwritten by canned ones.

    Returns per-table (inserted, total) so a caller can report it. Returns an
    empty dict when there is no fixture, because on Render a missing fixture must
    not take the whole service down -- an empty console is bad, a container that
    will not start is worse.
    """
    if not FIXTURE.exists():
        return {}
    payload = json.loads(FIXTURE.read_text())

    # Tables first, fixture second, seed_baseline last. Calling init_db() up front
    # would run seed_baseline() against an empty table, inserting a second row with
    # the same config_hash as the fixture's baseline and leaving two rows claiming
    # to be active. Running it after means it finds the fixture's row, recognises
    # the hash as the one the code actually holds, and activates that.
    SQLModel.metadata.create_all(engine)

    added = {}
    with get_session() as session:
        for key, model in TABLES:
            rows = payload.get(key, [])
            # Read every id first. Interleaving reads with adds makes SQLAlchemy
            # autoflush the pending rows mid-loop, and it flushes them before the
            # datetime coercion below has been applied to the rest.
            missing = [row for row in rows if session.get(model, row["id"]) is None]
            session.add_all(_revive(model, row) for row in missing)
            added[key] = (len(missing), len(rows))
        session.commit()

    seed_baseline()
    added["dataset_hash"] = payload["dataset_hash"]
    return added


def _revive(model, row: dict):
    """Rebuild a row object from JSON, turning ISO strings back into datetimes.

    SQLModel skips validation on `table=True` classes, so `Model(**row)` hands the
    string straight through to the DateTime column and SQLite rejects it several
    frames away from the cause. Coercing here by field annotation keeps the fix
    where the JSON is, rather than making the models tolerate strings they should
    never see at runtime.
    """
    fields = model.model_fields
    revived = {
        key: datetime.fromisoformat(value)
        if isinstance(value, str) and datetime in _annotations(fields[key].annotation)
        else value
        for key, value in row.items()
    }
    return model(**revived)


def _annotations(annotation) -> tuple:
    # `datetime | None` needs unwrapping; a bare `datetime` does not.
    return getattr(annotation, "__args__", (annotation,))
