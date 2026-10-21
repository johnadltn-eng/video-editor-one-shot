---
name: graphics-build
description: "Owns the graphics BUILD (step 5b): consumes projects/<job>/graphics-plan.json and drives the whole build — harness setup, asset prep, comp authoring per storyboard cell, browser probe, part renders, placement on the target surface (Premiere / Resolve / CapCut / chat-only ffmpeg), first-pass QA — ending with every planned graphic placed and ready for your review. Carries the render gotchas and the long-graphic part-split SOP; routes lane mechanics to the app skills and the chat-only assemble sheet. Does NOT decide graphics (graphics-plan does) and does NOT do captions/music/export. Triggers: build the graphics, build the planned graphics, execute the graphics plan, graphics build, run the build, composite the graphics, place the graphics on the timeline."
---

# Graphics Build — from plan to placed graphics, one owner

**Step 5b of the pipeline.** `graphics-plan` decided everything; this skill EXECUTES it: every
`graphic:true` beat built exactly as storyboarded, rendered, and placed on the target surface.
Done = all planned graphics on the timeline (or composited, chat-only lane), a build report, and
nothing left for you but to watch it and call adjustments.

**The bar: one-shot fidelity.** The plan is the contract — build what it says, at the times it
says, with the copy it says, verbatim. A better idea at build time is a NOTE in the report, never
a silent change (same rule as the tier gate: escalation and deviation are your calls). If a
cell turns out unbuildable as written (asset missing, timing impossible), build the closest
faithful version and flag it `⚠️` in the report — don't stall, don't redesign.

**Style comes from the plan's `preset` doc, and only that preset's docs.** Presets are independent;
never pull style from another preset's folder.

## The build loop — one graphic at a time, converged before the next (2026-08-29)

Stages 3–6 below run **PER GRAPHIC, in plan order**: author → probe → render → place → check the
real composite (program monitor / lane readback) → judge it against the plan cell, the preset
locks, and the Definition of Done → fix and re-render **until THAT graphic is right**, then move
to the next. Never park a known defect "for the review loop" — nothing broken moves forward.

**Effort scales with complexity.** A simple text animation: build, verify sync + layout, done —
minutes. A full-screen / punch-cut / multi-element graphic: expect multiple rounds (~10 min is
the working budget; the first generation of a complex graphic is usually NOT right — layout,
hierarchy, and arrow/prop craft take passes). Judge each round the way you would: placement,
sizing, balance, sync, readability — from the actual composite, not the comp render.

When every graphic has individually converged, Stage 7 runs the all-up QA and hands the draft to
the **final `edit-review` loop, which runs until zero defects** (stops on the first clean round) —
it catches what only the full sequence shows (cross-graphic rhythm, boundary bleeds, variation
collisions); it is not a substitute for per-graphic convergence.

## Stage 0 — preconditions

- `projects/<job>/graphics-plan.json` exists. If not → stop, run `graphics-plan` first.
- The rough cut ran (canonical transcript + EDL exist). Frame-snapped splice ⇒ **plan times ARE
  timeline times** — anchor comps and placements to them directly, no offset hunting.
- **Target surface** = the plan's `"compositor"` (`premiere` · `resolve` · `capcut` · absent =
  chat-only HyperFrames finish). App lanes need their bridge/app available — ping first, per the
  app skill.

## Stage 1 — harness

