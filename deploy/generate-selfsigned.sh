#!/usr/bin/env bash
set -euo pipefail

SSL_DIR=$(dirname "$0")/ssl
mkdir -p "$SSL_DIR"

echo "Generating self-signed certificate in $SSL_DIR"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$SSL_DIR/privkey.pem" \
  -out "$SSL_DIR/fullchain.pem" \
  -subj "/CN=localhost"

echo "Done. Files:"
ls -l "$SSL_DIR"
