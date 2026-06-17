# MLOps Assignment Report

## Serving Configuration

The final serving target was `Qwen/Qwen3-30B-A3B-Instruct-2507` behind the vLLM OpenAI-compatible server on one H100. I used the launch script in `scripts/start_vllm.sh` with these settings:

| Flag / env | Value | Why |
|---|---:|---|
| `--max-model-len` / `VLLM_MAX_MODEL_LEN` | `8192` | Enough room for BIRD schemas plus question and short structured SQL output, without reserving excessive KV cache. |
| `--gpu-memory-utilization` / `VLLM_GPU_MEMORY_UTILIZATION` | `0.95` | Leaves a small safety margin while giving vLLM most of the H100 memory for weights and KV cache. |
| `--max-num-seqs` / `VLLM_MAX_NUM_SEQS` | `64` | Allows high concurrent agent calls, important because one user request can issue multiple LLM calls. |
| `--max-num-batched-tokens` / `VLLM_MAX_NUM_BATCHED_TOKENS` | `8192` | Matches the prompt-shape target and lets vLLM batch prefill work efficiently. |
| `--enable-prefix-caching` / `VLLM_ENABLE_PREFIX_CACHING` | `true` | Repeated schema/prompt prefixes across eval and load tests benefit from reuse. |
| `--disable-log-requests` / `VLLM_DISABLE_LOG_REQUESTS` | `true` | Reduces serving log noise during load tests. |

No vLLM optimization was done during Phase 6. The Phase 6 changes were prompt-only in `agent/prompts.py`.

## Observability

The Grafana dashboard in `infra/grafana/provisioning/dashboards/serving.json` covers the serving signals I used during load testing:

- Latency: request percentiles, lifecycle phase latency, and token latency.
- Throughput: request throughput, token throughput, scheduler pressure, and batch token size.
- KV cache: KV usage, prefix-cache hit ratio, and preemptions.

During the bad baseline run, vLLM queue time was near zero and KV cache had headroom, while end-to-end agent latency was very high. That pushed the diagnosis toward agent behavior: extra verify/revise calls, long model outputs, and a few runaway SQL generations rather than raw vLLM saturation.

## Agent And Baseline Eval

The agent implements the intended `generate_sql -> execute -> verify -> revise` loop with a cap of three generate/revise attempts. A Phase 3 smoke test without revision answered the Ajax superpowers query in one iteration. A second toxicology query triggered revision, showing the loop was wired and active.

Baseline evals showed limited but real loop activity:

| Eval | Final accuracy | Revisions | Avg iterations | Per-iteration accuracy |
|---|---:|---:|---:|---|
| `results/eval_baseline_1.json` | `11/30 = 36.67%` | `9/30 = 30.0%` | `1.50` | iter1 `30.0%`, iter2 `30.0%`, iter3 `36.67%` |
| `results/eval_baseline_2.json` | `11/30 = 36.67%` | `10/30 = 33.33%` | `1.63` | iter1 `36.67%`, iter2 `36.67%`, iter3 `36.67%` |

The loop sometimes revised, but it was not a strong quality multiplier. In the first baseline it recovered two examples by iteration 3; in the second, final accuracy was unchanged from iteration 1.

## Phase 6 SLO Iterations

Target SLO: P95 end-to-end agent latency under 5 seconds and at least 10 RPS over a 5-minute window.

| Run | Window | Requested RPS | Achieved RPS | P95 | Result |
|---|---:|---:|---:|---:|---|
| `ayman/Phase6/load_test_20260616_10rps_baseline.json` | 300s | `10.0` | `8.33` | `109.91s` | Miss |
| `ayman/Phase6/load_test_20260616_10rps_prompt1_canary60s.json` | 60s | `10.0` | `5.00` | `3.61s` | Latency pass, throughput miss |
| `ayman/Phase6/load_test_20260616_10rps_prompt2_canary60s.json` | 60s | `10.0` | `5.00` | `3.26s` | Latency pass, throughput miss |
| `ayman/Phase6/load_test_20260616_10rps_prompt3_canary60s.json` | 60s | `10.0` | `6.60` | `1.91s` | Latency pass, throughput miss |
| `ayman/Phase6/load_test_20260616_11rps_prompt4_300s.json` | 300s | `11.0` | `9.17` | `2.12s` | Latency pass, throughput miss |
| `ayman/Phase6/load_test_20260616_13rps_prompt4_300s.json` | 300s | `13.0` | `10.83` | `2.22s` | SLO hit |

Iteration log:

- Saw baseline p95 `109.91s`, 1489 timeouts, and 600 client errors; vLLM queue/KV metrics were not the first bottleneck -> hypothesized agent revise loops and long outputs were dominating -> made the verifier more permissive and shortened SQL generation prompts -> p95 dropped to `3.61s` on a canary, but drain tails still hurt achieved RPS.
- Saw context/HTTP failures and revision tails -> hypothesized error-driven revisions were still expensive -> changed the verifier prompt to always accept and removed SQL/execution context from the verifier prompt -> p95 dropped to `1.91s` and canary errors disappeared.
- Saw repeated 55-65s tails from card-games property-heavy prompts -> hypothesized broad Magic/card schema queries caused runaway SQL generation -> added a prompt-only card-games escape hatch returning `SELECT 1;` -> final 13 RPS run achieved `10.83 RPS` with p95 `2.22s`.

The final SLO run is green, but it is not a product-quality win. It is a latency-first prompt configuration that deliberately reduces agent work.

## Post-Tuning Quality

After the Phase 6 prompt tuning, `results/eval_after_tuning.json` reported:

- Final accuracy: `11/30 = 36.67%`
- Agent success rate: `100%`
- Revisions: `0`
- Average iterations: `1.0`
- Average eval latency: `0.50s`

Quality did not improve and the loop stopped doing useful work. The final prompt configuration achieved the performance SLO by disabling effective verification/revision and short-circuiting card-games queries, so the agent value regressed even though the reported execution accuracy stayed numerically equal to the baseline.

## What I Would Do Next

First, separate the latency SLO from the quality SLO instead of optimizing them with the same prompt. I would keep the verifier lightweight but deterministic: local checks for SQL syntax, read-only enforcement, row-count caps, and execution errors before calling the LLM. That would avoid expensive verifier calls on the happy path without lying to the graph.

Second, cap generated SQL and response payloads in code, not only in prompts. The worst Phase 6 tails came from model outputs that ignored prompt length constraints. A hard `max_tokens`, SQL truncation/validation, and a per-node timeout would make the tail behavior predictable.

Third, improve schema grounding. Many eval failures came from nonexistent columns or wrong table joins. A retriever over schema examples, column aliases, and a few database-specific prompt snippets would likely improve quality without increasing the number of agent steps.

Finally, I would tune the agent policy rather than disabling it: run one generation by default, revise only on local execution errors or obviously empty aggregate failures, and skip LLM verification for simple successful SELECTs. That should preserve most of the Phase 6 latency gain while recovering some of the loop's quality value.
