#!/usr/bin/env bash
# REFERENCE full-screen graphics renderer — copy into projects/<job>/hf-graphics/gfx/
# alongside compositions/. Carries the locked chains: full = mp4 + film-grain pass,
# alpha = ProRes 4444 straight, STEP_FPS=12 (THE default for bg-DARK full-screens ONLY;
# bg-light full-screens render at the timeline rate, no 12 fps — grain is
# applied AFTER the frame-hold expansion, at the timeline rate), optional MBLUR
# (never together with STEP_FPS — see creative-moves.md 4c).
# usage: render.sh <id> full   -> renders/<id>[-VER].mp4      (full-screen: grain pass baked)
#        render.sh <id> alpha  -> renders/<id>-alpha[-VER].mov (overlay: ProRes 4444 straight)
#        VER=b render.sh <id> full     (NEVER overwrite a placed file — version it)
#        FPS=30000/1001 (default) — the timeline's exact rational rate
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p renders

ID="$1"; MODE="${2:-full}"
FPS="${FPS:-30000/1001}"
SUF=""
[ -n "${VER:-}" ] && SUF="-$VER"

# MBLUR=1 -> TRUE motion blur: render at MBLUR_SS x the target rate, average
# MBLUR_SHUTTER consecutive frames, decimate back (~216-degree shutter). Same chain
# as text-animation/render.sh — see that file + text-animation-style.md for the three gotchas
# (trailing tmix window, mid-group tail, premultiply before averaging alpha).
#
# STEP_FPS=12 -> "12 fps style": ANIMATE at 12 fps and hold each frame, then expand
# back to the timeline rate by frame duplication (the on-2s / stop-motion look). It
# composes with MBLUR — the shutter is then a 12 fps shutter, so the blur is heavier
# by design. Grain is applied AFTER the expansion, at the full timeline rate: film
# grain is a camera artifact, not animation, and stepping it reads as a compression
# bug. Word-synced events quantize to the 12 fps grid (up to ~83 ms of shift), which
# is inherent to the look — check anything that must land exactly on a word.
SS="${MBLUR_SS:-5}"; SHUT="${MBLUR_SHUTTER:-3}"
FPS_NUM="${FPS%%/*}"; FPS_DEN="${FPS##*/}"
[ "$FPS_NUM" = "$FPS_DEN" ] && FPS_DEN=1
if [ -n "${STEP_FPS:-}" ]; then
  ANIM_NUM="$STEP_FPS"; ANIM_DEN=1
  EXPAND=",fps=$FPS"            # duplicate the held frames up to the timeline rate
else
  ANIM_NUM="$FPS_NUM"; ANIM_DEN="$FPS_DEN"
  EXPAND=""
fi
ANIM_FPS="$ANIM_NUM/$ANIM_DEN"
SS_FPS="$((ANIM_NUM * SS))/$ANIM_DEN"
WEIGHTS=""; _i=0
while [ "$_i" -lt "$SHUT" ]; do WEIGHTS="$WEIGHTS 1"; _i=$((_i + 1)); done
WEIGHTS="${WEIGHTS# }"
PHASE=$(( (SHUT - 1) / 2 ))
# The tail pad guarantees the last group exists. The supersampled and base renders
# round their frame counts independently, so derive the cap as ceil(ss_frames / SS):
# it can run ONE frame long but never short. Long is harmless (placement pins the
# out point); short would leave a one-frame gap at the graphic's tail.
mb_frames() { # $1 = supersampled file -> exact target frame count
  _L=$(ffprobe -v error -select_streams v:0 -count_frames \
       -show_entries stream=nb_read_frames -of csv=p=0 "$1")
  echo $(( (_L + SS - 1) / SS ))
}
MB_CORE="tmix=frames=$SHUT:weights=$WEIGHTS,tpad=stop=$SS:stop_mode=clone,select='eq(mod(n\,$SS)\,$PHASE)'"
RFPS="$ANIM_NUM/$ANIM_DEN"

