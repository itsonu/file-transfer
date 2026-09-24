#!/usr/bin/env sh
# Open Transfer — one-command launcher for macOS and Linux.
#
#   ./run.sh                 share ./uploads on port 5000
#   ./run.sh ~/Share --pin   any open-transfer option works
#
# First run creates an isolated environment in .venv (uses uv if installed,
# otherwise Python's venv + pip). Later runs start instantly.
set -eu
cd "$(dirname "$0")"

VENV=".venv"
STAMP="$VENV/.open-transfer-installed"

say() { printf '  %s\n' "$*"; }

if [ ! -f "$STAMP" ] || [ pyproject.toml -nt "$STAMP" ]; then
  say "Setting up Open Transfer (first run only)…"
  if command -v uv >/dev/null 2>&1; then
    [ -x "$VENV/bin/python" ] || uv venv -q --python ">=3.10" "$VENV"
    uv pip install -q --python "$VENV/bin/python" -e .
  else
    PY=""
    for candidate in python3 python; do
      if command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
        PY="$candidate"
        break
      fi
    done
    if [ -z "$PY" ]; then
      say "Open Transfer needs Python 3.10 or newer."
      say "Install it from https://www.python.org/downloads/ (or install uv: https://docs.astral.sh/uv/) and run this again."
      exit 1
    fi
    [ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
    "$VENV/bin/python" -m pip install -q --disable-pip-version-check -e .
  fi
  touch "$STAMP"
fi

exec "$VENV/bin/open-transfer" "$@"