Set up the durable generated build under **`projects/<job>/hf-graphics/`** (never `/tmp` — a full
day of build source was wiped by macOS's overnight `/tmp` clear once).

**The minimum harness — what the shipped `your-job` intro actually used, and the default:**
`compositions/<id>.html` (one hand-authored comp per graphic) + **`render.sh` (copied into `hf-graphics/gfx/` alongside `compositions/`) from
[`presets/youtube/default/reference/fullscreen-render.sh`](../../../presets/youtube/default/reference/fullscreen-render.sh)**
(it carries the locked chains: `full` = mp4 + grain, `alpha` = ProRes 4444 straight, `STEP_FPS`,
`MBLUR`, `VER=`, and a byte-identical warning when a re-render did not change) + **`hf-anim.js`
(copied into `hf-graphics/gfx/` from
[`presets/youtube/default/reference/hf-anim.js`](../../../presets/youtube/default/reference/hf-anim.js))
, THE REGISTRY AS CODE: every comp starts as a copy of
[`reference/comp-scaffold.html`](../../../presets/youtube/default/reference/comp-scaffold.html),
declares its rate (`HF.init({fps, dur[, stepFps: 12]})`) and CALLS `pop`/`slam`/`riseIn`/`exit`/
`float`/`arrow`/`countUp`/`reveal`; nothing is retyped (2026-09-02: eleven comps each re-typed the
helper blocks and each got a different subset wrong, nine of ten motion defects)** + `PROJECT.md`
(the resume doc: write it now, update as you go, so any fresh session can pick up mid-build). The
preset also ships two *generated* builders you copy in whole when the job needs them:
`text-animation/` (run it with `--fps <timeline rate>`; it reads `transcript/cuts.json` and ends
each animation ON the next V1 cut by itself) and `titles/`.

- On the **basic tier** (4–7 short cards) each card is its **own independent comp** — no shared
  timelines, no part-splitting; a tweak re-renders one ~2s comp. **A `build.py` emitter is for
  the split-part case only** (a long multi-scene graphic, below) — do not build one for a set of
  short independent cards.
- ⚠️ `build.py` / `render-part.sh` / `render-all.sh` / `place.py` / `qa.py` are a HEAVIER harness
  from the Resolve-era jobs; they are not in the repo (the reference job lives on the archive
  drive). Do not treat them as a precondition — reach for that shape only on a part-split build,
  and author it fresh from the SOP below.
- **Stale tracking (split-part builds only):** stamp `renders/<id>.sha` with the hash of the comp
  each render came from and give the emitter a `--stale` mode that diffs comp-hash vs stamp. On a
  set of independent card comps there is nothing to track — one comp, one render.
  Parts of a shared-timeline chain embed the whole timeline, so touching one shared element marks
  every part of the chain stale — the seam-coupling rule, enforced instead of memorized.

## Stage 2 — assets

Everything a cell needs, gathered before any comp is authored:

- **Generated motion clips** (`b-roll` / `motion-graphic` cells with no real footage) →
  generated with your AI-video tool of choice, into `projects/<job>/broll/`. Its style block comes from THIS preset only.
- **Screenshots / screen-recs** the plan references → confirm they exist in the job folder
  (`assets/`, `raw/`); a missing artifact is a `⚠️` in the report, not a guess.
- **Fonts** → copy the preset's font files into `hf-graphics/assets/fonts/` and `@font-face`
  them (headless render needs the file; a system name silently falls back).
- **Split-frame explainer (full tier only):** measure the face crop first —
  `uv run workflows/face-frame.py <base-cut>` — and use the printed `object-position` verbatim.
- **Long-form, any overlay that shares the frame with your face:** measure the chin line first —
  `uv run workflows/chin-line.py <base-cut>` — and build every under-the-face comp inside the
  band it prints (`presets/youtube/default/default-overlay-style.md` § THE LOW BAND). The
  text-animation builder takes it as `TOP_MIN`; hand-authored comps put it in a header comment. A
  stack too tall for the band scales down WHOLE — never push past the floor to keep type big.
  On an app-finish job (`RENDER=0`, no flat cut exists), point `chin-line.py` at the RAW main
  take — it samples frames, so killed regions only add samples and the floor stays conservative.

## Stage 3 — author the comps

One comp per storyboard cell, straight from the plan: the cell's `template` from the preset doc
(an older plan may carry only `kind` + `content` — derive the template from those and note it),
its `copy` **verbatim** (never paraphrase on-screen words), its `region`/side, its motion note.
Timing: comp durations and placement times come from the cell's `start`/`end` — word-snapped
already, don't re-time. The preset doc's CSS/tokens are the lock; design freedom lives INSIDE the
template, not around it. HyperFrames authoring detail → the `hyperframes-core` / `-animation` /
`-keyframes` skills.

### Long graphics ship as split part clips (LOCKED SOP — 2026-07-21)

Render time is **linear in comp duration** and a tweak re-renders the whole comp, so a long
multi-scene graphic (one grew to 19s ≈ 85s + 1.5 GB per tweak) ships as **short part clips,
butt-joined** — adjacent clips on the app timeline, or adjacent segments in the chat-only
composite. Split even when scenes flow continuously; split on a transition if that's where the
cut wants to be — the seam just has to frame-match.

- **Frame-match by construction:** ONE shared timeline for the whole graphic in `build.py`; emit
  each part with a start offset — `emit("g2", durA, ...)` + `emit("g2b", durB, ..., t0=durA)`.
  The emit template wraps `tl` in a shim that shifts every position by `−t0` and collapses any
  set/tween ending before the seam into its END state at time 0 — part N+1's first frame IS part
  N's last frame, pixel-identical. (GSAP note: `master.add(tl, -t0)` does NOT work — negative
  positions get clamped; the shim is the way.)
