import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sqlmodel import desc, select  # noqa: E402

from agent import corpus, llm  # noqa: E402
from agent.graph import runner  # noqa: E402
from behavior_core import config_client  # noqa: E402
from behavior_core.db import get_session, init_db  # noqa: E402
from behavior_core.models import Conversation  # noqa: E402

WEB_DIR = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    llm.require_key()
    init_db()
    corpus.load()
    yield


app = FastAPI(title="Ask Luma", lifespan=lifespan)


class ChatRequest(BaseModel):
    session_id: str
    question: str


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    """The one endpoint that matters.

    This is the only try/except in the serving path, and it is here for
    observability rather than recovery: it does not rescue the request, it just
    makes sure a failure still lands in the table with its partial trajectory.
    Step 2's rollout health and auto-rollback are built entirely on those rows,
    so a failure that leaves no trace is worse than the failure itself.
    """
    resolved = config_client.resolve(request.session_id)

    try:
        outcome = runner.run(request.question, resolved.config)
    except Exception as exc:
        _persist(request, resolved, runner.Outcome(answer="", terminated_by="error"), repr(exc))
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc

    _persist(request, resolved, outcome, None)
    return {
        "answer": outcome.answer,
        "citations": outcome.citations,
        "version_label": resolved.version_label,
        "arm": resolved.arm,
        "experiment_tag": resolved.experiment_tag,
        "trajectory": outcome.trajectory,
        "terminated_by": outcome.terminated_by,
        "loop_count": outcome.loop_count,
        "llm_call_count": outcome.llm_call_count,
        "latency_ms": outcome.latency_ms,
        "cost_usd": outcome.cost_usd,
        "tokens_in": outcome.tokens_in,
        "tokens_out": outcome.tokens_out,
    }


def _persist(
    request: ChatRequest,
    resolved: config_client.ResolvedConfig,
    outcome: runner.Outcome,
    error: str | None,
) -> None:
    with get_session() as session:
        session.add(
            Conversation(
                session_id=request.session_id,
                question=request.question,
                answer=outcome.answer,
                error=error,
                version_id=resolved.version_id,
                config_hash=resolved.config_hash,
                model_version=llm.MODEL,
                experiment_tag=resolved.experiment_tag,
                arm=resolved.arm,
                trajectory=outcome.trajectory,
                terminated_by=outcome.terminated_by,
                loop_count=outcome.loop_count,
                llm_call_count=outcome.llm_call_count,
                retrieved_articles=outcome.retrieved_articles,
                citations=outcome.citations,
                latency_ms=outcome.latency_ms,
                cost_usd=outcome.cost_usd,
                tokens_in=outcome.tokens_in,
                tokens_out=outcome.tokens_out,
            )
        )
        session.commit()


@app.get("/api/conversations")
def conversations(
    session_id: str | None = None,
    tag: str | None = None,
    arm: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """History for the chat frontend (by session_id) and experiment slices for
    the step 2 console (by tag / arm). One endpoint, two consumers."""
    query = select(Conversation).order_by(desc(Conversation.created_at))
    if session_id:
        query = query.where(Conversation.session_id == session_id)
    if tag:
        query = query.where(Conversation.experiment_tag == tag)
    if arm:
        query = query.where(Conversation.arm == arm)

    with get_session() as session:
        rows = session.exec(query.offset(offset).limit(limit)).all()
    return [row.model_dump(mode="json") for row in rows]


@app.get("/api/health")
def health() -> dict:
    corpus_hash, articles, chunks = corpus.stats()
    resolved = config_client.resolve("health-check")
    return {
        "status": "ok",
        "corpus_hash": corpus_hash,
        "article_count": articles,
        "chunk_count": chunks,
        "active_version_label": resolved.version_label,
        "model": llm.MODEL,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

if os.getenv("LOG_LEVEL", "").lower() == "debug":
    import logging

    logging.basicConfig(level=logging.DEBUG)
