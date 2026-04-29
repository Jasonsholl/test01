#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .git ]]; then
  echo "Not a git repo: $ROOT_DIR" >&2
  exit 1
fi

git add site

if git diff --cached --quiet; then
  echo "No site changes to publish."
  exit 0
fi

msg="${1:-Update images $(date -u +"%Y-%m-%dT%H:%M:%SZ")}"
git commit -m "$msg"
git push

