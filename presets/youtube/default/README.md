# YouTube Default — the long-form finishing preset

The ONE default for long-form YouTube videos. Steps 1-2 of the pipeline (intake, rough cut) are
universal and unchanged; this preset defines everything after the cut: timeline architecture,
section structure, title cards, SFX, graphics tier, grade, audio finish, and the export lock.
Every other look (`vox-collage`, `liquid-glass` takeovers, `signature`) stays **opt-in by name**.

Skeleton reverse-engineered from a real shipped assembly (read live off the Resolve API 2026-08-27), then **fully dialled in
on Premiere** across the `your-job` intro (2026-08-29 → 08-31) — the graphics vocabulary,
the animation registry, the low band, the prop glow and the footage moves were all tuned there.
The look is app-agnostic; the per-app mechanics live in those apps' skills. Read the LANES section
next if you are finishing in anything other than Premiere.

## 🔒 LANES — what is universal, and what is per-app

**This preset is a LOOK, not a Premiere project.** Everything that decides how the video looks —
the graphics, the type, the motion, the timings, the colour, the structure — is app-independent,
because it is either a number (a frame count, a scale percentage, a hex) or it is rendered by
HyperFrames into a file any editor can take. Only two things are per-app: **where you put a clip**
and **how you bake a move onto footage.**

| Layer | Universal? | Notes |
|---|---|---|
| Graphics, title cards, text animations, backgrounds | ✅ fully | HTML comps → **alpha ProRes 4444 movs** (overlays) or **opaque mp4s** (full-screen graphics, grain baked; title cards via `titles/render.sh`, no grain). Any NLE takes both. |
| The in/out registry, THE FLOAT, arrows, burst reveals | ✅ fully | Runs inside the comp, before the file exists. |
| Card language, colours, THE LOW BAND, prop glow, scope | ✅ fully | Design rules, nothing to execute. |
| Section structure, title-card cadence, track roles | ✅ fully | A track map is generic NLE vocabulary (this one was read off a **Resolve** project). |
| The numbers on a footage move | ✅ fully | "100 → 108 over 12 frames, cubic ease-out" means the same everywhere. |
| **Placing** a graphic at a time on a track | ⚠️ per-app | Mechanics per lane, and which lanes have one: [`LANES.md`](../../../LANES.md). |
| **Baking** a footage move (zoom, push-in) | ⚠️ per-app | Same. Anything undocumented = keyframe by hand from the numbers above. |
| **Grading the footage and NOT the graphics** | ✅ the rule / ⚠️ the mechanism | The contract is universal: footage graded, graphics untouched, established before graphics are placed. How you get there is per-app. |
| Audio finish + export settings | ✅ the target / ⚠️ the mechanism | The targets are stated below; how each app hits them is per-lane. |

🔒 **THIS PRESET SAYS WHAT; THE APP SKILLS SAY HOW** (`premiere-pro`, `davinci-resolve`, `capcut`).
Nothing app-specific belongs in this file — not a command, not an argument quirk, not a track
index dressed up as a look decision. Mechanics live with the app because they are
preset-independent: placing an alpha mov at a timecode is the same move whichever preset asked for
it, so written here it would be re-written once per preset per app.

**[`LANES.md`](../../../LANES.md) is the index between the two.** One row per pipeline step, one
column per app, each cell saying scripted / manual / unvalidated / gap and pointing at the recipe.
Read the row for the step you are on before doing any per-app work.

**Premiere is the dialled lane, and its detail lives in its own docs.** The `premiere-pro` skill
and `lanes/premiere/premiere-grading.md` go down to argument quirks and traps that cost real time; that
detail is an asset, and it stays there. This file points at it and never repeats it, so the other
lanes read the same preset without a Premiere recipe in the way. They get what has actually been
validated, and nothing is invented.

**An undocumented lane is not a blocked lane.** If a step has no recipe for your app, the universal
spec above it is enough to do it by hand: the graphics are just movs to drop on an overlay track,
and a footage move is a scale ramp you can keyframe in any editor. Do it manually, **say so in the
run report**, and if it becomes routine write the recipe into that app's skill — never into this
preset.

