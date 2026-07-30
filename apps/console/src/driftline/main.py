"""Driftline's HTTP surface, all under /api/console.

Mounted alongside the chatbot by apps/server/main.py. Nothing here imports
apps/chatbot: the loop it runs comes from packages/agent, which is the same code
the chatbot serves. That is what makes "the benchmark tested production behavior"
structurally true rather than a claim.
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import col, desc, select

from agent import corpus, llm, tools
from agent.graph import runner
from behavior_core import config_client
from behavior_core.config import BehaviorConfig
from behavior_core.db import get_session
from behavior_core.models import BenchRun, Version
from driftline import bench, dataset

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

router = APIRouter(prefix="/api/console")


class ConfigBody(BaseModel):
    config: BehaviorConfig


class SaveVersionBody(BaseModel):
    config: BehaviorConfig
    label: str
    note: str = ""
    parent_id: str | None = None


class PlaygroundBody(BaseModel):
    config: BehaviorConfig
    question: str


@router.get("/versions")
def list_versions() -> list[dict]:
    with get_session() as session:
        rows = session.exec(select(Version).order_by(desc(Version.created_at))).all()
    return [row.model_dump(mode="json") for row in rows]


@router.post("/versions")
def save_version(body: SaveVersionBody) -> dict:
    version = Version(
        label=body.label,
        config_hash=body.config.config_hash(),
        config=body.config.model_dump(),
        status="draft",
        parent_id=body.parent_id,
        note=body.note,
    )
    with get_session() as session:
        session.add(version)
        session.commit()
        session.refresh(version)
    return version.model_dump(mode="json")


@router.post("/versions/{version_id}/activate")
def activate(version_id: str) -> dict:
    """100% switch. No gradual rollout in this step -- see design step 2 §1.

    The invalidate() call is the whole point: it is the only demonstrable proof
    that config resolution sits on the chatbot's critical path rather than being
    compiled in at deploy time.
    """
    with get_session() as session:
        target = session.get(Version, version_id)
        if target is None:
            raise HTTPException(404, f"no version {version_id}")

        for row in session.exec(select(Version).where(Version.status == "active")).all():
            row.status = "archived"
        target.status = "active"
        session.commit()
        session.refresh(target)

    config_client.invalidate()
    return target.model_dump(mode="json")


@router.get("/tools")
def tool_catalog(version_id: str | None = None) -> list[dict]:
    """Data source for the `#` autocomplete menu.

    Takes a version so the menu can show what each tool currently expands to; the
    expansion is a lever value, and lever values differ per version.
    """
    with get_session() as session:
        row = (
            session.get(Version, version_id)
            if version_id
            else session.exec(select(Version).where(Version.status == "active")).first()
        )
    return tools.catalog(BehaviorConfig(**row.config))


@router.get("/dataset")
def get_dataset() -> dict:
    return dataset.as_json(dataset.load())


@router.post("/playground/chat")
def playground_chat(body: PlaygroundBody) -> dict:
    """Single turn with a draft config, full trajectory, nothing persisted.

    Deliberately does not write a Conversation row. That table means real traffic;
    mixing experiments into it would make "how is this version doing in
    production" unanswerable.
    """
    outcome = runner.run(body.question, body.config)
    return {
        "answer": outcome.answer,
        "citations": outcome.citations,
        "trajectory": outcome.trajectory,
        "evidence": outcome.evidence,
        "terminated_by": outcome.terminated_by,
        "loop_count": outcome.loop_count,
        "llm_call_count": outcome.llm_call_count,
        "latency_ms": outcome.latency_ms,
        "cost_usd": outcome.cost_usd,
        "tokens_in": outcome.tokens_in,
        "tokens_out": outcome.tokens_out,
        "config_hash": body.config.config_hash(),
        "expanded_prompts": {
            "plan": tools.expand_tools(body.config.plan_prompt, body.config),
            "reflect": tools.expand_tools(body.config.reflect_prompt, body.config),
            "synthesize": tools.expand_tools(body.config.synthesize_prompt, body.config),
        },
    }


class SimulateBody(BaseModel):
    config: BehaviorConfig
    version_label: str = "draft"


@router.post("/simulate")
def simulate(body: SimulateBody, background: BackgroundTasks) -> dict:
    """Kick off a run and return immediately.

    A full pass takes 60-90 seconds because of the rate limit, so it cannot block
    the request. Polling /runs/{id} gives per-case progress for free, which is why
    there is no SSE here -- same call as TO-17 made for /chat.
    """
    run_id = bench.start(body.config, body.version_label)
    background.add_task(bench.execute, run_id)
    return {"run_id": run_id}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    return bench.summary(run_id)


@router.get("/runs")
def list_runs(limit: int = 20) -> list[dict]:
    with get_session() as session:
        rows = session.exec(
            select(BenchRun).order_by(desc(BenchRun.started_at)).limit(limit)
        ).all()
    return [row.model_dump(mode="json") for row in rows]


@router.get("/health")
def health() -> dict:
    data = dataset.load()
    return {
        "status": "ok",
        "model": llm.MODEL,
        "corpus_hash": corpus.stats()[0],
        "dataset_hash": data.hash,
        "case_count": len(data.cases),
        "tool_registry": sorted(tools.TOOL_REGISTRY),
    }


def attach(app: FastAPI) -> None:
    """Add the console's routes and static files to a host app.

    There is no standalone `app` object in this module on purpose. The console
    needs the corpus loaded and the tables created, both of which happen in the
    host's lifespan, so a half-configured app here would only be a way to get a
    confusing empty-corpus failure.
    """
    app.include_router(router)
    app.mount("/console/static", StaticFiles(directory=WEB_DIR), name="console-static")

    @app.get("/console")
    def console_index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")
