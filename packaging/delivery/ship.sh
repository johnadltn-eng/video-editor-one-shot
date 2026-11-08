#!/usr/bin/env bash
# Publication entrypoint. It always refuses.
# A Mac smoke record, when present, is printed as a local gate only.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RECORD="${1:-$ROOT/packaging/gates/records/mac-smoke-record.json}"

printf '%s\n' "publication disabled: this review branch does not publish archives, download releases, or external pages."

if [[ "$#" -gt 1 ]]; then
  printf '%s\n' "refusing extra arguments."
  exit 3
fi

if ! python3 "$ROOT/packaging/gates/check_mac_smoke.py" "$RECORD"; then
  printf '%s\n' "mac smoke gates are not recorded. That does not unlock publication."
fi

printf '%s\n' "refusing to publish."
exit 3