## Project setup

- **Match the project to the SOURCE fps.** ffprobe the raw first; the app's own read of the
  imported clip is the final authority (iPhone footage is variable-rate and can ingest at a
  different rate than ffprobe reports). How a project is created at that rate is per-lane
  ([`LANES.md`](../../../LANES.md) § step 2 → the app skill's project-setup section).
- **Resolution follows the footage:** 3840×2160 when the video is screen-recording-heavy (screen
  captures are 4K sources), 1920×1080 when the footage is 1080. Whether the timeline auto-conforms
  a mismatched asset or needs a scale set is per-lane (the app skill); never hand-scale before
  checking which.
- **Every media file lives in `projects/<job>/`.** One shipped job played 3 clips straight out of
  `~/Downloads` (cold-open, demo recording, meme b-roll) — that is a defect, not a pattern. Copy
  cutaway/meme media into `broll/` at intake so the project survives a Downloads cleanup.
- **Whether the audio polish swaps source files or applies clip effects is a lane property**
  (see Audio polish below); the timeline is built against the raw sections either way.

### 🔒 The AUTHORING FRAME is always 1920×1080

**Every locked number in this preset is in a 1920×1080 coordinate space** — THE LOW BAND
(y765 → y1030), the placement table, the text-animation builder (`W, H = 1920, 1080`), the
background comps. **Author every graphic at 1920×1080 regardless of the footage's resolution**,
and let the timeline scale the overlays if the project is 4K. **How that scaling happens is
per-lane and is the ONE place a 4K project needs a decision:** some apps auto-conform a 1080
asset to a 4K frame and some need a scale set on the graphics track; the app skill says which
(via [`LANES.md`](../../../LANES.md)), and doing it the other app's way either crops the middle
out or leaves the overlay a quarter-size.

⚠️ **`chin-line.py` reports the chin in the SOURCE video's own pixels.** On a 4K raw, normalize
before using it: `y_authoring = y_measured × 1080 / source_height`. Feeding a 4K chin number
straight into a 1080 comp puts every overlay off the bottom of the frame.

## Timeline architecture — the track map

Read off `full assembly 4K30` as shipped, then **amended 2026-08-31 to seat the grade**:
the shipped job had graphics on V2 and no grade track. The map below is the one to build.

⚠️ **The grade track is why this map has to exist before the graphics pass starts.** The grade
has to reach the footage and nothing else, so on any track-based app the grade layer sits BETWEEN
footage and graphics, and it is created empty at project setup: adding it later means inserting a
track *underneath* graphics already placed (recoverable on the lanes that have a recipe for it,
but never free). A lane whose footage-only separation is a grouping rather than a track needs no
track shuffle; the contract (footage graded, graphics untouched, before any graphic lands) is the
same. Mechanics per lane: [`LANES.md`](../../../LANES.md) § step 4.

| track | role | contents |
|---|---|---|
| V1 | the spine | EDL-replayed section clips + 3s section title cards, butt-joined |
| **V2** | **the grade** | ONE grade layer spanning the whole timeline (pipeline step 4): an adjustment layer or the app's equivalent. It sits here — above the footage, below the graphics — so it grades the footage and nothing else. Created empty at project setup, before any graphic is placed. |
| V3 | graphics | HyperFrames alpha ProRes 4444 overlay cards (rendered STRAIGHT alpha; a lane that composites premultiplied converts on its own side) + opaque full-screen mp4s, meme/b-roll cutaways, text callouts |
| V4 | accents | mascot/sticker PNGs that sit above a V3 cutaway |
| V5 | spare | keep empty for one-offs |
| A1 | voice | linked section audio — untouched during the cut and assembly; the step-3 polish lands here right after the cut (see Audio polish below) |
| A2 | SFX, primary | every event's first sound (step 6, [`sfx.md`](sfx.md)); the title-card whoosh at every section boundary lands here too |
| A3 | SFX, layer 2 | a second sound within 2 frames of one already on A2 (the tonal or weight half of a hit) |
| A4 | SFX, layer 3 | a third layer on the same frame; rare |
| A5 | music | optional flat bed, opt-in only (`background-music` rules) |

**Media pool layout:** section mp4s + title cards + timeline in the root, `graphics/` (the alpha
movs), `broll/`, `sfx/` (the bundled SFX library, imported wholesale from `assets/sfx/`), `Archive/`.

## Section structure

```
cold open (proof clip, ~7s) → intro (graphics-heavy, basic tier)
→ [ title card → section body ] × N → outro
```

- **Title card:** 3.0s (90 frames at 30), opaque mp4 on V1 between sections. Built by
  [`titles/`](titles/) (below). Placing the cards on V1 at the section boundaries is per-lane
  ([`LANES.md`](../../../LANES.md) § step 5; scripted on some lanes, hand-dropped on others); the
  card and whoosh timings here are the contract.
- **Whoosh:** `assets/sfx/Genius Intro Sound.wav` on A2, placed with each card, ~3.5s used,
  ~1s crossfade-out tail so it ducks under the section's first line.
- **Chapters:** the title-card timeline positions ARE the YouTube chapter timestamps — read them
  off the timeline at export time, no separate bookkeeping.
- **Sections are separate rough-cut sub-jobs** (`sections/<name>/`, raw symlinked, own transcript)
  — one WhisperX run each, replayed onto the assembly by EDL.
- ⚠️ **Sections are a MULTI-TAKE structure, not a requirement.** They exist when the video was
  filmed as separate takes. **A single continuous raw is ONE section** — no title cards, no
  chapter boundaries, no cold-open split — and the structure above collapses to
  `intro → body → outro`. Do not invent section boundaries (and therefore title cards) inside one
  continuous take; if the script clearly wants chapters, that is a one-line ask at plan time, not
  an assumption. The shipped `your-job` intro is the single-raw case: no title cards.
- **Outro:** keep the right side + bottom band clear during the last ~20s — YouTube end-screen
  cards snap there.

## Opening zoom-out — every video starts with it (2026-08-29)

**THE MOVE (universal):** the first clip on the spine opens slightly punched in and settles to
100% — **scale 107 → 100 over 10 frames, cubic ease-out, about the frame centre**, starting on the
clip's first frame. Fast off the mark, rests into place (the same settle feel as the text
animations; it was cut from 2.5s to 10 frames — it's a snap, not a drift). Overlays on the
graphics track do NOT inherit it: they hold still while the footage settles.

**HOW:** per-lane, via [`LANES.md`](../../../LANES.md) § step 5 → that app's skill. On any lane
with no recipe it is two keyframes and an ease done by hand — scale 107 → 100 across the first 10
frames, cubic ease-out. Nothing here needs scripting to be correct.

## Emphasis push-in — the default zoom-IN (2026-08-31)

When you vocally emphasize a phrase on camera, the footage pushes in: **100 → 108 over 12
frames, cubic ease-out**, starting ~2 frames before the phrase and holding to the clip's end
(the next cut resets it). Paired with a text animation of the phrase. Full spec +
the reasoning: [`creative-moves.md`](creative-moves.md) move 5.

**THE MOVE (universal):** scale **100 → 108 over 12 frames, cubic ease-out, about the frame
centre**, beginning ~2 frames before the emphasized word and held to the clip's end.

**HOW:** per-lane, via [`LANES.md`](../../../LANES.md) § step 5 → that app's skill. On a lane with
no recipe it is two keyframes on clip scale with a cubic ease-out, by hand; the numbers above are
the whole spec.

**Verify anywhere:** the ramp's midpoint (frame 6 of 12) must read exactly **107.00**. That is the
cubic signature; a linear bake reads 104.00 there. The check is app-independent.

## In / out animations → [`animations.md`](animations.md) — THE REGISTRY

🔒 **Every entrance and exit is one of the presets there; never author a bespoke one.**
Scale family — **`pop`** (the default for a free-standing OBJECT), **`slam`**, **`flash`**;
**type, cards and panels RISE instead**. Travel family —
**`riseIn` / `riseOut`** (the nudge, and the everyday default) and **`slideIn(from)` /
`slideOut(to)`** (OFF SCREEN, four directions — a rise is not a slide). **The default exit is
`riseOut`**: up 18px plus fade, 0.35s / `power2.in`. A **full-screen** graphic's first element
enters on **frame 0** when it is near-full-frame (the cut IS the entrance), and a
**near-full-frame** element rises rather than pops. Plus the variation
principle — vary by ROLE: peers in a graphic SHARE one entrance, the odd one out takes the
different one (exits do NOT vary). `flash` is banned on 12 fps graphics.
`draw-on` (arrows, tangent-computed heads) is a reveal, not a move. Hold life is THE
FLOAT, not an entrance — see creative-moves.md move 2.

## Full-screen backgrounds → [`backgrounds/`](backgrounds/)

The two standard fields behind any full-screen graphic: **`bg-light`** (light-gray
gradient, feathered navy vignette, film grain baked in) and **`bg-dark`** (deep navy,
faint 100px brand grid, edge fade). Locked 2026-08-29; specs, knobs, and the
vignette-measurement lesson in [`backgrounds/README.md`](backgrounds/README.md).
Renders are regenerable cache (`./render.sh`, ~90s each) — comps are the truth.

## Section title cards → [`titles/`](titles/)

The kinetic Inter riser (per-letter rise on an exponential curve, stepped to 12 fps, sampled
motion blur). Usage:

```
cp -R presets/youtube/default/titles projects/<job>/hf-graphics/titles
cd projects/<job>/hf-graphics/titles
cp titles.json.example titles.json   # edit ids + copy
./render.sh                          # → renders/<id>.mp4 (card) + <id>-alpha.mov (overlay)
```

The opaque card uses `renders/grid-bg.mp4` (the navy brand-grid backdrop) when present (drop your own backdrop loop at `titles/renders/grid-bg.mp4` — the branded one does not ship), and falls back to the solid navy field when it isn't. The V1 timeline only ever
places the opaque card; the alpha variant exists for overlay use.

## Emphasis text animations → [`text-animation/`](text-animation/)

Word-synced emphasis text for a phrase or a dead stretch — each word rises in and settles (`power3.out`), timed to the spoken word with an 80 ms lead. **The
lock is the animation + the font** (Helvetica Bold, lowercase, tight tracking, no fade-in,
faint black glow); the one power word in a phrase gets the emphasis font — **Playfair
Display Italic w700** (the two-font system, full recipe in the style doc), and the
builder carries the LAYOUT LAW (low block, width-solved sizes, balanced lines); placement /
color / glow flex per animation. Spec + knobs:
[`text-animation/text-animation-style.md`](text-animation/text-animation-style.md). Same usage shape as `titles/`:
copy the folder into `projects/<job>/hf-graphics/`, write `text.json`, `./render.sh`, place
the alpha movs on the graphics track at the printed times.

## 🔒 Grade (pipeline step 4 — BEFORE graphics, and underneath them)

**THE TARGET (universal):** the footage carries a consistent look, and **the graphics carry none
of it.** One treatment across the whole timeline, applied to the footage layer only, established
before a single graphic is placed.

**Footage-only is the requirement, not a preference.** Every colour in this preset is a locked
hex — accent royal, the prop glow, card fills, the two full-screen backgrounds — chosen to read
over footage and against each other. A grade sitting on top of the graphics shifts all of them,
and it shifts them invisibly, because a graded card still looks like a card.

### Why it runs before graphics (two independent reasons)

1. **Track mechanics** — lane-dependent, and the reason is cheap to undo. On a lane where the
   separation IS a track (an adjustment layer affects every track below it, so the layer lives
   *between* footage and graphics), that track is free at project setup and awkward to insert
   under clips already placed. Recoverable, so this reason alone would not fix the order; reason 2
   does. On a lane where the separation is a grouping rather than a track (a color group) this
   reason does not apply at all — reason 2 still does.
2. **Measurement validity.** The step-5c defect loop measures real numbers off program renders:
   prop-glow lift outside a prop's box, low-band legibility, card contrast over the shot. Grade
   afterward and every one of those measurements was taken against a picture that does not ship.

**Clip transforms are a non-issue.** The opening zoom-out and every emphasis push-in are
clip-level Motion/Transform on V1, applied *before* the adjustment layer sees the composite. The
grade lands on the already-transformed image, and re-baking a move later never disturbs it.

### 🔒 THE LOOK: `Autumn-Rec709.cube` as a Creative Look (2026-09-01)

The house LUT is [`assets/luts/rec709/Autumn-Rec709.cube`](../../../assets/luts/rec709/Autumn-Rec709.cube)
(the bundled Rec709 LUT, 33³), replayed from the `Autumn-Rec709.lookparams` beside it. The whole
library (15 Rec709 + 15 LOG cubes, your own) lives under `assets/luts/`,
moved out of `~/Downloads` 2026-09-01; [`assets/luts/README.md`](../../../assets/luts/README.md)
lists it and names the per-lane replay tool ([`LANES.md`](../../../LANES.md) § step 4). It is applied on the grade layer as a **Look** (the cube renders AFTER any
correction dials, so one colour effect holds everything). **The locked preset (2026-09-01): Look Intensity 70, Creative > Adjustments > Saturation 115, everything else at
default.** Same settings for every job regardless of footage. This preset is the single
source: every long-form `youtube/default` job inherits Autumn-Rec709 from here, and each lane's
replay tool reads it as its own default; a job never picks its own. (London-Rec709 was the first pick the same day, tried in the Input LUT slot;
Autumn was chosen over it. Its `.lutparams` stays beside its cube as a working input-slot
example, nothing uses it.)

⚠️ **The cube is universal; the two dial values are Lumetri's.** "Look Intensity 70 / Creative
Saturation 115" names Premiere controls, so another app hits the same appearance with its own
equivalents — the cube at reduced strength plus a small saturation lift — and **verifies by
measuring a frame, not by matching numbers.** Never report the dial values as applied on a lane
that has no Lumetri.

No per-machine install is needed: the cube data is embedded in the params file, so the replay
carries it. Minting params for a NEW LUT is the only time the file is browsed to by hand.

**Any cube in the library can become the look.** It takes ONE hand-application, ever, to capture a
cube's params; from then on it replays on any job by name, on any machine. That is a lane mechanic,
not a look decision. The default never moves unless someone changes it deliberately.

### 🔧 How each lane gets there

**The step is TWO things and no more: the layer, and the Look on it.** Nothing about them is a
per-job decision. Which lanes have a scripted recipe, which are unvalidated, and where each recipe
lives: [`LANES.md`](../../../LANES.md) § step 4. On a lane with no recipe, put an adjustment or
effects layer between the footage and the graphics track (or apply the cube to the footage clips
directly) and set the look by eye to the intensity and saturation above; the contract is only that
the footage is graded and the graphics are not.

⚠️ **Verify from a program render with the layer toggled, never from an effect readback.** The tell
is a mean-RGB channel delta in the tens between the two frames. A delta of 0 does not mean "the LUT
failed" — on every lane it can equally mean the track's output is off, so read the track's mute
state before drawing any conclusion.

### 🔒 There is no colour-correction step (2026-09-01)

The grade is the grade layer plus the Look. Nothing measures or corrects the footage first.
Properly shot footage needs no correction (an auto-correct pressed on the actual footage moved
nothing worth keeping), and an algorithm that fixes badly shot footage is a project of its own,
parked. If a clip needs a correction it is a manual call, made before the Look, and any dials
you settle on ride inside the captured `.lookparams`.

A measured "auto-correct" solver was built and deleted the same day (2026-09-01): every reference
frame it was calibrated against was the wrong thing, including an app's Auto pressed on the
adjustment layer itself, which analyses the layer's own blank media rather than the footage. The
full story and the two measurement lessons (never gray-world a lit set; pick the measurement mask
once, on the uncorrected frame) live with the Premiere grading doc, where the experiment ran:
[`lanes/premiere/premiere-grading.md`](../../../lanes/premiere/premiere-grading.md).

### One consequence to carry

**Generated b-roll placed above the grade stays ungraded.** For a Higgsfield clip that is usually
right (it was never camera footage), but it is a choice — drop it on V1 instead if it should take
the same look.

## Graphics (step 5)

- **The default vocabulary = [`creative-moves.md`](creative-moves.md) (2026-08-29 —
  apply UNPROMPTED):** text animations liberally (the default sprinkle), punch cut-to-graphic at
  key claims (hero + caption on a locked background, hard cuts), scene slides, self-made
  vector props entering on the house pop, emphasis push-ins paired with pops. Entrances follow
  [`animations.md`](animations.md) and the variation principle. Locked 2026-08-31:
  **bg-DARK full-screens render 12 fps style AND carry the subtle glow pass**
  (`STEP_FPS=12`, never with MBLUR) while bg-light full-screens get neither, pop-ins
  use the saved `pop` / `slam` shapes, hold life is the no-rotation **float** (two presets,
  `subtle` for a whole graphic and `medium` for one big hero element) — all
  specified in creative-moves 2 / 4b / 4c.
- **Cards:** [`default-overlay-style.md`](default-overlay-style.md) (blue UI cards over the
  footage) remains the language for informational beats. Its accent furniture carries
  **THE PROP GLOW** (bars, dots, chips, meters bloom in their own colour; type is default-off — it may glow where the subject itself emits light). Extended takeovers / bespoke art /
  other looks stay opt-in by name at plan time, never inferred.
- **Build:** per-job `hf-graphics/` generated build, part-by-part renders
  (the `graphics-build` skill).
- Plan with `graphics-plan`, build with `graphics-build`, place on the graphics track (V3 in the
  map above; the placement mechanics per lane are the app skill's, indexed by
  [`LANES.md`](../../../LANES.md) § step 5), then converge with `edit-review`.

## Definition of Done — the autonomous quality bar (2026-08-29)

The your-job intro's first clip (pop → punch graphic with slide + props → push-in
+ pop) IS the bar. A default pass is not finished until it hits that level, unprompted:

