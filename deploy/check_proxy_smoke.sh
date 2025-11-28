#!/usr/bin/env bash
set -euo pipefail

HOST="https://localhost:8443"

echo "Checking proxy server at $HOST"

echo "HEAD / ->" 
curl -sSkI "$HOST" | sed -n '1,6p'

echo "GET /api/health ->"
curl -sSk "$HOST/api/health" | jq || true

echo "If the proxy is up, you should see HTTP headers and a JSON body {\"status\":\"ok\"}."
