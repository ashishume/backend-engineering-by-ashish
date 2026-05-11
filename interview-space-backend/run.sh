#!/usr/bin/env bash
# Install deps when the venv is first created, or when you pass --install or INSTALL_DEPS=1.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
NEW_VENV=false
FORCE_INSTALL=false

[ "${INSTALL_DEPS:-}" = "1" ] && FORCE_INSTALL=true
for arg in "$@"; do
  if [ "$arg" = "--install" ]; then
    FORCE_INSTALL=true
    break
  fi
done

# Prefer a stable 3.10–3.13 interpreter when multiple are installed (avoids protobuf issues on 3.14).
resolve_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    printf '%s' "$PYTHON_BIN"
    return
  fi
  for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf '%s' "$cmd"
      return
    fi
  done
  printf ''
}

PYTHON_BIN="$(resolve_python)"
if [ -z "$PYTHON_BIN" ]; then
  echo "No python3 found on PATH."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR using $PYTHON_BIN..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  NEW_VENV=true
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [ ! -f "requirements.txt" ]; then
  echo "requirements.txt not found in $SCRIPT_DIR"
  exit 1
fi

if [ "$NEW_VENV" = true ] || [ "$FORCE_INSTALL" = true ]; then
  echo "Installing dependencies..."
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -r requirements.txt

  # google-generativeai still declares protobuf 4.x; CPython 3.14+ needs protobuf 6+ (wheels/API).
  if python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)'; then
    echo "Python 3.14+: upgrading Google protobuf stack for compatibility..."
    python -m pip install --upgrade \
      'protobuf>=6.30.0,<7' \
      'google-api-core>=2.30.0' \
      'google-ai-generativelanguage>=0.11.0' \
      'grpcio-status>=1.75.0'
  fi
else
  echo "Skipping pip install. Use ./run.sh --install or INSTALL_DEPS=1 after changing requirements.txt."
fi

PORT="${PORT:-8002}"
echo "Starting interview space backend on port $PORT..."
exec python -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
