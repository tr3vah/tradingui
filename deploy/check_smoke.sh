#!/usr/bin/env bash
set -euo pipefail

echo "Starting smoke check against http://localhost:8080"

if ! curl -sSf http://localhost:8080/ >/dev/null; then
  echo "ERROR: web root not available" >&2
  exit 2
fi

if ! curl -sSf http://localhost:8080/api/health >/dev/null; then
  echo "ERROR: api health failed" >&2
  exit 2
fi

echo "Smoke check OK — web root and API health reachable via proxy."
