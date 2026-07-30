"""Resolves "which behavior version should this request use", on the critical path.

This is the seam the whole product rests on. Because the chatbot asks this
question on every request instead of compiling prompts into the binary, a
version can be rolled out to a slice of traffic and rolled back without a
deploy. In production this call would be an HTTP hop to a control plane with a
local disk cache; here it reads the same SQLite file.

Note there is no fail-open to a last-known-good config. Reading local SQLite
does not have a partial-failure mode worth defending against, and silently
serving traffic with a stale config is exactly the invisible drift this product
exists to eliminate. Let it fail (TO-22).
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Literal

from sqlmodel import select

from behavior_core.config import BehaviorConfig
from behavior_core.db import get_session
from behavior_core.models import Experiment, Version

CACHE_TTL_SECONDS = 5


@dataclass(frozen=True)
class ResolvedConfig:
    version_id: str
    version_label: str
    config_hash: str
    config: BehaviorConfig
    experiment_tag: str | None
    arm: Literal["baseline", "candidate", "default"]


_cache: tuple[float, Version, Experiment | None] | None = None


def invalidate() -> None:
    """Called by the console after any write so changes land on the next request."""
    global _cache
    _cache = None


def _load_state() -> tuple[Version, Experiment | None]:
    global _cache
    if _cache and time.monotonic() - _cache[0] < CACHE_TTL_SECONDS:
        return _cache[1], _cache[2]

    with get_session() as session:
        active = session.exec(select(Version).where(Version.status == "active")).first()
        if active is None:
            raise RuntimeError("No active Version. Run: uv run python -m ask_luma.cli init-db")
        experiment = session.exec(select(Experiment).where(Experiment.status == "running")).first()

    _cache = (time.monotonic(), active, experiment)
    return active, experiment


def _bucket(experiment_id: str, session_id: str) -> int:
    # Salted with the experiment id so consecutive experiments reshuffle. Without
    # the salt the same users land on the same side every time and the second
    # experiment's result is contaminated by the first.
    digest = hashlib.sha256(f"{experiment_id}:{session_id}".encode()).hexdigest()
    return int(digest, 16) % 100


def resolve(session_id: str) -> ResolvedConfig:
    active, experiment = _load_state()

    if experiment is None:
        return ResolvedConfig(
            version_id=active.id,
            version_label=active.label,
            config_hash=active.config_hash,
            config=BehaviorConfig(**active.config),
            experiment_tag=None,
            arm="default",
        )

    in_candidate = _bucket(experiment.id, session_id) < experiment.rollout_pct
    wanted_id = experiment.candidate_version_id if in_candidate else experiment.baseline_version_id
    with get_session() as session:
        version = session.get(Version, wanted_id)
    if version is None:
        raise RuntimeError(f"Experiment {experiment.id} points at missing version {wanted_id}")

    return ResolvedConfig(
        version_id=version.id,
        version_label=version.label,
        config_hash=version.config_hash,
        config=BehaviorConfig(**version.config),
        experiment_tag=experiment.tag,
        arm="candidate" if in_candidate else "baseline",
    )
