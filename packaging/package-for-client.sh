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
  premiere) ;;
  *)
    printf 'ERROR: refusing lane %s. This starter is Premiere on macOS only.\n' "$LANE" >&2
    printf 'Resolve, CapCut, and chat-only are not included and are not certified.\n' >&2
    exit 2
    ;;
esac

exec python3 "$ROOT/packaging/package_starter.py" "${ARGS[@]}"
