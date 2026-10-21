# Backgrounds — the two standard full-screen fields

The go-to backdrops for full-screen graphics on the youtube-default preset. Locked
2026-08-29 (you dialed both live against the Premiere monitor). Anything else is
opt-in by name.

- **`bg-light`** — light-gray radial field (`#f2f3f6` → `#dde0e7`), a feathered
  navy-tinted vignette (7 eased stops, corners land ~45% darker than center, no visible
  onset ring), and **film grain baked in** (luma-only temporal noise, strength 7 — real
  moving grain, added as an ffmpeg post-pass in render.sh).
- **`bg-dark`** — the brand navy field, two steps darker than the card token
  (`#060c1d` → `#010308`), 100px brand grid at 9% alpha, grid fading out under its own
  edge vignette. No grain.

**Any full-screen comp built ON bg-dark carries the GLOW pass AND renders 12 fps
style** (`STEP_FPS=12`) — the two travel together as the dark-field treatment, and
bg-light full-screens get neither (2026-08-31; glow level locked at subtle 0.26): a `#bloom` clone of the content layer with
`filter:brightness(1.45) contrast(1.12) blur(30px); mix-blend-mode:screen;
opacity:0.26`, so bright elements bleed light into the navy field. Full recipe +
the two-layer sync pattern: `../creative-moves.md` move 2. bg-light gets no glow.
The grid is a SIBLING layer in these comps — any dim/blur tween on the content must
name it too (`'.wall, #grid'`), or it stays sharp while everything else recedes.

## Rendering

```
./render.sh              # both → renders/bg-{light,dark}.mp4  (6s, 1920×1080)
./render.sh bg-light     # one
VER=b ./render.sh bg-light   # versioned — NEVER re-render onto a placed path
GRAIN=0 ./render.sh          # skip the grain pass; GRAIN_STRENGTH=7 is the knob
FPS=30000/1001               # default; match the timeline when it matters
```

**Renders are regenerable cache, not committed** — the grain makes bg-light ~88MB
(temporal noise defeats the encoder), so the comps + this script are the source of
truth; rebuild in ~90s per asset. For a longer bed than 6s, loop the clip in the
editor or bump `data-duration` and re-render.

## The vignette lesson (2026-08-29, cost three flat iterations)

Vignette intensity lives in the PIXELS, not the alpha values: with a big gradient
ellipse (105%+) the far stops land OUTSIDE the frame, so raising the corner alpha does
nearly nothing on screen — three "more intense" bumps moved the measured corner 5 luma
total while looking identical. Keep the ellipse small enough that the full ramp lands
inside the frame (78% 72% here), and verify a change by SAMPLING the render's corner
pixels against the previous version, not by re-reading the CSS.
