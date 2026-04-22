#!/usr/bin/env bash
# Deprecated: use ./run.sh from the booking-service directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="$SCRIPT_DIR/run.sh"

if [ ! -f "$TARGET_SCRIPT" ]; then
  echo "Could not find run script at: $TARGET_SCRIPT" >&2
  exit 1
fi

exec bash "$TARGET_SCRIPT" "$@"