- Every text/graphic beat **word-synced** off the canonical transcript (80ms lead), cut
  points a hair before their trigger words, nothing bleeding across a V1 cut.
- Layout obeys the law: measured, not eyeballed — sizes solved to width, x-height parity
  verified by ink measurement, pixel-sampled when a "more intense" change must be proven
  (the vignette lesson: alpha values lie, pixels don't).
- **Every under-the-face overlay inside THE LOW BAND (y765 → y1030)**, band re-derived for
  the shoot with `workflows/chin-line.py` — see `default-overlay-style.md`. A two-line
  block is smaller and lower than a one-liner; that falls out of the band, don't fight it.
- **Every accent prop glowing; type glow default-off** (THE PROP GLOW — a subject that emits
  light may glow its type, never via text-shadow). Confirm a masked prop's
  glow actually renders — measure light OUTSIDE the mask, don't trust the CSS being present.
- **Every entrance and exit is a REGISTRY preset** (`animations.md`) — never improvised. The
  default exit is `riseOut`. Entrances vary by ROLE: peers share one, the odd element
  out takes the contrast. No `flash` on a 12 fps graphic. **A full-screen graphic's first
  element enters on frame 0** when it is near-full-frame — no blank lead, or the cut and the
  arrival read as two frame-scale events (the defect scales with the element's size).
  **A near-full-frame element rises instead of popping** (a pop that big lurches the picture).
- **Hold life is THE FLOAT**, one of the two presets, spanning the element's whole on-screen
  life on a wrapper, with the in/out composing on top.
- **Action beats are SCENES, not cards.** No decoration shaped like data — a meter with no
  scale is a defect, not filler.
- **Every arrowhead COMPUTED from its path's end tangent** via `arrow()`, never typed as
  `points`. Measure the curved ones: a head 20° off its shaft is the tell.
- **A READABLE graphic HOLDS its complete content 2-3s** (budget backwards:
  `reveal_end = duration − HOLD`), reveals in word BURSTS on a ~12 fps beat (never a linear
  per-frame wipe), deterministically (no `Math.random`), **with the zero frame pinned empty**
  (a content reveal never opens half-done).
- Every comp probed in the browser before rendering; every placed composite verified
  from the app's **program output**, never from the comp render; every placement followed by
  a track readback. No craters, no stale media, no missing heads.
- **Rhythm law held:** a visual event at least every ~10s, visual-content stretches
  covered continuously, treatments and backgrounds varied — never the same move twice
  in a row, never a flat stretch.
- Entrances varied by ROLE per the variation principle; emphasis font sprinkled where it earns
  its place; grain on every full-screen graphic.
- **The process (2026-08-29): plan → build one graphic at a time, converging EACH to
  right before the next** (simple pop = verify and move on; complex/full-screen = as many
  rounds as it takes, ~10 min working budget) → all placed → **one final edit-review loop
  until zero defects**. Don't stop at the first plausible render, and don't park a known
  defect for the loop.

## Audio polish (pipeline step 3 — right after the cut lands)

**THE TARGET (universal):** one static pass over the whole timeline that lands the voice at a
consistent level — **never dynamic loudnorm (it pumps), never per-segment gain (it clicks at
every cut).** The house chain is **a static gain into a hard limiter at −6 dBFS, and the gain is MEASURED: the
raw's kept speech goes to −17 LUFS integrated before the limiter** (`workflows/voice-gain.py`; the
target was locked 2026-09-03 on your-job, whose −32.1 LUFS kept speech took +15 dB and
sounded exactly right: peaks about 8 dB over the ceiling, the limiter working every stressed
syllable, the saturation you want). That is the number set on any lane that can apply timeline
effects (or bake them into the render). A lane with no audio-effects surface hits the same goal by normalizing the
source files instead (per-file to a loudness target plus a limiter, then swapping the media);
its numbers differ because the mechanism does, deliberately. Which lane does which: the app skill.

- **Never touch levels during the rough cut or assembly** — one pass over the whole timeline,
  run immediately after the EDL replay lands (pipeline step 3, you 2026-08-28). A timeline
  rebuild discards clip effects — re-apply after any re-replay.
- **The gain is one command on every lane:** `uv run workflows/voice-gain.py projects/<job>`
  measures the RAW over the EDL's kept ranges (`transcript/cuts.json`, ebur128 integrated
  loudness, never the whole take: dead air would drag the number down and over-gain the speech)
  and prints the whole-dB gain for −17 LUFS plus the Premiere Amplify value. It needs no flat
  render, so it is the same call on an app finish and on chat-only. The old "+10, or +8 if peaky"
  rule is retired; a peaky raw simply measures louder and gets less gain.
