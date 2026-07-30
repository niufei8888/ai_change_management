"""Put real, pre-computed data in the database so the console is not three empty tables.

    uv run python scripts/seed_demo.py load      # fixture -> database (idempotent)
    uv run python scripts/seed_demo.py export    # database -> fixture (how it was made)

The reason this exists: without an API key nothing can be produced, and a reviewer
holding an Anthropic key rather than a Gemini one (TO-31) would otherwise open a
console with no versions, no runs and no traffic. It also means the "a regression
was caught" story does not depend on spending 80 seconds and 15 requests/minute of
quota live on a call.

Why a JSON fixture and a script rather than a committed .db: `data/` is gitignored,
a binary cannot be reviewed in a diff, and shipping my own database would ship
every question I have ever asked it. TO-16.

The fixture is a snapshot of real runs, so it drifts from the code the moment a
prompt constant changes -- a seeded run's config_hash then matches no Version. That
is the same problem TO-26 dealt with, handled the same way: this is additive and
idempotent, never destructive, and seeded rows are visibly marked in the UI so
canned data is never mistaken for something you just produced.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import SQLModel, select  # noqa: E402

from behavior_core.db import engine, get_session, seed_baseline  # noqa: E402
from behavior_core.models import BenchResult, BenchRun, Conversation, Version  # noqa: E402

FIXTURE = Path(__file__).resolve().parent.parent / "datasets" / "demo_seed.json"
SEED_PREFIX = "seed-"

# Order matters on load: BenchResult points at BenchRun, and a Conversation names
# a version_id. Nothing enforces it in SQLite, but loading children first would
# still be a lie about the shape of the data.
TABLES = [("versions", Version), ("conversations", Conversation), ("runs", BenchRun),
          ("results", BenchResult)]


def export() -> None:
    """Snapshot the interesting rows out of whatever is in the database now.

    Conversations are rewritten to a `seed-` session so they are recognisable
    later, and errored ones are dropped: a failed request is worth keeping in a
    real table but seeding one just looks like the seed is broken.
    """
    with get_session() as session:
        versions = session.exec(select(Version)).all()
        runs = session.exec(select(BenchRun).order_by(BenchRun.started_at)).all()
        results = session.exec(select(BenchResult)).all()
        conversations = session.exec(
            select(Conversation).order_by(Conversation.created_at)
        ).all()

    # Only runs against the dataset as it exists on disk. Picking the most common
    # hash instead would have exported the oldest generation of runs, which had the
    # most: results are cached per dataset_hash, so an older dataset accumulates
    # more of them precisely because it is no longer being changed.
    from driftline import dataset

    current = dataset.load().hash
    matching = [run for run in runs if run.dataset_hash == current]
    if not matching:
        raise SystemExit(
            f"no runs against the current dataset ({current}). Run "
            "`python -m driftline.cli bench baseline` and `... bench bad-scope` first."
        )

    # The newest run per label, not every run. Editing a prompt constant changes
    # config_hash without changing dataset_hash, so a label accumulates runs against
    # configs the code can no longer produce. Shipping those would put results in the
    # fixture whose config_hash resolves to nothing -- the exact drift `load` warns
    # about. `runs` is ordered by started_at, so the last write wins.
    latest = {run.version_label: run for run in matching}
    keep_runs = list(latest.values())
    keep_ids = {run.id for run in keep_runs}

    # One conversation per terminal state is enough to show what the column means.
    # Newest first, so a re-export picks up rows produced by the current code rather
    # than the oldest ones that happen to share a terminal state.
    by_outcome: dict[str, Conversation] = {}
    for row in reversed(conversations):
        if row.terminated_by != "error":
            by_outcome.setdefault(row.terminated_by, row)
    keep_conversations = list(by_outcome.values())

    # Only versions something exported actually points at, plus the active one. My
    # own database accumulates every version I have ever saved; dumping all of them
    # would ship a version list where most rows explain nothing.
    wanted = {c.version_id for c in keep_conversations}
    hashes = {r.config_hash for r in keep_runs}
    keep_versions = [
        v for v in versions if v.id in wanted or v.config_hash in hashes or v.status == "active"
    ]

    payload = {
        "_comment": (
            "Real rows exported from a live run, not hand-written. Regenerate with "
            "`python scripts/seed_demo.py export`. Loaded by `... load`, which is "
            "idempotent and never deletes anything."
        ),
        "dataset_hash": current,
        "versions": [_dump(v) for v in keep_versions],
        "conversations": [_seed_session(_dump(c)) for c in keep_conversations],
        "runs": [_dump(r) for r in keep_runs],
        "results": [_dump(r) for r in results if r.run_id in keep_ids],
    }
    FIXTURE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    print(f"wrote {FIXTURE.relative_to(Path.cwd())}")
    print(f"  dataset_hash  {current}")
    for key, _ in TABLES:
        print(f"  {key:14} {len(payload[key])}")


def _dump(row) -> dict:
    return json.loads(row.model_dump_json())


def _seed_session(row: dict) -> dict:
    row["session_id"] = SEED_PREFIX + row["terminated_by"]
    return row


def load() -> None:
    """Insert anything from the fixture that is not already there, by primary key.

    Deliberately not an upsert: if a row already exists, whatever is in the
    database wins. A reviewer who has been clicking around should not have their
    own runs quietly overwritten by canned ones.
    """
    if not FIXTURE.exists():
        raise SystemExit(f"no fixture at {FIXTURE}; run `export` first")
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

    print(f"fixture dataset_hash {payload['dataset_hash']}")
    for key, _ in TABLES:
        new, total = added[key]
        print(f"  {key:14} +{new} of {total}" + ("" if new else "  (already present)"))
    _warn_if_stale(payload)


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


def _warn_if_stale(payload: dict) -> None:
    """Say so if the fixture no longer describes this code.

    A seeded run whose config_hash matches no Version is exactly the invisible
    drift this product exists to surface, so it gets said out loud rather than
    left for someone to notice in the UI.
    """
    from driftline import dataset

    live = dataset.load().hash
    if live != payload["dataset_hash"]:
        print(
            f"\n  note: fixture was built against dataset {payload['dataset_hash']}, "
            f"the dataset on disk hashes to {live}.\n"
            "  Seeded results stay valid as history but are not comparable to new runs.\n"
            "  Re-export to refresh them."
        )


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "export":
        export()
    elif command == "load":
        load()
    else:
        raise SystemExit(__doc__)
