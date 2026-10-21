#!/usr/bin/env bash
# render the section-title cards -> renders/<id>.mp4  (opaque card, grid bg baked in)
#                                -> renders/<id>-alpha.mov (ProRes 4444, type only)
# usage: render.sh [id ...]          (no args = every title in titles.json)
#        ALPHA_ONLY=1  render.sh t-setup   (skip the opaque card)
#        OPAQUE_ONLY=1 render.sh           (skip the alpha overlays — the V1
#                                           timeline only ever places the opaque card)
#        VER=b         render.sh           (-> renders/<id>-b.mp4)
#
# VER: NEVER re-render onto a path an editing app has already placed. Overwriting a
# placed file half-stales Premiere's frame index and random frames come back
# transparent. Version the filename and import it fresh.
#
# Alpha is STRAIGHT. A lane that composites premultiplied converts on its own side — see LANES.md § step 5.
#
# Pin: 0.8.16 — the validated new-job pin (2026-08-27, PNG-sequence A/B vs 0.7.92
# on this very builder: opaque pixel-identical 90/90, alpha 233 px of glyph AA total). Bump deliberately.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders

PY=python3; "$PY" -c '' 2>/dev/null || PY=python
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8   # Windows pipes default to cp1252, which cannot encode the ⚠ status glyphs

if [ $# -gt 0 ]; then
  IDS="$*"
else
  IDS=$("$PY" build.py --ids)
fi

"$PY" build.py $IDS

SUF=""
[ -n "${VER:-}" ] && SUF="-$VER"

for ID in $IDS; do
  if [ "${ALPHA_ONLY:-0}" != "1" ]; then
    echo "==> $ID (opaque card)"
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps 30 --quality standard \
      --video-frame-format png --format mp4 --output "renders/$ID$SUF.mp4"
  fi

  if [ "${OPAQUE_ONLY:-0}" = "1" ]; then
    continue
  fi

  echo "==> $ID (alpha overlay)"
  npx hyperframes@0.8.16 render . -c "compositions/$ID-alpha.html" --fps 30 --quality standard \
    --video-frame-format png --format mov --output "renders/$ID-alpha$SUF.mov"
done
