#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-$ROOT_DIR/.venv/bin/python}"

if [[ -x "$PYTHON_BIN" ]]; then
  "$PYTHON_BIN" -m compileall "$ROOT_DIR/scripts"
elif command -v uv >/dev/null 2>&1; then
  cd "$ROOT_DIR"
  uv run python -m compileall scripts
else
  python3 -m compileall "$ROOT_DIR/scripts"
fi
