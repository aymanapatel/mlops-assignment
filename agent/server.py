"""FastAPI wrapper exposing the agent over HTTP.

Run:
    uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001

The /answer endpoint accepts {question, db, tags?} and returns the
agent's final SQL, the result rows, and per-iteration history.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
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

_METRIC_BUCKETS = (
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    4.0,
    5.0,
    7.5,
    10.0,
    15.0,
    30.0,
    60.0,
    120.0,
)
_metrics_lock = threading.Lock()
_request_counts: dict[tuple[str, str, str, str], int] = {}
_latency_bucket_counts: dict[tuple[str, str, str, str], dict[float, int]] = {}
_latency_counts: dict[tuple[str, str, str, str], int] = {}
_latency_sums: dict[tuple[str, str, str, str], float] = {}


def _metric_label(value: str | None) -> str:
    return (value or "none").replace("\\", "\\\\").replace('"', '\\"').replace("\n", "_")


def _normalize_tags(tags: dict[str, str]) -> dict[str, str]:
    normalized = dict(tags)
    if normalized.get("variant") == "unoptimized":
        normalized["variant"] = "baseline"
    if "run" in normalized:
        normalized["run"] = normalized["run"].replace("unoptimized", "baseline")
    return normalized


def _trace_tags(tags: dict[str, str]) -> list[str]:
    variant = tags.get("variant")
    if variant in {"baseline", "optimized"}:
        return [variant]
    return []


def _metric_key(status: str, tags: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        status,
        _metric_label(tags.get("variant")),
        _metric_label(tags.get("phase")),
        _metric_label(tags.get("run")),
    )


def _label_string(key: tuple[str, str, str, str]) -> str:
    status, variant, phase, run = key
    return f'status="{status}",variant="{variant}",phase="{phase}",run="{run}"'


def _record_agent_request(status: str, latency_seconds: float, tags: dict[str, str]) -> None:
    key = _metric_key(status, tags)
    with _metrics_lock:
        _request_counts[key] = _request_counts.get(key, 0) + 1
        _latency_counts[key] = _latency_counts.get(key, 0) + 1
        _latency_sums[key] = _latency_sums.get(key, 0.0) + latency_seconds
        bucket_counts = _latency_bucket_counts.setdefault(
            key,
            {bucket: 0 for bucket in _METRIC_BUCKETS},
        )
        for bucket in _METRIC_BUCKETS:
            if latency_seconds <= bucket:
                bucket_counts[bucket] += 1


def _render_agent_metrics() -> str:
    with _metrics_lock:
        counts = dict(_request_counts)
        buckets = {key: dict(value) for key, value in _latency_bucket_counts.items()}
        latency_counts = dict(_latency_counts)
        latency_sums = dict(_latency_sums)

    lines = [
        "# HELP agent_requests_total Full end-to-end agent /answer requests.",
        "# TYPE agent_requests_total counter",
    ]
    if not counts:
        empty_key = ("ok", "none", "none", "none")
        lines.append(f"agent_requests_total{{{_label_string(empty_key)}}} 0")
    for key, count in sorted(counts.items()):
        lines.append(f"agent_requests_total{{{_label_string(key)}}} {count}")

    lines.extend([
        "# HELP agent_request_latency_seconds Full end-to-end agent /answer latency in seconds.",
        "# TYPE agent_request_latency_seconds histogram",
    ])
    metric_keys = sorted(set(buckets) | set(latency_counts))
    if not metric_keys:
        metric_keys = [("ok", "none", "none", "none")]
        buckets[metric_keys[0]] = {bucket: 0 for bucket in _METRIC_BUCKETS}
        latency_counts[metric_keys[0]] = 0
        latency_sums[metric_keys[0]] = 0.0
    for key in metric_keys:
        label_string = _label_string(key)
        bucket_counts = buckets.get(key, {bucket: 0 for bucket in _METRIC_BUCKETS})
        count = latency_counts.get(key, 0)
        for bucket in _METRIC_BUCKETS:
            lines.append(
                f'agent_request_latency_seconds_bucket{{{label_string},le="{bucket}"}} '
                f"{bucket_counts.get(bucket, 0)}"
            )
        lines.append(f'agent_request_latency_seconds_bucket{{{label_string},le="+Inf"}} {count}')
        lines.append(f"agent_request_latency_seconds_count{{{label_string}}} {count}")
        lines.append(f"agent_request_latency_seconds_sum{{{label_string}}} {latency_sums.get(key, 0.0)}")
    return "\n".join(lines) + "\n"


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


@app.get("/metrics")
def metrics() -> Response:
    return Response(_render_agent_metrics(), media_type="text/plain; version=0.0.4")


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
    tags = _normalize_tags(req.tags)
    config: dict[str, Any] = {
        "callbacks": [_lf_handler] if _lf_handler is not None else [],
        "metadata": tags,
        "tags": _trace_tags(tags),
    }
    logger.info(
        "answer.start db=%s tags=%s question=%r",
        req.db,
        tags,
        req.question[:300],
    )
    try:
        final = graph.invoke(state, config=config)
    except Exception as e:  # noqa: BLE001
        elapsed = time.perf_counter() - started
        _record_agent_request("error", elapsed, tags)
        logger.exception(
            "answer.graph_failed db=%s tags=%s elapsed=%.3fs question=%r",
            req.db,
            tags,
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
        _record_agent_request("error", elapsed, tags)
        logger.error(
            "answer.no_execution db=%s tags=%s iterations=%s elapsed=%.3fs sql=%r history=%s",
            req.db,
            tags,
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
        _record_agent_request("error", elapsed, tags)
        logger.warning(
            "answer.execution_failed db=%s tags=%s iterations=%s elapsed=%.3fs error=%r sql=%r",
            req.db,
            tags,
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
        tags,
        iteration,
        len(execution.rows or []),
        elapsed,
        sql[:500],
    )
    _record_agent_request("ok", elapsed, tags)
    return AnswerResponse(
        sql=sql,
        rows=[list(r) for r in (execution.rows or [])],
        iterations=iteration,
        ok=True,
        history=history,
    )