- **Cut on exact frame counts:** part durations = `k * 1001/24000` (23.976) so clips butt-join on
  the frame grid with no gap or overlap.
- **Coupling rule:** a change visible at the seam = re-render BOTH adjacent parts; a change
  contained inside one part = that part only (`--stale` enforces this).
- **Motion THROUGH a seam = per-frame `tl.set`s on FRAME-INTEGER times** — a `.to()` straddling
  the seam gets clamped by the shim. Compute each set's time as `frameIndex * 1001/24000 - 0.0005`
  (the guard keeps every set safely before its frame sample in BOTH parts; a rounded decimal base
  lands one part a frame late → a double-step stutter exactly at the seam). Verify a mid-motion
  seam by measuring the moving element across the 4 frames spanning the join (smooth easing
  steps), never by diffing the two seam frames (adjacent real-motion frames SHOULD differ).
- **Grain is free at seams:** grain flicker alternates every few frames anyway, so the grain-phase
  flip at a seam is invisible (and defeats the renderer's static-frame dedup).
- **Premiere side:** each part = its own project item + clip (per-part `refreshMedia`); baked
  Transform keys live on the part that plays them.

## Stage 4 — probe before render

**Rendering to find out whether a comp works is the most expensive habit in this pipeline** — a
part render is 1.5–3.5 min; seeking the paused timeline in the Browser pane is one tool call.
**Serve over localhost, never `file://` (2026-08-29):** the Browser pane pins a `file://` comp to a
static `data:` snapshot — relative assets (images, fonts) 404 silently and rect coordinates come
back scaled/garbage, which reads as a layout bug that isn't there. Start the repo's `probe`
server (`.claude/launch.json`: `preview_start {name: "probe"}`, a static server on 8123 rooted at
the repo: never a Bash-run server) and open
`http://localhost:8123/projects/<job>/hf-graphics/<folder>/compositions/<id>.html`; `resize_window`
to 1920×1080 on that tab makes screenshots capture the full frame. Then measure MECHANICS: positions, pivots, whether a
tween fired, whether frame 0 is the settled seam state:

```js
(() => { const t = window.__timelines.main, o = {};
  [8, 24, 50, 80].forEach(f => { t.seek(f * 1001 / 30000);          // fps of THIS job
    const e = document.getElementById('gear1'), b = e.getBoundingClientRect();
    o['f'+f] = [Math.round(b.x + b.width/2), Math.round(b.y + b.height/2), e.getAttribute('transform')];
  }); return o; })()
```

The failures this catches are invisible in a contact sheet: a wrongly-pivoted element still
animates, it just orbits, so the sheet reads as "odd design" rather than "bug". Two traps:
**`seek(0)` when the timeline is already at 0 is a no-op** (seek away and back), and
`location.reload()` inside a probe kills the execution context (re-`navigate` with `force: true`).

**Scope: mechanics on new or structural work.** On second-pass nudges of a locked graphic, skip
visual self-QA entirely — edit, render the part, show; the fixes get called live from the review.

## Stage 5 — render

Part-by-part via the harness scripts, at the base footage's fps, `-q standard` (the part render
IS final quality — no separate "final render" step):

