"""Eval runner using execution accuracy.

Reads evals/eval_set.jsonl, calls the agent at AGENT_URL on each question,
then compares the agent's SQL output to the gold SQL by *executed rows*
(canonicalized: sorted, stringified, None-coerced to empty).

Helpers (run_sql / canonicalize / matches) are provided. You implement
eval_one() and summarize().

Run:
    uv run python evals/run_eval.py --out results/eval_baseline.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx

from agent.graph import MAX_ITERATIONS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_FILE = ROOT / "evals" / "eval_set.jsonl"
DEFAULT_OUT_FILE = ROOT / "results" / "eval_baseline.json"
DB_DIR = ROOT / "data" / "bird"
AGENT_URL_DEFAULT = "http://localhost:8001/answer"


# ---------- Helpers (provided) -----------------------------------------

def run_sql(db_id: str, sql: str, timeout: float = 5.0) -> tuple[bool, list[tuple] | None, str | None]:
    """Run sql against db_id in read-only mode. Returns (ok, rows, error)."""
    path = DB_DIR / f"{db_id}.sqlite"
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout) as conn:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            return True, rows, None
    except Exception as e:  # noqa: BLE001
        return False, None, f"{type(e).__name__}: {e}"


def canonicalize(rows: list[tuple] | None) -> list[tuple] | None:
    """Sort rows; coerce cells to str; None -> ''."""
    if rows is None:
        return None
    return sorted(tuple("" if c is None else str(c) for c in row) for row in rows)


def matches(gold_rows: list[tuple] | None, pred_rows: list[tuple] | None) -> bool:
    if gold_rows is None or pred_rows is None:
        return False
    return canonicalize(gold_rows) == canonicalize(pred_rows)


# ---------- Implement these (Phase 5) ----------------------------------

def eval_one(question: dict, agent_url: str) -> dict:
    """Score one question. Return a dict capturing per-iteration correctness."""
    db_id = question["db_id"]
    question_text = question["question"]
    gold_sql = question["gold_sql"]

    gold_ok, gold_rows, gold_error = run_sql(db_id, gold_sql)
    started = time.monotonic()

    result: dict[str, Any] = {
        "question": question_text,
        "db_id": db_id,
        "gold_sql": gold_sql,
        "gold_ok": gold_ok,
        "gold_error": gold_error,
        "agent_ok": False,
        "agent_error": None,
        "agent_sql": "",
        "iterations": 0,
        "latency_seconds": None,
        "history": [],
        "attempts": [],
        "final_correct": False,
    }

    if not gold_ok:
        result["agent_error"] = f"gold SQL failed: {gold_error}"
        result["latency_seconds"] = time.monotonic() - started
        return result

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                agent_url,
                json={
                    "question": question_text,
                    "db": db_id,
                    "tags": {
                        "phase": "phase5",
                        "run": "eval_baseline",
                        "db": db_id,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as e:  # noqa: BLE001
        result["agent_error"] = f"{type(e).__name__}: {e}"
        result["latency_seconds"] = time.monotonic() - started
        return result

    result["latency_seconds"] = time.monotonic() - started
    result["agent_ok"] = bool(payload.get("ok", False))
    result["agent_error"] = payload.get("error")
    result["agent_sql"] = payload.get("sql", "")
    result["iterations"] = int(payload.get("iterations", 0) or 0)
    result["history"] = payload.get("history", [])

    sql_attempts = [
        h["sql"]
        for h in result["history"]
        if h.get("node") in {"generate_sql", "revise"} and h.get("sql")
    ]
    if not sql_attempts and result["agent_sql"]:
        sql_attempts = [result["agent_sql"]]

    for idx, sql in enumerate(sql_attempts, 1):
        pred_ok, pred_rows, pred_error = run_sql(db_id, sql)
        correct = pred_ok and matches(gold_rows, pred_rows)
        result["attempts"].append({
            "iteration": idx,
            "sql": sql,
            "ok": pred_ok,
            "error": pred_error,
            "correct": correct,
        })

    if result["attempts"]:
        result["final_correct"] = bool(result["attempts"][-1]["correct"])

    return result


def summarize(results: list[dict]) -> dict:
    """Aggregate per-question results.

    Per-iteration carry-forward: if the agent terminated at iteration j < k
    (verify said ok at j, or it hit MAX_ITERATIONS at j < k), treat the
    question's iteration-k result as identical to its iteration-j result.
    The agent stopped emitting; whatever it had at termination is what
    would have been served had we polled at iteration k.
    """
    total = len(results)
    if total == 0:
        return {
            "total": 0,
            "final_correct": 0,
            "final_accuracy": 0.0,
            "per_iteration": {},
        }

    final_correct = sum(1 for r in results if r.get("final_correct"))
    agent_success = sum(1 for r in results if r.get("agent_ok"))
    revised = sum(
        1
        for r in results
        if any(h.get("node") == "revise" for h in r.get("history", []))
    )
    latencies = [
        float(r["latency_seconds"])
        for r in results
        if r.get("latency_seconds") is not None
    ]
    iterations = [int(r.get("iterations", 0) or 0) for r in results]

    per_iteration: dict[str, dict[str, float | int]] = {}
    for k in range(1, MAX_ITERATIONS + 1):
        correct = 0
        attempted = 0
        for r in results:
            attempts = r.get("attempts", [])
            if not attempts:
                continue
            attempted += 1
            carried_attempt = attempts[min(k, len(attempts)) - 1]
            if carried_attempt.get("correct"):
                correct += 1
        per_iteration[str(k)] = {
            "correct": correct,
            "attempted": attempted,
            "total": total,
            "accuracy": correct / total,
        }

    return {
        "total": total,
        "agent_success": agent_success,
        "agent_success_rate": agent_success / total,
        "final_correct": final_correct,
        "final_accuracy": final_correct / total,
        "revised": revised,
        "revise_rate": revised / total,
        "avg_iterations": sum(iterations) / total,
        "max_iterations": max(iterations) if iterations else 0,
        "avg_latency_seconds": sum(latencies) / len(latencies) if latencies else None,
        "per_iteration": per_iteration,
    }


# ---------- Main (provided) --------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_FILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_FILE)
    parser.add_argument("--agent-url", default=AGENT_URL_DEFAULT)
    args = parser.parse_args()

    questions = [json.loads(line) for line in args.eval_set.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(questions)} eval questions from {args.eval_set}")

    results: list[dict] = []
    t0 = time.monotonic()
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['db_id']}: {q['question'][:60]}...", flush=True)
        results.append(eval_one(q, args.agent_url))
    elapsed = time.monotonic() - t0

    summary = summarize(results)
    out = {
        "summary": summary,
        "wall_clock_seconds": elapsed,
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
