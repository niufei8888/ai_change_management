"""The Simulation runner: every golden case against one config, serially.

Serial and throttled because the free tier allows 15 requests per minute and one
full pass costs 12-18 of them (see design step 2 §7). Concurrency here would not
make it faster, it would make it spend its time in backoff.

This module is the one documented exception to let-it-fail (TO-22): a single case
blowing up must be recorded as that case failing, not take the batch with it. A
crash on case 1 that hides cases 2 and 3 is a worse outcome than a red row.
"""

import time
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, col, desc, select

from agent import corpus, llm
from agent.graph import runner
from behavior_core.config import BehaviorConfig
from behavior_core.db import get_session
from behavior_core.models import BenchResult, BenchRun
from driftline import checks, dataset, judge

# Enough to keep a 3-case pass inside the rate limit. Skipped after the last case
# and for cache hits, since neither spends quota.
THROTTLE_SECONDS = 20


def start(config: BehaviorConfig, version_label: str) -> str:
    """Create the run row and return its id. Execution happens in the background."""
    data = dataset.load()
    with get_session() as session:
        run = BenchRun(
            config_hash=config.config_hash(),
            dataset_hash=data.hash,
            corpus_hash=corpus.stats()[0],
            config=config.model_dump(),
            version_label=version_label,
        )
        session.add(run)
        session.commit()
        return run.id


def execute(run_id: str) -> None:
    """Run every case. Called as a FastAPI BackgroundTask."""
    data = dataset.load()
    with get_session() as session:
        run = session.get(BenchRun, run_id)
        config = BehaviorConfig(**run.config)
        fingerprint = (run.config_hash, run.dataset_hash, run.corpus_hash)

        spent_quota = False
        for index, case in enumerate(data.cases):
            if spent_quota and index:
                time.sleep(THROTTLE_SECONDS)

            cached = _cached_result(session, fingerprint, case.id)
            if cached is not None:
                session.add(_copy(cached, run_id))
                session.commit()
                continue

            spent_quota = True
            session.add(_run_case(case, config, run_id))
            session.commit()
            run.total_cost_usd = _run_cost(session, run_id)
            session.commit()

        run.status = "done"
        run.total_cost_usd = _run_cost(session, run_id)
        run.finished_at = datetime.now(timezone.utc)
        session.commit()


def _run_case(case: dataset.Case, config: BehaviorConfig, run_id: str) -> BenchResult:
    result = BenchResult(
        run_id=run_id,
        case_id=case.id,
        persona=case.persona,
        question=case.question,
    )
    try:
        outcome = runner.run(case.question, config)
    except Exception:
        result.error = traceback.format_exc(limit=3)
        return result

    observations, passed = checks.run(case, outcome)
    verdicts, judge_result = judge.run(case, outcome)

    result.answer = outcome.answer
    result.trajectory = outcome.trajectory
    result.evidence = outcome.evidence
    result.terminated_by = outcome.terminated_by
    result.observations = observations
    result.verdicts = verdicts
    result.passed = passed
    result.latency_ms = outcome.latency_ms
    result.cost_usd = outcome.cost_usd + (judge_result.cost_usd if judge_result else 0.0)
    return result


def _cached_result(
    session: Session, fingerprint: tuple[str, str, str], case_id: str
) -> BenchResult | None:
    """Same config, same dataset, same corpus, same case -> same answer.

    All three hashes are in the key. Dropping the corpus hash would be the subtle
    bug: refetch the docs, retrieval changes, and every cached result silently
    describes behavior against a corpus that no longer exists.
    """
    config_hash, dataset_hash, corpus_hash = fingerprint
    statement = (
        select(BenchResult)
        .join(BenchRun, col(BenchRun.id) == col(BenchResult.run_id))
        .where(
            BenchRun.config_hash == config_hash,
            BenchRun.dataset_hash == dataset_hash,
            BenchRun.corpus_hash == corpus_hash,
            BenchResult.case_id == case_id,
            col(BenchResult.error).is_(None),
        )
        .order_by(desc(BenchResult.created_at))
    )
    return session.exec(statement).first()


def _copy(source: BenchResult, run_id: str) -> BenchResult:
    return BenchResult(
        run_id=run_id,
        case_id=source.case_id,
        persona=source.persona,
        question=source.question,
        answer=source.answer,
        trajectory=source.trajectory,
        evidence=source.evidence,
        terminated_by=source.terminated_by,
        observations=source.observations,
        verdicts=source.verdicts,
        passed=source.passed,
        cached=True,
        latency_ms=source.latency_ms,
        cost_usd=0.0,  # a cache hit costs nothing, and the run total must show that
    )


def _run_cost(session: Session, run_id: str) -> float:
    rows = session.exec(select(BenchResult).where(BenchResult.run_id == run_id)).all()
    return sum(row.cost_usd for row in rows)


def run_sync(config: BehaviorConfig, version_label: str = "cli") -> dict[str, Any]:
    """Blocking version for the CLI.

    The design's checkpoint is that bench and judge must work from a terminal
    before any of the frontend exists, so that a red result is unambiguously the
    chatbot's behavior and not a fetch bug.
    """
    run_id = start(config, version_label)
    execute(run_id)
    return summary(run_id)


def summary(run_id: str) -> dict[str, Any]:
    with get_session() as session:
        run = session.get(BenchRun, run_id)
        rows = session.exec(
            select(BenchResult)
            .where(BenchResult.run_id == run_id)
            .order_by(col(BenchResult.created_at))
        ).all()

    data = dataset.load()
    return {
        "run": {
            "id": run.id,
            "status": run.status,
            "version_label": run.version_label,
            "config_hash": run.config_hash,
            "dataset_hash": run.dataset_hash,
            "corpus_hash": run.corpus_hash,
            "model": llm.MODEL,
            "total_cost_usd": run.total_cost_usd,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "case_total": len(data.cases),
        },
        "results": [
            {
                **row.model_dump(mode="json"),
                "expectations": [
                    {"index": e.index, "policy": e.policy, "expect": e.expect}
                    for e in data.case(row.case_id).expectations
                ],
                "persona_note": data.personas.get(row.persona, ""),
            }
            for row in rows
        ],
    }