# A versioned re-render that is BYTE-IDENTICAL to an earlier render means the comp did not change
# (the renderer and encoder are deterministic): g2-b.mp4 == g2.mp4 on your-job, so a
# 3-minute render and a placement swap were both no-ops and nobody noticed. Say so, loudly.
same_as_previous() { # $1 = the file just written
  _new="$1"; _base="${_new##*/}"; _fam="${_base%%-*}"; _ext="${_new##*.}"
  for _old in renders/"$_fam"*."$_ext"; do
    [ -f "$_old" ] && [ "$_old" != "$_new" ] || continue
    if cmp -s "$_old" "$_new"; then
      echo "⚠️  $_new is BYTE-IDENTICAL to $_old, the comp did not change. A render without an edit is a no-op;" >&2
      echo "    placing this file changes nothing on the timeline. Check the edit actually landed in compositions/$ID.html." >&2
    fi
  done
}

if [ "$MODE" = "alpha" ]; then
  if [ -n "${MBLUR:-}" ]; then
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$SS_FPS" --quality standard \
      --video-frame-format png --format mov --output "renders/$ID-ss.mov"
    NB=$(mb_frames "renders/$ID-ss.mov")
    [ -z "${STEP_FPS:-}" ] || NB=""   # `&& NB=` would exit under set -e
    ffmpeg -y -v error -i "renders/$ID-ss.mov" ${NB:+-frames:v "$NB"} -vf \
      "format=rgba64le,premultiply=inplace=1,$MB_CORE,unpremultiply=inplace=1,setpts=N/($RFPS)/TB$EXPAND,format=yuva444p12le" \
      -c:v prores_ks -profile:v 4444 -r "$FPS" "renders/$ID-alpha$SUF.mov"
    rm "renders/$ID-ss.mov"
    echo "-> renders/$ID-alpha$SUF.mov (motion blur baked)"
  else
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$ANIM_FPS" --quality standard \
      --video-frame-format png --format mov --output "renders/$ID-alpha$SUF.mov"
  fi
  same_as_previous "renders/$ID-alpha$SUF.mov"
else
  if [ -n "${MBLUR:-}" ]; then
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$SS_FPS" --quality standard \
      --output "renders/$ID-ss$SUF.mp4"
    # opaque full-screen: no premultiply needed, and the grain rides in the same pass
    NB=$(mb_frames "renders/$ID-ss$SUF.mp4")
    [ -z "${STEP_FPS:-}" ] || NB=""   # `&& NB=` would exit under set -e
    ffmpeg -y -v error -i "renders/$ID-ss$SUF.mp4" ${NB:+-frames:v "$NB"} -vf \
      "$MB_CORE,setpts=N/($RFPS)/TB$EXPAND,noise=c0s=7:c0f=t" \
      -c:v libx264 -crf 14 -pix_fmt yuv420p -an -r "$FPS" "renders/$ID$SUF.mp4"
    rm "renders/$ID-ss$SUF.mp4"
    echo "-> renders/$ID$SUF.mp4 (motion blur + grain baked)"
  else
    npx hyperframes@0.8.16 render . -c "compositions/$ID.html" --fps "$ANIM_FPS" --quality standard \
      --output "renders/$ID-clean$SUF.mp4"
    # the standing film-grain pass (same recipe as bg-light) — full-screens only
    ffmpeg -y -v error -i "renders/$ID-clean$SUF.mp4" -vf "${EXPAND#,}${EXPAND:+,}noise=c0s=7:c0f=t" \
      -c:v libx264 -crf 14 -pix_fmt yuv420p -an "renders/$ID$SUF.mp4"
    rm "renders/$ID-clean$SUF.mp4"
    echo "-> renders/$ID$SUF.mp4 (grain baked)"
  fi
  same_as_previous "renders/$ID$SUF.mp4"
fi
