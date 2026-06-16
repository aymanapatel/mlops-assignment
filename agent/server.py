"""FastAPI wrapper exposing the agent over HTTP.

Run:
    uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001

The /answer endpoint accepts {question, db, tags?} and returns the
agent's final SQL, the result rows, and per-iteration history.
"""
from __future__ import annotations

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()
if os.environ.get("LANGFUSE_BASE_URL") and not os.environ.get("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

from agent.graph import AgentState, graph  # noqa: E402

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "agent_server.log"

formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=[stream_handler, file_handler],
)
logger = logging.getLogger("agent.server")

# Langfuse callback handler. If keys are set we initialize it; failures
# are NOT swallowed - a misconfigured Langfuse should not silently
# produce zero traces.
_lf_handler: Any = None
if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
    # langfuse>=4 exposes the LangChain/LangGraph handler here.
    from langfuse.langchain import CallbackHandler

    _lf_handler = CallbackHandler()
    logger.info("Langfuse callback enabled host=%s", os.environ.get("LANGFUSE_HOST"))
else:
    logger.info("Langfuse callback disabled")


app = FastAPI()


class AnswerRequest(BaseModel):
    question: str
    db: str
    tags: dict[str, str] = Field(default_factory=dict)


class AnswerResponse(BaseModel):
    sql: str
    rows: list[list[Any]] | None
    iterations: int
    ok: bool
    error: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception path=%s method=%s client=%s",
        request.url.path,
        request.method,
        request.client.host if request.client else "unknown",
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


@app.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest) -> AnswerResponse:
    started = time.perf_counter()
    state = AgentState(question=req.question, db_id=req.db)
    trace_tags = [f"{key}:{value}" for key, value in req.tags.items()]
    config: dict[str, Any] = {
        "callbacks": [_lf_handler] if _lf_handler is not None else [],
        "metadata": req.tags,
        "tags": trace_tags,
    }
    logger.info(
        "answer.start db=%s tags=%s question=%r",
        req.db,
        req.tags,
        req.question[:300],
    )
    try:
        final = graph.invoke(state, config=config)
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        logger.exception(
            "answer.graph_failed db=%s tags=%s elapsed=%.3fs question=%r",
            req.db,
            req.tags,
            elapsed,
            req.question[:300],
        )
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    sql = final.get("sql", "")
    iteration = final.get("iteration", 0)
    history = final.get("history", [])
    execution = final.get("execution")
    elapsed = time.perf_counter() - started

    if execution is None:
        logger.error(
            "answer.no_execution db=%s tags=%s iterations=%s elapsed=%.3fs sql=%r history=%s",
            req.db,
            req.tags,
            iteration,
            elapsed,
            sql[:500],
            history,
        )
        return AnswerResponse(
            sql=sql,
            rows=None,
            iterations=iteration,
            ok=False,
            error="agent produced no execution result",
            history=history,
        )
    if not execution.ok:
        logger.warning(
            "answer.execution_failed db=%s tags=%s iterations=%s elapsed=%.3fs error=%r sql=%r",
            req.db,
            req.tags,
            iteration,
            elapsed,
            execution.error,
            sql[:500],
        )
        return AnswerResponse(
            sql=sql,
            rows=None,
            iterations=iteration,
            ok=False,
            error=execution.error,
            history=history,
        )

    logger.info(
        "answer.ok db=%s tags=%s iterations=%s rows=%s elapsed=%.3fs sql=%r",
        req.db,
        req.tags,
        iteration,
        len(execution.rows or []),
        elapsed,
        sql[:500],
    )
    return AnswerResponse(
        sql=sql,
        rows=[list(r) for r in (execution.rows or [])],
        iterations=iteration,
        ok=True,
        history=history,
    )