- **Overlays** (cards, text animations, enacting overlays — anything that composites over
  footage) → **alpha ProRes 4444, straight alpha** on every app lane; never premultiply.
- **Full-screen GRAPHICS** (punch-cut graphics — anything that REPLACES the frame) → **opaque mp4
  with the film-grain pass baked**, via `render.sh <id> full` (the reference renderer's `full`
  mode does grain + libx264 crf 14 in one chain). bg-DARK full-screens add `STEP_FPS=12` AND the
  glow pass; bg-LIGHT gets neither.
- **Section title cards** → the preset's own `titles/render.sh` **unmodified** (its signature is
  `render.sh [id ...]` — there is no mode argument, and it bakes NO grain, by design). Don't route
  them through the full-screen chain.
- **CapCut lane only** → premultiply every alpha mov (CapCut reads 4444 as premultiplied; straight
  renders blow out soft pixels).
- **Re-renders get a NEW versioned filename** — overwriting a placed file half-stales Premiere's
  frame index (random transparent frames) and CapCut silently serves the old file.

### Render gotchas (learned, don't relearn)

- **Pin the CLI version in every render script.** A bare `npx hyperframes` floats to whatever
  shipped last (the 0.7.42 contract break landed mid-job exactly this way). Every render script —
  the copied `render.sh`, and any emitter — calls `npx hyperframes@<tested version>` — currently `0.8.16` for new jobs (validated 2026-08-27:
  png-sequence A/B vs 0.7.92 on the titles builder — opaque frames pixel-identical 90/90,
  alpha 233 px of glyph AA across the whole clip; never 0.7.67). Jobs already
  rendering on an older pin keep it. Bump deliberately: edit, re-render one part, review, adopt.
- **Panels must read on their OWN fill.** An isolated alpha render has nothing behind it, so
  `backdrop-filter` does nothing — design opaque-bright surfaces, never live backdrop blur.
- **Match fps to the base** (`--fps 24000/1001` for 23.976 footage) or overlays drift.
- **No raw emoji glyphs — they HANG the headless render** (Chrome spins at 100% CPU resolving the
  system color-emoji font; never errors, never times out — a 5s part burned 5+ min before being
  killed). Fake the look in the brand font, or bake the glyph to a PNG with
  `uv run workflows/bake-emoji.py rocket=🚀 --out projects/<job>/hf-graphics/assets/emoji`.
  Smell test: a render at ~3× its siblings' time on a same-length part = kill it, look for a glyph.
- **An exit tween must finish INSIDE the clip's `data-duration`, plus a hard-kill**
  (`tl.set("#id",{opacity:0}, <next-clip-start>)`) — HyperFrames hard-hides a clip at its window
  end, so a mid-dissolve exit POPS. Lint catches only the missing hard-kill half; the
  too-short-duration half passes lint and pops in the video.
- **A fixed-pivot rotate/scale on an SVG element goes in the SVG `transform` ATTRIBUTE** —
  `rotate(deg cx cy)`, per-frame `gsap.set` of the attribute string is fine. GSAP `rotation` +
  `transformOrigin`/`svgOrigin` on SVG displaces the pivot (measured on 3.14.2), and a later bare
  `{rotation:N}` tween silently reverts it — the element still animates, it just orbits, which is
  exactly what the Stage-4 probe exists to catch.
