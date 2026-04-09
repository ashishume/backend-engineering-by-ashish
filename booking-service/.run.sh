#!/usr/bin/env bash
# Deprecated: use ./run.sh from the booking-service directory.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run.sh" "$@"
