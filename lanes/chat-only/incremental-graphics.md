# Chat-Only Assemble Lane — ffmpeg composite for no-app finishes

**The graphics lane for jobs finished WITHOUT an editing app** (clients with no Premiere / Resolve /
CapCut). Graphics render as parts and an ffmpeg pass composites them onto the base cut — a tweak
re-renders one part (seconds) and recomposites (~5s), never the whole video. **Not the primary
path** — app finishes place parts as timeline clips and never need this sheet. Everything
lane-agnostic (harness, part-splitting, probing, render gotchas) lives in the **`graphics-build`**
skill; this sheet is only the ffmpeg-composite mechanics.

## The architecture

Three layer types, composited by ffmpeg over the **base** (the rough cut — rendered ZERO times by graphics):

| Layer | What | Rendered as |
|-------|------|-------------|
| **base** | the rough cut (`outputs/<job>.mp4`) | already done — never re-rendered |
| **overlay** | a card/panel floating OVER the footage | standalone comp → transparent `.mov` (`--format mov`) |
| **segment** | a part that *modifies the footage itself* (reframe takeover, full-screen cutaway, speed ramp) | standalone comp **with its own base slice** → opaque `.mp4` |
| **ffseg** | a footage move expressible in pure ffmpeg (zoom / push-in / pan) | `zoompan` on the base slice — **prefer this over a browser segment every time** |

**Overlay vs segment, one question:** does the part change the underlying footage? → segment.
Floats on top? → overlay. **And prefer ffseg over segment** wherever the move is pure geometry —
zero browser round-trip, zero brightness shift.

The harness (`build.py` → `compositions/`, `render-part.sh`, `parts.json`) is the standard
`graphics-build` Stage-1 setup plus **`assemble.sh`**: ONE ffmpeg overlay pass — base + segments +
overlays → `renders/final.mp4` (~5s). Each part comp's GSAP timeline is rebased to start at 0;
`assemble.sh` places each clip at its real timestamp with `-itsoffset` +
`overlay=enable='between(t,start,end)'`. The loop: edit `build.py` → probe → `./render-part.sh
<id>` → `./assemble.sh` → review. "Render everything" at the end is just `./assemble.sh`.

## ffmpeg-composite gotchas (learned, don't relearn)

- ⭐ **Every overlay needs `:eof_action=pass`, or ffmpeg silently duplicates ~1-in-4 output frames
  (the stutter trap — cost six rounds).** `overlay` defaults ended inputs to `repeat`; several
  ended-but-repeating inputs make the scheduler duplicate output frames on a periodic cadence.
  The output is dead-even CFR so ffprobe/PTS read perfectly fine — content just changes ~18×/sec
  in a 24fps costume, and every input measures clean in isolation. The single exception is a
  deliberately-held final frame (a push-in that holds to the end): that one part gets
  `eof_action=repeat` — never `tpad=stop_mode=clone` after `zoompan`, which never EOFs and
  ballooned a 4s clip past 1 GB. **Detect:** `signalstats` YDIF=0 tally (clean ~0–3%, the bug
  ~25%); `assemble.sh` runs this after every composite and **exits 1 at ≥8% dups — do not remove
  the guardrail.** Never mask stutter with `-r`/`fps=` (already CFR; it just re-times the dups).
- **Segments carry their own base slice**, cut at the **PLACED time, not the build time.** If the
  base was re-spliced and graphics slide via a `PLACE_SHIFT`, a slice cut at the raw build time
  makes the segment's footage jump at the seam and run out of sync with the audio for its whole
  window — a base re-splice means re-cut the slice at the placed time AND re-render the segment.
  Verify: the slice's frame 0 luma matches `ffmpeg -ss <placed_start> -i base`.
- **The segment brightness dip — fix at the ROOT.** A browser segment round-trips footage through
  headless Chrome (decode→RGB→re-encode) and darkens it ~3% vs the passthrough base, visible at
  every seam. (1) Prefer **ffseg**: `zoompan` never enters the browser → zero shift. (2) If it
  MUST be a browser segment (rounded-card takeover revealing graphics behind the face): render
  with `--video-frame-format png` (halves the dip — the default lossy JPG extraction is most of
  it), then close the remainder with a residual **gamma** lutyuv on that segment in assemble
  (`G≈1.03` measured; re-derive by comparing `signalstats` YAVG of segment frame 0 vs its slice).
- **A browser segment reframes via the WRAPPER's layout box** — GSAP-transforming the `<video>`
  silently drops it from the render. `<video>` (`object-fit:cover`) sits in an `overflow:hidden`
  wrapper div; GSAP animates the wrapper's `left/top/width/height` (+ borderRadius/boxShadow) —
  the parent shrinks/slides and crops the untransformed video.
- **`zoompan` on a mid-video slice needs `trim=start=S:end=E,setpts=PTS-STARTPTS` in the
  filtergraph** (never `-ss` alone) — zoompan's frame counter `on` counts from the filtergraph
  input's start, so a mid-video part sees `on` already huge at frame 0 and any `on`-based ramp
  pins at its end value → a constant zoom that reads as a hard cut (invisible on a part starting
  at 0). More zoompan: crop w/h can't animate (only x/y); upscale 2× first
  (`scale=3840:2160`) so the zoom doesn't quantization-jitter; ease on output time with a cosine
  so zoom=1.0 at both seams; set `fps=` to the base.
- **Anchor footage motion to the MEASURED cut on pre-snap bases.** Frame-snapped splices (current
  pipeline) make EDL == rendered timeline, so plan times anchor directly. A base rendered BEFORE
  the 2026-07-09 frame-snap fix drifts ~0.4s by the end — measure the real cut with
  `scdet=threshold=0` (take the max score in the gap) and cut slices with `-ss` AFTER `-i`
  (decode-accurate; before `-i` is keyframe-only).

## Reference implementation

No sample projects ship — author the harness fresh from `graphics-build` + this sheet.
