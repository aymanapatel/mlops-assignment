# Commands

Run repo commands from:

```bash
cd /home/ayman/mlops-assignment
```

## Phase 0 - Setup

Forward ports from laptop to VM:

```bash
ssh -L 3000:localhost:3000 \
    -L 9090:localhost:9090 \
    -L 3001:localhost:3001 \
    -L 8000:localhost:8000 \
    -L 8001:localhost:8001 \
    <user>@<vm-host>
```

Install dependencies and create env:

```bash
uv sync
cp .env.example .env
```

Install Python headers needed by vLLM/Triton:

```bash
sudo apt-get update
sudo apt-get install -y python3.12-dev
```

Load BIRD data:

```bash
uv run python scripts/load_data.py
```

Start observability stack:

```bash
docker compose up -d
```

If Docker permissions fail:

```bash
sudo docker compose up -d
```

Check UIs:

```bash
curl http://localhost:9090/-/healthy
curl http://localhost:3000
curl http://localhost:3001
```

Safe stop without deleting volumes:

```bash
docker compose down
```

Do not use this if you want to keep Langfuse/Grafana/Prometheus data:

```bash
docker compose down -v
```

## Phase 1 - vLLM

Set `.env` values:

```bash
HF_TOKEN=<your_huggingface_token>
VLLM_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
VLLM_MAX_MODEL_LEN=8192
VLLM_GPU_MEMORY_UTILIZATION=0.95
VLLM_MAX_NUM_SEQS=64
VLLM_MAX_NUM_BATCHED_TOKENS=8192
VLLM_ENABLE_PREFIX_CACHING=true
VLLM_DISABLE_LOG_REQUESTS=true
```

Start vLLM:

```bash
bash scripts/start_vllm.sh
```

Check model endpoint:

```bash
curl http://localhost:8000/v1/models
```

Manual text-to-SQL request:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "messages": [
      {
        "role": "user",
        "content": "Convert this question to SQLite SQL only. Question: How many users received commentator badges in 2014?"
      }
    ],
    "temperature": 0,
    "max_tokens": 256
  }' | jq
```

Check vLLM metrics:

```bash
curl http://localhost:8000/metrics | head
curl http://localhost:8000/metrics | rg 'vllm:'
```

## Phase 2 - Grafana / Prometheus

Restart Grafana after editing provisioned dashboard JSON:

```bash
docker compose restart grafana
```

If Docker permissions fail:

```bash
sudo docker compose restart grafana
```

Validate dashboard JSON:

```bash
jq empty infra/grafana/provisioning/dashboards/serving.json
jq '.panels | length' infra/grafana/provisioning/dashboards/serving.json
```

Check Prometheus can query vLLM:

```bash
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=sum(vllm:num_requests_running)' | jq
```

Validate every dashboard PromQL expression:

```bash
jq -r '.panels[].targets[]?.expr' infra/grafana/provisioning/dashboards/serving.json |
while IFS= read -r expr; do
  curl -G -s --data-urlencode "query=$expr" http://localhost:9090/api/v1/query |
    jq -e '.status == "success"' >/dev/null &&
    echo "OK: $expr" || echo "FAIL: $expr"
done
```

Open:

```text
http://localhost:3000
```

## Phase 3 - Agent

Start agent server:

```bash
uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001
```

Health check:

```bash
curl http://localhost:8001/health
```

Basic agent request:

```bash
curl http://localhost:8001/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "List down Ajax'\''s superpowers.",
    "db": "superhero"
  }' | jq
```

Check whether revise triggered:

```bash
curl -s http://localhost:8001/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Calculate the percentage of carcinogenic molecules which contain the Chlorine element.",
    "db": "toxicology"
  }' |
  jq '{iterations, revised: any(.history[]; .node == "revise"), history_nodes: [.history[].node]}'
```

Run a direct graph smoke test:

```bash
uv run python - <<'PY'
from agent.graph import AgentState, graph