- **Never pre-position a GSAP-tweened element with CSS `transform`** — the stylesheet transform
  gets absorbed into GSAP's cache and a later `x`/`xPercent` tween nets the wrong end position.
  GSAP owns position; set initial poses via `tl.set(...)`.
- **ALL CSS inline in the comp** — a `<link rel="stylesheet">` silently does not load in the
  headless render (zero error, zero lint; fonts fall back to serif, classes vanish). Smell test:
  brand font rendering as Times.
- **A staggered `fromTo` whose from-pose changes glyph geometry needs `immediateRender:false`** —
  GSAP applies from-poses at build time by default, so pre-scaled glyph boxes eat the margins and
  un-revealed text renders packed together.
- **Benign lint noise — don't "fix":** `duplicate_media_discovery_risk` (warning),
  `missing_local_asset: <id>-base.mp4` (clears when the slice is cut),
  `timeline_track_too_dense` (warning), `missing_three_script` (false positive on `+esm` imports).
- **Never GSAP-`transform` a `<video>` element — it silently drops from the render** (the face
  vanishes, no error). Footage moves on app lanes are baked in-app (Transform keys / Fusion);
  on the chat-only lane use the wrapper-box / ffseg recipes in
  [`lanes/chat-only/incremental-graphics.md`](../../../lanes/chat-only/incremental-graphics.md).

## Stage 6 — place

Route to the lane's own doc — this skill orders the work, the lane doc carries the mechanics:

| Compositor | Recipe |
|---|---|
| `resolve` | the `davinci-resolve` skill — `place.py` pattern (AppendToTimeline, V2, exclusive endFrame, 108000 offset), idempotent + readback-verified |
| `premiere` | **`uv run lanes/premiere/place-graphics.py projects/<job> --plan --write` then `--apply`**, one owner for `hf-graphics/placement.json` and the graphics tracks: derives every row from the plan + the newest render version, places what is not yet on the timeline, swaps stale versions, reads every write back; `--verify` is the readback, `--sync-plan` writes frame-snapped times back into the plan so plan-fidelity never argues over a rounding (2026-09-02: eight hand ES batches + two reconciliations). Mechanics underneath: the `premiere-pro` skill's "Graphics in Premiere" (V3 on youtube/default: V1 footage, V2 grade, V3 graphics; baked footage moves on V1 via the bridge `zoom`; AME banned) |
| `capcut` | the `capcut` skill — `lanes/capcut/capcut-bridge.py add-overlay` (+ `--force` rules) |
| chat-only | [`lanes/chat-only/incremental-graphics.md`](../../../lanes/chat-only/incremental-graphics.md) — the ffmpeg assemble lane (kept for no-app clients; not the primary path) |

Long-form structure (section title cards, SFX whoosh, track map) is the **preset README's**
territory (e.g. `presets/youtube/default/`) — place graphics onto that architecture, don't invent
tracks.

## Stage 7 — first-pass QA + report

**The gate first (2026-09-02):**

```bash
uv run workflows/graphics-qa.py projects/<job> --json projects/<job>/hf-graphics/qa-report.json
```

Non-zero exit = not done; fix and re-run until it is green. It sweeps every frame of every placed
render and owns, mechanically, most of what the list below used to ask you to check by hand:
render format + fps, placed vs render duration, the band and edge sweep (3b), exit completeness
and the hard-kill, static lead frames on full-screens, the grain pass, cut alignment to the frame,
holes/overlaps on the graphics tracks, plan reconciliation, text-animation copy vs plan, em dashes,
helper integrity + registry constants + relative riseOut + float coverage + the 12 fps form (3d),
zero-frame pins (3d-1), hand-typed arrowheads (3e), `position:absolute` with no offsets, exits
before entrances, and the density numbers. **A deliberate deviation is a line in
`hf-graphics/qa-waivers.json`** (`{"g18": {"band": "DOWN arrow reaches the floor by design"}}`),
never a sentence in the report: the review loop reads the JSON and treats prose as no evidence.
Items 1–3g below remain the checks the script cannot make (composite spot-checks, prop-glow spill,
readable holds and burst cadence on the render, arrow geometry measurement, footage-move keys,
borrowed palettes) plus the ones it already covers, kept for what to look at when it fails.

