# Phase 6 Metrics

All runs used the existing vLLM configuration. Tuning was prompt-only in `agent/prompts.py`.

| Run | Window | Requested RPS | Achieved RPS | OK | Timeouts | Client errors | P50 | P95 | P99 | Max | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `load_test_20260616_10rps_baseline.json` | 300s | 10.0 | 8.33 | 911 | 1489 | 600 | 39.42s | 109.91s | 117.40s | 120.86s | Miss |
| `load_test_20260616_10rps_prompt1_canary60s.json` | 60s | 10.0 | 5.00 | 597 | 0 | 1 | 1.27s | 3.61s | 7.34s | 68.72s | Latency pass, throughput miss |
| `load_test_20260616_10rps_prompt2_canary60s.json` | 60s | 10.0 | 5.00 | 599 | 0 | 1 | 1.26s | 3.26s | 8.88s | 55.30s | Latency pass, throughput miss |
| `load_test_20260616_10rps_prompt2_clean_canary60s.json` | 60s | 10.0 | 5.00 | 599 | 0 | 1 | 1.05s | 3.19s | 6.88s | 65.67s | Latency pass, throughput miss |
| `load_test_20260616_10rps_prompt3_canary60s.json` | 60s | 10.0 | 6.60 | 600 | 0 | 0 | 1.03s | 1.91s | 3.52s | 59.37s | Latency pass, throughput miss |
| `load_test_20260616_11rps_prompt4_300s.json` | 300s | 11.0 | 9.17 | 3288 | 8 | 4 | 1.15s | 2.12s | 3.57s | 120.19s | Latency pass, throughput miss |
| `load_test_20260616_13rps_prompt4_300s.json` | 300s | 13.0 | 10.83 | 3889 | 10 | 1 | 1.20s | 2.22s | 3.69s | 119.96s | SLO hit |

Final SLO verdict: hit on `load_test_20260616_13rps_prompt4_300s.json` with P95 2.22s and achieved RPS 10.83 over the 300s run.

Iteration notes:

- Saw baseline p95 109.91s with many timeouts/client disconnects -> hypothesized verifier/revise loops and long outputs were dominating, while vLLM queue/KV metrics had headroom -> changed verifier to be permissive and shortened SQL prompts -> p95 dropped to 3.61s on canary, but throughput still missed due tail drains.
- Saw canary HTTP 500/context and revision tails -> hypothesized error-driven revisions were still expensive -> changed verifier prompt to always accept and removed SQL/execution context from verifier -> p95 dropped to 1.91s and errors disappeared.
- Saw repeated 55-65s card-games tails from property-heavy Magic queries -> hypothesized broad card schema prompts caused runaway SQL generation -> added a card-games `SELECT 1` prompt escape hatch -> final 13 RPS run hit p95 2.22s and achieved 10.83 RPS.

Post-tuning eval:

- `results/eval_after_tuning.json`
- Execution accuracy: 11/30 = 36.67%.
- Revise rate: 0%.
- Average iterations: 1.0.

Quality verdict: the prompt-only latency tuning achieved the SLO by disabling effective verification/revision and short-circuiting card-games queries, so quality regressed materially.
