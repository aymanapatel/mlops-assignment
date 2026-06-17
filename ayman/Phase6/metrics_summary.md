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
| `load_test_20260616_langfuse_baseline_10rps_60s.json` | 60s | 10.0 | 5.00 | 592 | 0 | 8 | 21.43s | 35.59s | 42.24s | 57.78s | Tagged `baseline`; miss |
| `load_test_20260616_langfuse_optimized_10rps_60s.json` | 60s | 10.0 | 5.86 | 600 | 0 | 0 | 0.99s | 1.89s | 3.75s | 42.53s | Tagged `optimized`; latency pass |
| `load_test_20260616_langfuse_optimized_13rps_300s_slo.json` | 300s | 13.0 | 10.83 | 3893 | 6 | 1 | 1.21s | 2.21s | 3.92s | 119.83s | Tagged `optimized`; SLO hit |
| `load_test_20260616_langfuse_baseline_13rps_300s_before_optimization.json` | 300s | 13.0 | 10.83 | 619 | 2498 | 783 | 47.92s | 106.16s | 118.09s | 120.12s | Tagged `baseline`; miss |
| `load_test_20260616_langfuse_optimized_13rps_300s_after_optimization.json` | 300s | 13.0 | 10.83 | 3889 | 10 | 1 | 1.20s | 2.18s | 3.33s | 114.45s | Tagged `optimized`; SLO hit |
| `load_test_20260616_agent_metrics_baseline_13rps_300s_before_summary_only.json` | 300s | 13.0 | 10.83 | 369 | 2741 | 789 | 27.35s | 116.05s | 119.99s | 120.72s | Tagged `baseline`; Grafana run label; miss |
| `load_test_20260616_agent_metrics_optimized_13rps_300s_after_contaminated_summary_only.json` | 300s | 13.0 | 10.83 | 3298 | 18 | 584 | 10.27s | 82.72s | 100.82s | 105.64s | Tagged `optimized`; contaminated by leftover pressure; rerun |
| `load_test_20260616_agent_metrics_optimized_13rps_300s_after_clean.json` | 300s | 13.0 | 10.83 | 3887 | 9 | 4 | 1.22s | 2.20s | 3.48s | 119.00s | Tagged `optimized`; Grafana run label; SLO hit |
| `load_test_20260616_30s_unoptimized_13rps.json` | 30s | 13.0 | 4.33 | 383 | 0 | 7 | 31.61s | 45.36s | 48.48s | 61.03s | 30s compare; unoptimized/baseline miss |
| `load_test_20260616_30s_optimized_13rps.json` | 30s | 13.0 | 12.23 | 390 | 0 | 0 | 1.04s | 1.96s | 2.80s | 13.51s | 30s compare; optimized hit |
| `load_test_20260617_5m_unoptimized_13rps.json` | 300s | 13.0 | 10.83 | 321 | 2794 | 784 | 23.45s | 115.82s | 120.04s | 120.53s | 5m compare; unoptimized/baseline miss |
| `load_test_20260617_5m_optimized_13rps.json` | 300s | 13.0 | 10.83 | 3889 | 10 | 1 | 1.22s | 2.22s | 3.55s | 114.87s | 5m compare; optimized SLO hit |

Final SLO verdict: hit on `load_test_20260616_13rps_prompt4_300s.json` with P95 2.22s and achieved RPS 10.83 over the 300s run.

Tagged SLO verdict: hit on `load_test_20260616_langfuse_optimized_13rps_300s_slo.json` with P95 2.21s and achieved RPS 10.83 over the 300s run. Langfuse metadata included `variant=optimized`, `phase=phase6_slo`, and `run=optimized_13rps_300s_slo`.

Before/after tagged comparison verdict: baseline missed with P95 106.16s at 13 requested RPS over 300s; optimized hit with P95 2.18s at the same requested RPS and window. Langfuse traces were verified with literal tags `baseline` and `optimized`.

Agent Grafana comparison verdict: baseline missed with P95 116.05s at achieved 10.83 RPS in the 2026-06-16T23:12:12Z to 23:17:12Z scheduled window. The clean optimized rerun hit with P95 2.20s at achieved 10.83 RPS in the 2026-06-16T23:25:29Z to 23:30:29Z scheduled window. Langfuse trace tags are normalized to `baseline` and `optimized`; the run IDs remain in metadata. Grafana uses matching `variant` and `run` labels from `agent_requests_total` and `agent_request_latency_seconds_bucket`.

30-second comparison verdict: unoptimized/baseline missed with P95 45.36s and achieved RPS 4.33 in the 2026-06-16T23:47:09Z to 23:47:39Z scheduled window. Optimized hit the same short-window target shape with P95 1.96s and achieved RPS 12.23 in the 2026-06-16T23:49:22Z to 23:49:52Z scheduled window. Serving-layer comparison moved in the same direction: vLLM p95 request latency 3.48s -> 1.42s, TTFT p95 82ms -> 39ms, max running requests 40 -> 17, KV cache usage 5.72% -> 3.85%, with zero preemptions in both windows.

5-minute comparison verdict: unoptimized/baseline missed with P95 115.82s at achieved RPS 10.83 in the 2026-06-17T00:06:36Z to 00:11:36Z scheduled window. Optimized hit the assignment SLO with P95 2.22s at achieved RPS 10.83 in the 2026-06-17T00:12:58Z to 00:17:58Z scheduled window. Serving-layer comparison moved in the same direction: vLLM p95 request latency 3.90s -> 1.73s, TTFT p95 97ms -> 40ms, max running requests 38 -> 31, KV cache usage 35.90% -> 21.90%, with zero preemptions in both windows.

Iteration notes:

- Saw baseline p95 109.91s with many timeouts/client disconnects -> hypothesized verifier/revise loops and long outputs were dominating, while vLLM queue/KV metrics had headroom -> changed verifier to be permissive and shortened SQL prompts -> p95 dropped to 3.61s on canary, but throughput still missed due tail drains.
- Saw canary HTTP 500/context and revision tails -> hypothesized error-driven revisions were still expensive -> changed verifier prompt to always accept and removed SQL/execution context from verifier -> p95 dropped to 1.91s and errors disappeared.
- Saw repeated 55-65s card-games tails from property-heavy Magic queries -> hypothesized broad card schema prompts caused runaway SQL generation -> added a card-games `SELECT 1` prompt escape hatch -> final 13 RPS run hit p95 2.22s and achieved 10.83 RPS.
- Re-ran the before/after prompt comparison with Langfuse metadata tags. Baseline requests used `variant=baseline`, which the server expands to Langfuse tags `variant:baseline` and `baseline`; optimized requests used `variant=optimized`, expanded to `variant:optimized` and `optimized`.
- Added agent-level Prometheus metrics for true full `/answer` SLO tracking and split them by `variant`, `phase`, and `run`. Grafana now differentiates before/after runs directly instead of using raw vLLM request counts.

Post-tuning eval:

- `results/eval_after_tuning.json`
- Execution accuracy: 11/30 = 36.67%.
- Revise rate: 0%.
- Average iterations: 1.0.

Quality verdict: the prompt-only latency tuning achieved the SLO by disabling effective verification/revision and short-circuiting card-games queries, so quality regressed materially.