final = graph.invoke(AgentState(
    question="What is the coordinates location of the circuits for Australian grand prix?",
    db_id="formula_1",
))
print("iterations:", final.get("iteration"))
print("verify_ok:", final.get("verify_ok"))
print("sql:", final.get("sql"))
print("history:", [h.get("node") for h in final.get("history", [])])
PY
```

## Phase 4 - Langfuse

Start stack if needed:

```bash
docker compose up -d
```

Open Langfuse and create project:

```text
http://localhost:3001
```

Set `.env` values:

```bash
LANGFUSE_PUBLIC_KEY=<pk-lf-...>
LANGFUSE_SECRET_KEY=<sk-lf-...>
LANGFUSE_HOST=http://localhost:3001
```

If using `LANGFUSE_BASE_URL`, the server maps it to `LANGFUSE_HOST`.

Restart agent server after changing `.env`:

```bash
uv run uvicorn agent.server:app --host 0.0.0.0 --port 8001
```

Send one tagged trace:

```bash
curl http://localhost:8001/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "List down Ajax'\''s superpowers.",
    "db": "superhero",
    "tags": {
      "phase": "phase4",
      "run": "manual-smoke",
      "model": "qwen3-30b",
      "config": "maxlen-32768"
    }
  }' | jq
```

Run the 10-question Phase 4 trace script:

```bash
./ayman/Phase4/curl_commands.sh
```

Responses are written to:

```bash
ls ayman/Phase4/responses
jq '{iterations, ok, history_nodes: [.history[].node]}' ayman/Phase4/responses/response_10.json
```

Filter Langfuse by tags:

```text
phase:phase4
run:langfuse-10q
question_index:10
```

## Phase 5 - Evals

Run the full baseline eval:

```bash
uv run python evals/run_eval.py --out results/eval_baseline.json
```

Run another eval output file:

```bash
uv run python evals/run_eval.py --out results/eval_baseline_1.json
```

Inspect summary:

```bash
jq '.summary' results/eval_baseline.json
```

Inspect failed cases:

```bash
jq -r '.results[] | select(.final_correct == false) |
  [.db_id, .iterations, .question, (.attempts[-1].sql // ""), (.attempts[-1].error // "")] |
  @tsv' results/eval_baseline.json
```

Run a tiny smoke eval:

```bash
head -n 3 evals/eval_set.jsonl > /tmp/eval_3.jsonl
uv run python evals/run_eval.py --eval-set /tmp/eval_3.jsonl --out /tmp/eval_3.json
jq '.summary' /tmp/eval_3.json
```

Run targeted eval rows:

```bash
printf '%s\n' \
  "$(sed -n '1p' evals/eval_set.jsonl)" \
  "$(sed -n '3p' evals/eval_set.jsonl)" \
  "$(sed -n '9p' evals/eval_set.jsonl)" \
  "$(sed -n '10p' evals/eval_set.jsonl)" \
  > /tmp/eval_prompt_fix.jsonl

uv run python evals/run_eval.py \
  --eval-set /tmp/eval_prompt_fix.jsonl \
  --out /tmp/eval_prompt_fix.json
```

## Phase 6 - Load Test / SLO

Run a short smoke load test:

```bash
uv run python load_test/driver.py \
  --rps 1 \
  --duration 30 \
  --out results/load_test_smoke.json
```

Run baseline load test:

```bash
uv run python load_test/driver.py \
  --rps 8 \
  --duration 300 \
  --out results/load_test_rps8.json
```

Run target SLO load test:

```bash
uv run python load_test/driver.py \
  --rps 10 \
  --duration 300 \
  --out results/load_test_rps10.json
```

Inspect load summary:

```bash
jq '.summary' results/load_test_rps10.json
```

Run eval after tuning:

```bash
uv run python evals/run_eval.py --out results/eval_after_tuning.json
jq '.summary' results/eval_after_tuning.json
```

Useful live checks during load:

```bash
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, sum by (le) (rate(vllm:e2e_request_latency_seconds_bucket[1m])))' | jq

curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=sum(rate(vllm:request_success_total[1m]))' | jq

curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=100 * max(vllm:kv_cache_usage_perc)' | jq
```

## General Checks

Compile changed Python files:

```bash
uv run python -m py_compile agent/graph.py agent/prompts.py agent/server.py evals/run_eval.py
```

Check git changes:

```bash
git status --short
git diff --stat
```

Check running local endpoints:

```bash
curl http://localhost:8000/v1/models
curl http://localhost:8001/health
curl http://localhost:9090/-/healthy
```