Verify, then report — never hand over unverified work:

1. **Per render:** file exists, duration matches the cell, and the format matches the ROLE:
   overlays = alpha present (`ffprobe` — `yuva444p12le` for ProRes 4444); full-screen GRAPHICS =
   OPAQUE mp4 with the film-grain pass baked (do not check for alpha here — its absence is
   correct; do check the grain, since the rendered-bed route ships grainless). **Section title
   cards are exempt from the grain check** — `titles/render.sh` is a locked builder that does not
   bake grain, and re-rendering outside it would break the lock.
2. **Placement readback:** every overlay at its planned time on the right track (each lane doc's
   readback method). Timeline count == plan's `graphic:true` count.
3. **Composite spot-check:** 2–3 real composite frames at the strongest cells (Resolve: a real
   render, never `get_thumbnail_image`; Premiere: the bridge `frame` command / `window-grab.sh`,
   never fronting the app; chat-only: ffmpeg frame of the assembled file). Verify against the
   plan's cell: right copy, right side, face clear.
3b. **Band check (long-form):** every under-the-face overlay's ink sits inside the measured band
   on its own render — check the comp's box geometry in the browser probe (cheap, exact) rather
   than eyeballing a composite. The one legal exception is a DOWN arrow, whose lowest bounce
   frame sits ON the floor.
3c. **Prop-glow check (long-form):** for every accent prop, measure its own colour's light
   OUTSIDE the prop's box on the finished render (a masked fill's `box-shadow` renders nothing
   — `default-overlay-style.md` § THE PROP GLOW). A comparison against the previous render is
   the fastest form: zero accent pixels outside the box means the glow never existed.
