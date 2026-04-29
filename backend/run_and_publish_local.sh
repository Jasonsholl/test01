#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SOURCE="${1:-}"
if [[ -z "$SOURCE" ]]; then
  echo "Usage: backend/run_and_publish_local.sh /path/to/image-folder [YYYY-MM-DD]" >&2
  exit 1
fi

DATE_ARG="${2:-}"
if [[ -n "$DATE_ARG" ]]; then
  backend/.venv/bin/python backend/import_local.py "$SOURCE" --date "$DATE_ARG"
else
  backend/.venv/bin/python backend/import_local.py "$SOURCE"
fi

backend/publish_site.sh
