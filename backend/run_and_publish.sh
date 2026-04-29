#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d backend/.venv ]]; then
  echo "Missing backend/.venv; create venv and install requirements first." >&2
  exit 1
fi

backend/.venv/bin/python backend/run_daily.py
backend/publish_site.sh "${1:-}"

