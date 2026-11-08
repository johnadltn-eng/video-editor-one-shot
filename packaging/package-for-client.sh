#!/usr/bin/env bash
# Local allowlisted starter archive. The historical name is kept because
# setup notes refer to it. This script does not publish.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANE="premiere"
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lane)
      [[ $# -ge 2 ]] || { printf 'ERROR: --lane needs a value\n' >&2; exit 2; }
      LANE="$2"
      shift 2
      ;;
    --publish|--upload|--release)
      printf 'ERROR: refusing %s. This packager does not publish or release.\n' "$1" >&2
      exit 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

case "$LANE" in
  premiere|resolve|capcut|chat-only) ;;
  *)
    printf 'ERROR: unknown lane %s.\n' "$LANE" >&2
    exit 2
    ;;
esac
printf 'Archive lane note: %s is not a certification. The zip keeps every allowlisted source lane.\n' "$LANE" >&2

exec python3 "$ROOT/packaging/package_starter.py" "${ARGS[@]}"
