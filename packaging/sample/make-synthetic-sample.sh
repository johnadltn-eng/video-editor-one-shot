#!/usr/bin/env bash
# Write a 2-second synthetic test pattern. No filmed footage, no network.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEFAULT="$ROOT/packaging/sample/out/synthetic-sample.mp4"
OUT="${1:-$DEFAULT}"

case "$OUT" in
  *".."*) printf 'ERROR: refusing a path that contains ..\n' >&2; exit 2 ;;
esac

case "$OUT" in
  "$ROOT"/packaging/sample/out/*) ;;
  /tmp/*) ;;
  "${TMPDIR:-/tmp}"/*) ;;
  *)
    printf 'ERROR: refusing to write %s\n' "$OUT" >&2
    printf 'Use packaging/sample/out/ or a directory under /tmp.\n' >&2
    exit 2
    ;;
esac

case "$OUT" in
  *"/projects/"*)
    printf 'ERROR: refusing to write into a job folder\n' >&2
    exit 2
    ;;
esac

command -v ffmpeg >/dev/null 2>&1 || { printf 'ERROR: ffmpeg is required\n' >&2; exit 2; }

mkdir -p "$(dirname "$OUT")"
ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "testsrc2=size=320x180:rate=24:duration=2" \
  -f lavfi -i "sine=frequency=440:duration=2" \
  -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac -movflags +faststart \
  "$OUT"
printf 'wrote synthetic sample %s\n' "$OUT"
printf 'This file is a test pattern. Do not commit it.\n'
