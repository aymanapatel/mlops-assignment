#!/usr/bin/env bash
#
# Start vLLM with your chosen configuration.
# Reference: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

set -euo pipefail

if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

MODEL="${VLLM_MODEL:-Qwen/Qwen3-30B-A3B-Instruct-2507}"
MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.95}"
MAX_NUM_SEQS="${VLLM_MAX_NUM_SEQS:-64}"
MAX_NUM_BATCHED_TOKENS="${VLLM_MAX_NUM_BATCHED_TOKENS:-8192}"
ENABLE_PREFIX_CACHING="${VLLM_ENABLE_PREFIX_CACHING:-true}"
DISABLE_LOG_REQUESTS="${VLLM_DISABLE_LOG_REQUESTS:-true}"

args=(
    uv run python -m vllm.entrypoints.openai.api_server
    --model "$MODEL"
    --host 0.0.0.0
    --port 8000
    --max-model-len "$MAX_MODEL_LEN"
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
    --max-num-seqs "$MAX_NUM_SEQS"
    --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS"
)

if [[ "$ENABLE_PREFIX_CACHING" == "true" ]]; then
    args+=(--enable-prefix-caching)
fi

if [[ "$DISABLE_LOG_REQUESTS" == "true" ]]; then
    args+=(--disable-log-requests)
fi

exec "${args[@]}"
