#!/usr/bin/env bash
set -euo pipefail

AGENT_URL="${AGENT_URL:-http://localhost:8001/answer}"
OUT_DIR="${OUT_DIR:-ayman/Phase4/responses}"
RUN_ID="${RUN_ID:-langfuse-10q}"
MODEL_TAG="${MODEL_TAG:-qwen3-30b}"
CONFIG_TAG="${CONFIG_TAG:-maxlen-32768}"

mkdir -p "$OUT_DIR"

echo "Sending tagged Phase 4 requests to $AGENT_URL"
echo "Responses will be written to $OUT_DIR"

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the coordinates location of the circuits for Australian grand prix?",
    "db": "formula_1",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "01",
      "db": "formula_1",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_01.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "List down Ajax'\''s superpowers.",
    "db": "superhero",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "02",
      "db": "superhero",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_02.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "List the top five schools, by descending order, from the highest to the lowest, the most number of Enrollment (Ages 5-17). Please give their NCES school identification number.",
    "db": "california_schools",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "03",
      "db": "california_schools",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_03.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the average number of crimes committed in 1995 in regions where the number exceeds 4000 and the region has accounts that are opened starting from the year 1997?",
    "db": "financial",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "04",
      "db": "financial",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_04.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many male clients in '\''Hl.m. Praha'\'' district?",
    "db": "financial",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "05",
      "db": "financial",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_05.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the average fastest lap time in seconds for Lewis Hamilton in all the Formula_1 races?",
    "db": "formula_1",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "06",
      "db": "formula_1",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_06.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "From race no. 50 to 100, how many finishers have been disqualified?",
    "db": "formula_1",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "07",
      "db": "formula_1",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_07.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Calculate the difference of the total amount spent in all events by the Student_Club in year 2019 and 2020.",
    "db": "student_club",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "08",
      "db": "student_club",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_08.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the complete address of the school with the lowest excellence rate? Indicate the Street, City, Zip and State.",
    "db": "california_schools",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "09",
      "db": "california_schools",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_09.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

curl -sS "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Calculate the percentage of carcinogenic molecules which contain the Chlorine element.",
    "db": "toxicology",
    "tags": {
      "phase": "phase4",
      "run": "'"$RUN_ID"'",
      "question_index": "10",
      "db": "toxicology",
      "model": "'"$MODEL_TAG"'",
      "config": "'"$CONFIG_TAG"'"
    }
  }' | tee "$OUT_DIR/response_10.json" | jq '{iterations, ok, history_nodes: [.history[].node]}'

echo "Done. Filter Langfuse by tags like phase:phase4, run:$RUN_ID, or question_index:10."
