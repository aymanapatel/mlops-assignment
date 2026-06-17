jq '.summary | {achieved_rps, latency_p95, ok, timeouts, http_errors, client_errors}' results/load_test_rps10.json