3d. **Registry + float conformance (long-form) — AUTHORED graphic comps only.** The preset's
   generated builders (`text-animation/`, `titles/`) are exempt: they emit their own JS branch
   names (`ENTRANCE = "rise" | "punch" | "flicker"`, where `punch` is the scale family and
   `flicker` is `flash`) and text animations carry no `float()` by design — their motion is
   locked in the builder, so conformance there means "the builder was used unmodified".
   For every hand-authored comp: grep its script for the entrances and
   exits — every one must be a preset from `animations.md` (`pop` / `slam` / `flash` /
   `riseIn` / `riseOut` / `slideIn` / `slideOut`), the exit defaulting to `riseOut`, `slide*`
   used ONLY where the element crosses a frame edge, a full-screen graphic's FIRST element
   entering on frame 0 with zero blank lead WHEN that element is near-full-frame (measure on the
   render — heavy-downscale diff, not an edge count, or grain swamps it; the defect scales with
   the element's size), a near-full-frame element rising rather than popping, and
   hold life must be a
   `float()` call with a named preset on a WRAPPER spanning `0 → DUR`. Retired moves (the 1.45×
   punch, the ±2° wiggle, a stepped card in/out) are defects, and so is `flash` in a comp
   rendered `STEP_FPS=12` (its single-frame gaps sit below the 83ms step and vanish). Check the
   entrance split against ROLE: peers share one preset, the odd element out carries the
   contrast. Check the RENDER FLAGS against the field: a bg-DARK full-screen renders
   `STEP_FPS=12` AND carries the glow pass (the pair travels together); a bg-LIGHT one gets
   NEITHER. Because these helpers are inlined
   per comp, also assert every comp that CALLS one DEFINES it: load them all and check each
   exposes `window.__timelines.main` at its authored duration — a missing helper throws and the
   comp renders blank.
3d-1. **Zero-frame check:** grab frame 0 of every render and confirm nothing that ANIMATES IN
   is already present — a content-mutating reveal (`innerText`, counters, list rows) does not
   reliably revert on a seek, so it can open half-done. Pin it with a `set(...)` at time 0. When
   measuring text on a render, crop the WHOLE content box: a crop that starts below line 1 reads
   grain as "empty" and hid exactly this bug. In the same pass, grep every comp for
   `onUpdate`-driven content — the callback never fires on a seek, so onUpdate text renders
   FROZEN headless; reveals are positioned `tl.set`s, always.
3d-2. **Readable-hold check (long-form):** for any graphic built to be READ (prompt, command,
   code, config, quote), count the frames on the render that carry the COMPLETE content — it must
   be **2-3s**. Budget the slot backwards (`reveal_end = duration − HOLD`), never forwards from
   the reveal. Measure neutral-bright TEXT pixels only: an accent cursor blinking through the hold
   makes a naive luma threshold report half the frames as incomplete. The reveal itself must be
   BURSTS (2-6 words, ~12 fps beat, punctuation doubles the hold — count discrete steps on the
   render; a new state every frame is the linear-wipe defect) and DETERMINISTIC (grep the comp:
   `Math.random` in a reveal is a defect — the headless render seeks).
3e. **Arrow check (long-form):** any comp with a path-and-head arrow must build the head with
   `arrow()` from `animations.md` § The arrow. Two greps settle it: a literal `points="…"` on
   an element classed `head` is a defect (heads ship empty), and every `.head` must read back a
   computed `points` in the browser probe — including the clones inside a `#bloom` glow layer.
   Then measure: the head's axis (tip minus base-midpoint) within **1°** of the path's end
   tangent, its base within **0.5×stroke-width** of the path end, and every head vertex inside
   the SVG's viewBox. Straight arrows hide this bug — a hand-drawn head only reads broken on a
   curve — so measure the curved ones even when they look fine.
3f. **Footage-moves check (long-form):** the opening zoom-out (107 → 100 over 10f cubic) is baked
   on clip 1, and every plan-marked emphasis beat has its push-in (100 → 108 over 12f cubic).
   Read the Transform keys back — they are NOT on Motion; a `Motion/Scale` query reports zero
   keys and reads as "no push-ins here". The ramp midpoint must read exactly 107.00 at frame 6
   of 12 (a linear bake reads 104.00).
3g. **Borrowed-palette check:** any colour borrowed from a depicted product or brand must match a
   SAMPLE off the real asset (measure the render against the source logo/screenshot — e.g. Claude
   orange `#d97757` from `assets/logos/claude-icon-color.png`). A guessed brand hex is a defect
   (`default-overlay-style.md` § BORROWED PALETTES).
4. **Report:** built/placed counts, the `graphics-qa.py` summary line (green), the waivers with
   their reasons, the 2–3 frames as proof. Then step 5c: hand the draft to the **`edit-review`**
   polish loop (the gate, then two-dimension review rounds until zero verified defects) BEFORE
   presenting for review. The **live second
   pass** starts after that — iterate part-by-part (edit → re-render the one part →
   re-place/re-assemble), and on those tweak rounds skip the self-QA frame grabs: just edit,
   render, show — the fixes get called live from the review.

## Not this skill

Deciding graphics (step 5a: `graphics-plan`) · the color grade (pipeline step 4 — it runs BEFORE
this step and lives on the track UNDER the graphics; never fold it into the build) · captions and
background music (conditional passes, not numbered steps) · SFX (pipeline step 6, after this
step and its defect loop: `workflows/sfx-plan.py` then the lane's placer) · audio of any kind (the polish is **pipeline step 3**, run right after the
cut lands on its finish surface, never during the build) · export (step 8, `finalize.sh`).