**HOW, per lane:** [`LANES.md`](../../../LANES.md) § step 3. Every lane must land the same target;
what differs is only where the gain is applied (clip effects on a timeline, or baked into the
source files on a lane with no audio-FX surface).

## Captions

- **No burned-in captions.** YouTube CC serves long-form.
- **No thumbnail either (2026-09-01).** It used to be a standing part of every long-form
  job; it came off the line entirely. A thumbnail is a publishing asset, not an edit, and this
  preset finishes at the exported file. `thumbnail-generator` is still installed and still runs
  when you ask for one by name, but **nothing in this preset calls it and a job is complete
  without one.** If it ever rejoins the line it goes AFTER export, never mid-edit.

## Export — the lock

**THE TARGET (universal):** H.264 MP4, 2160p (or the project's native resolution), AAC 48 kHz,
one clip, straight to `projects/<job>/outputs/<job>.final.mp4`. **Verify the finished FILE with
ffprobe** — never trust the app's own reported settings. The encoder settings each app needs to
reach that target are per-lane: [`LANES.md`](../../../LANES.md) § step 8. An app not listed just
needs to hit the same numbers; the preset does not care which encoder dialog produced them.

Then `./finalize.sh <job> --apply` for promotion + the `~/Downloads` export copy — lane-agnostic,
it only looks at the files in `outputs/`.

⚠️ **Whether the run renders the final or the creator does is a lane property**
([`LANES.md`](../../../LANES.md) § step 8): on the lane where you render, the automated work
STOPS at "placed + verified" and the export settings above are for when you render. Either way
`finalize.sh` runs only once a final file actually exists in `outputs/`; never render one to
satisfy the step.
