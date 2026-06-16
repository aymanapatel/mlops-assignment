# Home Assignment: Code Changes Summary

## Files to modify

| File | What to do | Phase |
|------|-----------|-------|
| `scripts/start_vllm.sh` | Add optimized vLLM flags (tensor-parallel, max-model-len, gpu-memory-utilization, kv-cache-dtype, chunked-prefill, max-num-seqs, etc.) | 1 |
| `infra/grafana/provisioning/dashboards/serving.json` | Add latency (P50/P95/P99), throughput, and KV cache panels | 2 |
| `agent/prompts.py` | Fill in all 6 prompt templates (GENERATE_SQL_SYSTEM, GENERATE_SQL_USER, VERIFY_SYSTEM, VERIFY_USER, REVISE_SYSTEM, REVISE_USER) | 3 |
| `agent/graph.py` | Implement `verify_node`, `revise_node`, `route_after_verify` | 3 |
| `evals/run_eval.py` | Implement `eval_one` (HTTP call + execution accuracy) and `summarize` (per-iteration carry-forward) | 5 |
| `REPORT.md` | Create and write the final report (config, baseline, SLO iteration log, agent value, next steps) | 7 |
| `.env` | Fill in HF_TOKEN, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY | 0, 4 |

---

## Detailed breakdown

### Phase 1: vLLM serving
- **File**: `scripts/start_vllm.sh`
- The current script only has `--model`, `--host`, `--port`.
- You need to add optimization flags for the workload (Qwen3-30B-A3B on 1x H100, 1.5-3K token prompts, short outputs, 2-3 dependent calls per request).
- Examples: `--tensor-parallel-size`, `--max-model-len`, `--gpu-memory-utilization`, `--kv-cache-dtype`, `--enable-chunked-prefill`, `--max-num-seqs`, quantization flags, etc.

### Phase 2: Grafana dashboard
- **File**: `infra/grafana/provisioning/dashboards/serving.json`
- Current: 2 starter panels (Requests running, Generated tokens/sec).
- Need to add panels covering:
  - **Latency**: P50, P95, P99 from `vllm:request_latency_seconds`, `vllm:time_to_first_token_seconds`, etc.
  - **Throughput**: requests/s, queue depth, generation rate.
  - **KV cache**: utilization / headroom metrics (e.g., `vllm:gpu_cache_usage_perc`, `vllm:num_cache_blocks`).

### Phase 3: Agent implementation
- **Files**: `agent/prompts.py`, `agent/graph.py`
- **prompts.py**: Fill in all 6 prompt templates (currently empty strings).
  - `GENERATE_SQL_SYSTEM` / `GENERATE_SQL_USER`: Guide model to produce SQL from schema + question.
  - `VERIFY_SYSTEM` / `VERIFY_USER`: Ask whether execution result answers the question; ask for `{"ok": bool, "issue": str}`.
  - `REVISE_SYSTEM` / `REVISE_USER`: Include failing SQL, execution result, and verifier complaint; guide model to fix it.
- **graph.py**: Implement three stub functions:
  1. `verify_node(state)`: Build verify prompt, call llm(), parse `{"ok": bool, "issue": str}`, return `{"verify_ok": ..., "verify_issue": ...}`.
  2. `revise_node(state)`: Build revise prompt with failure info, call llm(), extract SQL, return `{"sql": ..., "iteration": +1, "history": ...}`.
  3. `route_after_verify(state)`: Return `"end"` if `verify_ok` or `iteration >= MAX_ITERATIONS`, else `"revise"`.

### Phase 4: Agent observability (Langfuse)
- **Files**: `agent/server.py`, `.env`
- `server.py` already has callback handler wiring; just ensure you send tags in requests.
- `.env`: Fill in `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (get them from local Langfuse UI at http://localhost:3001).

### Phase 5: Eval runner
- **File**: `evals/run_eval.py`
- Implement `eval_one(question, agent_url)`:
  - Call agent via HTTP (`httpx.post(agent_url, json={...})`).
  - Capture final SQL and iteration count.
  - Run agent SQL and gold SQL against sqlite using `run_sql()`.
  - Compare canonicalized results with `matches()`.
  - Return dict with per-iteration results.
- Implement `summarize(results)`:
  - Aggregate overall pass rate and per-iteration pass rates (carry-forward: if agent stopped at iteration j, treat as result for all later iterations).
  - Return summary dict.

### Phase 6: SLO tuning
- **File**: `scripts/start_vllm.sh` (iterate config)
- Run `load_test/driver.py` with different `--rps` values to measure latency.
- Run `evals/run_eval.py` after each tuning change to confirm quality (save to `results/eval_after_tuning.json`).
- Document each iteration in `REPORT.md`.

### Phase 7: Report
- **File**: `REPORT.md` (create it)
- Content:
  1. vLLM flags + one-line justification each.
  2. Baseline eval results (overall + per-iteration pass rates).
  3. SLO iteration log: *"saw X -> hypothesized Y -> changed Z -> result was W"*.
  4. Agent value paragraph (cite per-iteration pass rate).
  5. What you'd do with more time (specific, not "add Kubernetes").

