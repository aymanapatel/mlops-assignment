curl http://localhost:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{
    "model": "Qwen/Qwen3-30B-A3B-Instruct-2507",
    "messages": [
      {
        "role": "user",
        "content": "Convert this question to SQL only. Question: What is the coordinates location of the circuits for Australian grand prix?"
      }
    ],
    "temperature": 0,
    "max_tokens": 256
  }' | jq