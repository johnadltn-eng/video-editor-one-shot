# Creative Moves — the default editing vocabulary

**This is what "edit this video" produces, unprompted.** Locked 2026-08-29 off the
your-job intro — you dialed every move live, and the finished first clip IS the
quality bar (see the README's Definition of Done). These moves are the DEFAULT for
youtube/default: reach for them on your own; don't wait for instructions.

Read with [`animations.md`](animations.md) (entrance vocabulary),
[`text-animation/text-animation-style.md`](text-animation/text-animation-style.md) (type system + layout law),
[`backgrounds/README.md`](backgrounds/README.md) (the two locked fields).

## The moves

### 1. Text animation — the default sprinkle (use liberally)
Word-synced animated text on the A-roll for emphasized phrases or dead stretches.
**When nothing else is called for, a text animation is the move.** Built by
`text-animation/build.py` (copy the folder in, write text.json); the builder carries the whole
layout law. Emphasis font on 0-2 power words via `*asterisks*`. A text animation NEVER
bleeds across a V1 cut — trim the placed clip to the edit.

**It lives in THE LOW BAND (y765 → y1030) like every other under-the-face overlay** —
the builder enforces it, so a two-line block comes out smaller and lower than a one-liner
by construction. Full spec + how to re-derive the band per shoot:
[`default-overlay-style.md`](default-overlay-style.md) § THE LOW BAND.

### 2. Cut-to-graphic — the punch cut (key claims)
On a power phrase, hard-cut the footage to a **full-screen graphic on a locked
background** (bg-light or bg-dark — they ALTERNATE, see THE DENSITY NUMBERS), and hard-cut back — no fades, ever.
**Full-screen graphics on bg-DARK render 12 fps style by default (2026-08-31)**
— the stepped motion reads as motion graphics; see 4c. bg-LIGHT full-screens stay at the
timeline rate. The dark treatment travels as a pair: 12 fps AND the glow pass below;
light full-screens get neither.
**A full-screen has no face to clear, so THE LOW BAND does not apply — but it does not
sit dead centre either (2026-08-31): a tad smaller, a touch low.** One transform
on the content layer does it and keeps the glow clone pixel-synced —
`transform:translateY(40px) scale(0.92); transform-origin:50% 50%` on `#content,#bloom`.
Child GSAP transforms compose with it, so entrances and floats need no rework.
Anatomy of the shipped "edited by Claude" graphic (reference implementation ships in
this preset: [`reference/punch-cut-reference.html`](reference/punch-cut-reference.html)
— original built on the reference job):

- **Background:** the locked field baked into the comp (gradient + vignette CSS),
  film grain added by the same ffmpeg post-pass as the background asset
  (`noise=c0s=7:c0f=t`, libx264 crf 14).
- **bg-dark full-screens ALWAYS carry the glow pass (2026-08-31, level locked
  at subtle):** build the content into TWO synced layers — `#content` plus a `#bloom`
  clone — and give the clone `filter:brightness(1.45) contrast(1.12) blur(30px);
  mix-blend-mode:screen; opacity:0.26; pointer-events:none`. Bright elements bleed
  light into the dark field, and because both layers are animated by the same class
  selectors the glow is frame-exact with every move. Populate both layers in JS
  (`cloneNode` into each) rather than duplicating markup by hand. 0.26 is the locked
  level — 0.40 was built and passed on, 0.58 blows highlights toward white. bg-light
  gets NO glow (light bleeding needs a dark field to bleed into).
  **The overlay lane gets the same light from THE PROP GLOW** — accent furniture
  (bars, dots, chips, meters) blooms in its own colour; type is default-off, glowing only
  where the subject itself emits light (neon, an LED readout, a terminal accent). Spec +
  the `overflow:hidden` trap: `default-overlay-style.md` § THE PROP GLOW.
- **Hero visual front and center** — big (640px on the mascot), horizontally centered,
  face-height. The graphic's subject is THE thing; caption below it.
- **Hero glow** = blurred duplicates of the image behind the sharp copy (never
  drop-shadow): blur 90px @ 0.38 (scaled 1.06) + blur 34px @ 0.30.
- **Caption** under the hero: Helvetica Bold lowercase + Playfair Italic on the power
  word, x-height parity.
- **Annotation arrow** where it helps: tail starts AT the caption, draws up to the hero
  (draw-on spec in animations.md — tangent-computed head, never eyeballed).
- **Entrances follow the variation principle (vary by ROLE)** — here the hero, the arrow and
  the caption each do a different job, so each takes a different move: hero flicker-in, arrow
  draw-on, caption rise-in. Where a graphic has PEERS instead (steps in a flow, rows in a list),
  they share one entrance and only the odd element out contrasts. ⚠️ On a bg-DARK punch-cut the
  hero cannot flicker — that graphic renders 12 fps style, which drops the strobe (`pop` or
  `slam` instead; see 4c and `animations.md` § No flash at 12 fps).
- 🔒 **Hold life = THE FLOAT — TWO presets, `subtle` and `medium` (2026-08-31;
  replaces the retired ±2° wiggle). ZERO rotation.** A slow x/y drift with x and y on
  DIFFERENT periods, so the path traces a shallow ellipse instead of a straight diagonal —
  that period mismatch is what reads as floating rather than sliding. The element **rests at
  its authored position and drifts out and back (0 → A → 0)**; it never straddles it.

  🔒 **The float spans the element's ENTIRE on-screen life — entrance and exit compose ON TOP
  of it (2026-08-31).** It does not wait for the entrance to finish and then begin:
  the mascot floats *through* its flicker-in, the g6 hero floats *while* it rises. A graphic
  that holds still and then starts moving reads as two separate animations bolted together.
  In practice: `float(target, 0, DUR, preset)` — the whole composition, every time. Drift
  while the element is still invisible costs nothing and means it is already alive the
  instant it appears.

  | Preset | Travel | Periods | Max step @29.97 | Use on |
  |---|---|---|---|---|
  | **`subtle`** | 6px x · 8px y | 1.25s · 0.95s | 0.25 · 0.44 px/f | a WHOLE graphic — a card, a chat thread, a panel and its furniture |
  | **`medium`** | 10px x · 16px y | 1.35s · 1.05s | 0.39 · 0.80 px/f | ONE big hero element — the mascot, a hero card, a single node |

  **Which one is decided by what is moving, not by how big the frame is.** A whole graphic
  drifting reads as the panel being alive; the same amount on a lone hero reads as dead.
  Medium is derived from the mascot in the `edited` punch-cut, the reference implementation
  shipped in this preset: [`reference/punch-cut-reference.html`](reference/punch-cut-reference.html).

  **Values are TRAVEL in px, and neither preset scales with element size.** Two presets with
  fixed numbers is the whole point — "scale amplitude with element size" is what let graphics
  drift off the standard one at a time.

  ```js
  const FLOAT = {subtle: [6, 8, 1.25, 0.95], medium: [10, 16, 1.35, 1.05]};
  const float = (target, t0, t1, preset) => {
    const [AX, AY, PX, PY] = FLOAT[preset];
    const leg = (prop, A, p) => {
      let cur = 0, out = true;
      for (let t = t0; t < t1 - 0.02; t += p) {
        const rem = Math.min(p, t1 - t);
        cur += ((out ? A : 0) - cur) * (rem / p);   // partial last leg, SAME speed
        tl.to(target, {[prop]: cur, duration: rem, ease: 'sine.inOut'}, t);
        out = !out;
      }
    };
    leg('x', AX, PX); leg('y', -AY, PY);   // y drifts UP first
  };
  float('#floatWrap', t0, t1, 'subtle');
  ```

  ⚠️ **Specify TRAVEL, never amplitude.** That ambiguity shipped one pass at double intensity:
  `±10` reads as "amplitude 10" but the element moves 20.

  ⚠️ **Never let the final leg be truncated.** Giving it a short duration but the full travel
  makes the graphic cover its whole excursion in a fraction of the time, so the float visibly
  ACCELERATES into the exit — measured 0.82 px/frame in the last 0.4s against 0.44 everywhere
  else, which reads as the graphic getting agitated right before it leaves. Scale the last
  leg's travel by the time remaining (above) so the speed stays flat.

  ⚠️ **Measure at the TIMELINE rate.** A 12 fps-style render steps 2.5× further per rendered
  frame by definition; probing at the animation rate will make you "correct" a float that is
  already right.

  **A hold shorter than one period gets a partial leg, and that is correct** — g6's hero and
  g14's node both hold ~0.92s, so on `medium` they trace ~14px of y instead of 16. If a
  graphic needs more life, give it a longer hold, never a hotter float.

  ⚠️ **Which is why the float ALWAYS goes on a WRAPPER — no exceptions.** Once it runs the
  whole composition it necessarily overlaps the entrance and the exit, so any x/y they touch
  would fight it (GSAP gives the property to whichever tween was added last, silently). The
  wrapper is `position:absolute; inset:0`, so the child's own `left`/`top` still resolve
  against the full frame once the transform makes the wrapper a containing block; the child
  keeps the entrance, the exit, opacity, className, everything. Where the layers are
  hand-duplicated for the glow pass (`#content` + `#bloom`), the wrapper goes in BOTH; where
  the clone is built in JS from `innerHTML`, one edit covers both.

  Author it as explicit alternating tweens — never `repeat: -1`, which makes the timeline
  duration infinite and breaks the paused-seek render.

  On your-job: `subtle` on `g7` and `g12`, `medium` on `g6-wall`'s hero,
  `g14-flow`'s node and the `edited` mascot — all five on a wrapper, all five spanning
  `0 → DUR`.
- **Hero entrance option — the RACK FOCUS (shipped on the g6 wall):** the hero
  **`slideIn('bottom')`** — from off screen, so it is a SLIDE, not a rise (0.75s power2.out,
  starting ~0.45s before its word) — while the
  ENTIRE background dims and defocuses over the SAME window (opacity → 0.32,
  `blur(0px) → blur(6px)`). The law behind it: **a background state change must ride
  the move that motivates it** — a 4-frame dim at 12 fps is barely one stepped frame
  and reads as a switch, not an animation. Three traps: (1) the blurred layer needs
  `position:absolute; inset:0` FIRST — `filter` makes an element the containing block
  for absolute descendants, so filtering an unpositioned wrapper re-anchors everything
  inside it; (2) declare `filter:blur(0px)` in the CSS so GSAP interpolates from a
  number, not `none`; (3) name EVERY background layer in the tween — a sibling grid
  layer left out stays sharp and bright while the rest recedes (smooth gradient layers
  like base/vignette stay out on purpose: blur is a no-op on them, and blurring a
  full-frame opaque layer pulls transparency in at the edges and rims the frame).

**Timing craft:** cut TO the graphic a hair before the trigger word lands (~30ms early;
the word's own 80ms-led caption pops right after the cut). Cut BACK just before the next
spoken beat you want on camera. Trigger word "edited" at 2.067 → cut at 2.035; cut back
at 6.306 with "fully" at 6.436.

### 3. Scene slide — second beat inside a graphic
When the spoken content moves while the graphic holds, don't cut — **slide**: current
content group `slideOut('left')` as the next `slideIn('right')`, over the STATIC background
(the field never moves). The numbers are the registry's, not bespoke: **out 0.38s
`power3.inOut`, in 0.75s `power2.out`** ([`animations.md`](animations.md) slide family — the
in-slide must NOT take a power3 ease; measured, it dumps half the travel into step one). Text
on the incoming panel rides in pre-set; later words appear word-synced after it lands.

### 4a. Vector props (self-made VFX)
Literal-word moments (shot/break/boom) get **self-generated vector art in the comp** —
NEVER YouTube green-screen pulls (2026-08-29 lock: stock quality is a lottery and
choosing clips is a human call; if real footage is truly needed, flag it for your
manual pass). The shipped bullet holes: irregular dark core polygon + thin radiating
crack triangles (solid fills, house icon rule), three distinct shapes, varied
rotation/scale. **Entrance = the house pop (see below).** Stagger multiple hits a few frames apart
(4.85 / 5.03 / 5.16 against "shot" at 4.773). SFX sells these later at the SFX step.

### 4b. THE SCALE ENTRANCES + motion blur (2026-08-31)
**Free-standing OBJECTS scale in** — a prop, a chip, an icon, the mascot, a flow node — using one
of two saved shapes. **Type, cards and panels RISE instead** (`riseIn`; see
[`animations.md`](animations.md) § The default entrance and exit). Full spec, knobs and the
render recipe:
[`text-animation/text-animation-style.md`](text-animation/text-animation-style.md).

- **`pop` — the default OBJECT entrance.** Scale **0.90 → 1.10 over 3 frames (power2.out), then snap
  to 1.00 on frame 4.** Comes in UNDER size; the overshoot-and-correct is the beat.
- **`slam` — the occasional.** Scale **1.16 settling to 1.00 over 7 frames**
  (power2.out). Heavier, lands rather than pops. Reach for it on a punchline that
  should hit like a stamp (the shipped "one shot." card), not as a general default.

**Motion blur is OPTIONAL and OFF by default** (2026-08-31 — it "adds too
much complexity"). Both shapes are authored to read correctly unblurred. The flag
`MBLUR=1 ./render.sh <id>` still exists in both renderers and does real supersampled
motion blur without Premiere, but don't reach for it by default — and never pair it
with 12 fps style (see 4c).

**Scale `MBLUR_SS` with the TRAVEL DISTANCE, not with taste.** The default 5
supersamples cover a small scale pop fine, but anything crossing a large part of
the frame renders as 3 discrete ghost copies instead of a smear — the samples are
simply too far apart (measured on a full-height card slide, 2026-08-31: `MBLUR_SS=15`
was the fix). Pair a raised SS with `MBLUR_SHUTTER` at roughly 180° of that sample
count (`SS=15` → `SHUTTER=7`); the 216° default gets mushy once travel is large.

### 4c. 12 fps style — stepped animation (2026-08-31)
**THE DEFAULT for full-screen graphics on a DARK background, and only those**
(2026-08-31). The stepped motion reads as motion graphics against the navy
field. Everything else runs at the timeline rate: bg-LIGHT full-screens, overlay
cards, stat callouts, and text animations on the A-roll. The scope pairs with the glow —
a bg-dark full-screen gets 12 fps + glow; a bg-light one gets neither.
`STEP_FPS=12 ./render.sh <id>` animates at 12 fps and holds each frame, then expands
back to the timeline rate by duplication — the on-2s / stop-motion look.

🔒 **No `flash` on a 12 fps graphic (2026-08-31).** One step is 83ms, and `flash` is
built from single-frame (33ms) gaps, so they are dropped: measured on g14, the authored six
states rendered as TWO — a dim hold at luma 17.8 for seven frames, then full at 52.1. Use `pop`
or `slam`. Generally, a move here gets only `duration × 12` distinct states, so anything
authored in single frames must be re-expressed in whole 83ms steps. The working
renderer ships in this preset: [`reference/fullscreen-render.sh`](reference/fullscreen-render.sh)
(copy into the job's `hf-graphics/gfx/`; the text-animation `render.sh` carries the same
flags for alpha overlays). It composes
with `MBLUR` (the shutter then spans a 12 fps frame, so blur is heavier by design).
Grain is applied AFTER the expansion at full rate: grain is a camera artifact, not
animation, and stepping it reads as a compression bug.

**Do NOT combine 12 fps style with MBLUR.** An instant appearance (`opacity 0 -> 1`)
landing inside a shutter makes that frame average empty-plus-present, and at 12 fps
that partial-opacity frame is HELD for ~3 timeline frames — so every element reads as
FADING IN. Measured on the g6 wall: a card went 7.8 -> 18.9 (held 3 frames) -> 83.4
with blur, versus a clean 7.8 -> 83.2 without. Fixing it means snapping every
appearance to the step grid minus half a shutter, which is more machinery than the
look is worth. Render 12 fps style unblurred; the stepping already reads as motion.

**At 12 fps the EASE is the smoothness.** A move only gets `duration × 12` distinct
positions, so a hard ease-out spends most of them standing still: a 0.55s power3.out
rise measured 384 → 344 → 336 → 332 px — it teleports on step one, then creeps. The
same rise at 0.75s power2.out measured 508 → 428 → 376 → 348 → 336 → 332, a real
deceleration. Prefer power2.out and ~0.75s for big travels; when a stepped move looks
wrong, measure the per-step positions off the render before touching anything else.

Two other things to watch: word-synced events quantize to the 12 fps grid (up to
~83 ms of shift, so re-check anything that must land exactly on a word), and the
expansion makes the output a few frames long — harmless, placement pins the out point.

### 4d. READABLE graphics — the HOLD is the deliverable (2026-08-31)

**When a graphic exists so the viewer can READ something — a prompt, a command, a code block, a
config, a quote, a DM, a list of specifics — the complete content must sit still for 2-3
seconds.** People pause and screenshot this kind of graphic. If the reveal is still running when
the clip cuts, they never get a frame worth pausing on.

*"If we're showing a prompt, we should probably have the full prompt on screen longer so the
viewer has time to screenshot it or pause and look at it... the typing animation probably needs
to be a lot faster or it needs to come in earlier."*

**So budget the slot backwards from the hold, not forwards from the reveal.** The hold is the
point; the type-on, draw-on or stagger is garnish, and it gets whatever time is left:

```
reveal_end = clip_duration − HOLD        (HOLD = 2.5s for anything text-heavy)
```

g19 is the worked example. In a 4.50s slot it typed a 316-character prompt until 3.90 and held
the complete text for **0.60s** — unreadable, and unpausable in practice. Retimed to type
0.25 → 2.00, it now holds for **2.50s** in the identical slot: same graphic, same duration,
4× the readable time. Measured on the render by counting neutral-bright text pixels per frame
(exclude the accent cursor — its luma sits right at a naive threshold and the blink then makes
half the hold frames read as incomplete).

#### The reveal itself: BURSTS, never a linear wipe

**Revealing N characters every frame is a progress bar wearing a monospace font.** It has one
constant rate and no rhythm, and it reads as robotic however fast you run it. you: *"it just
looks a little stiff... split it up into chunks of words appearing at a time, that way it looks
more like mimicking real typing instead of just robotically revealing at a linear speed."*

Three things make it read as typing, and all three are cheap:

1. **Reveal by WORD BURST, not by character** — 2–6 words at a time.
2. **Hold each burst about a 12 fps beat** (~2 timeline frames at 29.97). The stepping is what
   kills the wipe feel; it does NOT require rendering the comp at 12 fps.
3. **Double the hold on a burst that ends in punctuation.** That hesitation is most of the
   realism — it is the only cue that says a mind is behind the keys.

**Everything must be DETERMINISTIC — never `Math.random`,** or the headless render seeks to
different text on every pass. And use a fixed irregular PATTERN rather than a modulo: `(i*5+2)%3`
looks varied and collapsed to 21 of 23 bursts being exactly 3 words, which is uniform in the one
dimension that matters. A cycled list works:

```js
tl.set(el, {innerText: ''}, 0);                       // PIN THE ZERO FRAME — see below
const BURST = [3, 2, 5, 2, 4, 3, 2, 6, 3, 2, 4, 2];   // words per burst, cycled
const holds = chunks.map(c => /[.,?!]$/.test(c) ? 2 : 1);
const step  = (T1 - T0) / holds.reduce((a, b) => a + b, 0);  // solved to land exactly on T1
// ...then tl.set(el, {innerText: sofar}, Math.round(t / F) * F) — snap each to the frame grid
```

Measured on g19's render: **25 discrete steps held 1–4 frames each**, the 4s being the
punctuation pauses, against a new state every single frame before.

🔒 **PIN THE ZERO FRAME, or the reveal opens half-done.** A positioned `tl.set(el, {innerText})`
does not reliably revert when the renderer seeks back to the start — GSAP records whatever was
last applied as the "from" value — so g19 shipped a pass whose frame 0 already read
*"All right, go"*. `tl.set(el, {innerText: ''}, 0)` fixes it. This is the same law as every
element starting at CSS `opacity:0`: **never rely on the DOM's initial value surviving a seek,
state the zero frame explicitly.** It applies to any content-mutating reveal — text, counters,
list rows, a progress label.

Practical notes:

- **A faster type-on does not look wrong.** g19 already ran at ~89 chars/sec, far past human
  typing; at ~180 it reads as a fast paste or a stream, which is what an agent doing the typing
  should look like anyway.
- **Starting earlier is the cheaper lever.** The reveal can begin during the entrance — g19 starts
  typing at 0.25 while the terminal is still rising, and the two do not fight because the rise is
  nearly settled by then.
- **A blinking cursor keeps a static hold alive.** Solid while typing (a real terminal does not
  blink mid-keystroke), then a steady 0.30s blink through the hold.
- **If the content genuinely cannot be read in the slot, say so at plan time** — the fix is a
  longer clip or less text on screen, and both are the creator's call. Do not silently shrink the
  hold to fit the animation.

### 5. Emphasis push-in + text animation (A-roll emphasis)
When you vocally emphasize a phrase on camera: **8% push-in (100 → 108) over 12
frames, cubic ease-out** (2026-08-31 — "a little longer and zoom in a tad bit
farther, but keep the eased smooth motion"; was 6% over 8 frames), starting ~2 frames
before the phrase, holding to the clip's end (the next cut resets naturally) — paired
with a text animation of the phrase.

One command, `at` taking the word's SEQUENCE timestamp (the README carries the full line and
the traps): `zoom '{"clip":N,"from":100,"to":108,"frames":12,"ease":"cubic","fps":"30000/1001","at":<sec>}'`.

Baked as **per-frame Transform scale keys** (not Motion — the two are separate effects,
and a survey of `Motion/Scale` will report no keyframes at all). Both `Scale Height` and
`Scale Width` carry identical keys, so any edit must touch both. Key times are in
**SOURCE time** (`clip.inPoint.seconds + offset`), not sequence time. Values are
`100 + 8 * (1 - (1 - i/12)^3)` for `i` in `0..12`:

```
100.00  101.84  103.37  104.62  105.63  106.41  107.00  107.42  107.70  107.88  107.96  108.00  108.00
```

⚠️ **When the clip already carries keys, ADD — never clear.** Clip 1 holds the opening
zoom-out (107 → 100) *and* a later push-in in the same property track, so a blanket rewrite
destroys the opening move. The `zoom` command handles this — given `at`/`offset` it clears only
from the ramp start onward — and it refuses (changing nothing) if the ramp would start before
the clip or run past its end.

### 6. Opening zoom-out
Every video's first clip: 107 → 100 over 10 frames, cubic — already locked in the
README. Don't ask, just bake it.

### 7. Real artifacts beat drawn ones (2026-08-30)
When the script points at something that **actually exists and is findable** — other
people's videos, a tweet, a repo, a product page, a comment — go get the real thing.
A drawn stand-in for a real artifact (a vector "video card" with a play triangle where
a thumbnail belongs, fake title bars, a made-up duration) reads as placeholder even
when it's well drawn. This is the counterpart to move 4a, not a contradiction: **invent
vector art for abstract/literal-word VFX, fetch the real asset for real things.**

- **YouTube thumbnails:** `yt-dlp "ytsearch12:<topic>" --skip-download --flat-playlist
  --print "%(id)s | %(view_count)s | %(channel)s | %(title)s"` to find them, then
  `https://i.ytimg.com/vi/<id>/maxresdefault.jpg` (fall back to `hqdefault.jpg`).
  Real durations via `yt-dlp --skip-download --print "%(duration_string)s"`. Store under
  the job's `assets/thumbs/<videoId>.jpg` and hardcode id + duration in the comp so the
  render stays deterministic.
- **Pick for VISUAL variety, not just relevance.** Any hot topic has thumbnail clone
  clusters (the your-job wall's first pass had three identical "CLAUDE + VIDEO"
  layouts and two identical "Claude Video Is Insane" layouts). Two near-identical
  thumbnails on one wall read as a rendering bug. Build a contact sheet, look at it,
  then swap duplicates for alternates. Spread light/dark/warm/cool and faces/non-faces.
- **Put one of your own in** when he's genuinely part of the set — a quiet easter egg,
  never the hero.
- **Layout note:** real thumbnails carry their own baked-in text, so don't add title
  lines under them — that's two layers of type fighting. A thin frame + the real
  duration chip is enough to read as "video". And when a card bleeds off the right
  frame edge, flip its chip to the card's left, or it renders visibly clipped.
- **CSS trap:** the thumbnail rule (`height:100%; object-fit:cover`) will also match
  any hero/mascot image sharing the class — an override must reset `height` AND
  `object-fit`, not just width, or the hero gets silently cover-cropped at the sides
  (this clipped the mascot's edge nubs once before it was caught).

## Rhythm — the retention law (2026-08-29)

### 🔒 THE DENSITY NUMBERS — measured off the shipped intro (2026-08-31)

The rhythm law gives a FLOOR ("something every ~10s") and the scope contract gives a card
CEILING, but nothing told you the actual cadence — so a conformant plan could ship at half the
reference density and still pass every rule. These are the shipped `your-job` intro's
real numbers. **Plan to them, per MINUTE of runtime** (the old "per section" scoping is
meaningless on a single continuous raw, which is one section by definition):

| per minute of finished runtime | target | shipped intro (121.0s, 25 graphics) |
|---|---|---|
| **graphic events, all kinds** | **11–13** | 25 events = **12.4/min** |
| of which **text animations** | 6–7 | 13 = 6.4/min |
| of which **full-screen graphics** | 2–3 | 5 = 2.5/min |
| of which **scenes** (the enacting kind) | ~1 | 2 = 1.0/min |
| of which **cards / stat callouts / annotations** | 2–3 (the 4–7 ceiling is per intro or section) | 5 = 2.5/min |
| **emphasis push-ins** (on V1) | 1–2 | 4 = 2.0/min |
| **longest bare stretch** | **≤ 6s** | 5.44s |
| **full-screen share of runtime** | **≤ 25%** | 21.4s = 17.7% |

Read that as a cadence, not a quota: the beats still decide WHICH graphic goes where, and a
stretch with nothing to show stays bare. But a plan landing at 5 events/minute is not "restrained",
it is under the reference look, and a plan at 20 is over it.

**Background rotation is not a coin flip.** bg-dark and bg-light alternate across the video's
full-screens (shipped: 2 dark, 2 light, alternating), and the choice drives locked render flags —
bg-dark gets `STEP_FPS=12` **and** the glow pass, bg-light gets neither. Pick by what the visual
reads better on (dark field for bright/glowy/UI-style art, light field for dark ink and props),
then check you have not ridden one field twice in a row.


- **Something visual happens at least every ~10 seconds** — more when it flows. No stretch
  of nothing, ever; rhythm beats perfection.
- **A visual-content stretch gets continuous coverage**: when the script is describing
  something visual, graphics run for its WHOLE length — 30 seconds of visual storytelling
  means 30 straight seconds of visuals telling it.
- **The ladder:** beat clearly visual → a visual move (punch cut, chart, prop, card).
  Nothing obvious → a text animation. Never bare.

## Variety — the anti-stale law (2026-08-29)

Variety IS retention: new things keep happening, so it never feels flat.

- **Text animations are EXEMPT from this law** — they are the connective tissue that carries the
  density floor and legitimately run back to back (the shipped intro does). For the big moves:
  **never the same FULL-SCREEN treatment or card template twice in a row.** Rotate moves, rotate entrances (the
  variation principle), rotate looks.
- **Word-level treatments inside pops**, when the content calls for one: a **red
  highlight** sweeping a negation word ("that's *not* it" → `#ff4d5e` family); an
  **inline mini data-viz** behind a quantity word ("100% into discipline, 20% into
  structure" → a bar fills behind each word to its number); an underline; the emphasis
  font. When nothing calls for one, a plain pop is right — don't force it.
- **Backgrounds rotate:** pick `bg-light` or `bg-dark` per punch graphic by what the
  visual reads better on — the dark field for bright/glowy/UI-style visuals, the light
  field for dark art, ink, and props. Don't ride one field for the whole video.

## Placement mechanics (how these reach the timeline)

**Universal:** graphics render as **mp4** (full-screen, grain baked) or **ProRes 4444
straight-alpha mov** (overlays), then land on the graphics track at the plan's times. Two rules
hold in every app:

- **Every full-screen graphic gets the film-grain pass** — the standing recipe, same as
  bg-light's: `ffmpeg -vf "noise=c0s=7:c0f=t" -c:v libx264 -crf 14 -pix_fmt yuv420p` on
  the comp render before import. Alpha overlays ship clean.
- **Verify composites from the app's own program output**, never from the comp render — the
  composite over real footage is what the viewer sees.

- **A re-render is a NEW filename**, never an overwrite of a placed file: every editing app
  caches something about a placed path, and the failure is silent on all of them.
- **After any placement, read the track back** (start/end per clip) before trusting it.

**Which track, which command, and which alpha convention each app wants is the app skill's,
not this preset's: [`LANES.md`](../../../LANES.md) § step 5** points at the recipe per lane
(`premiere-pro`, `davinci-resolve`, `capcut`). On any app without one, drag the movs onto an
overlay track above the grade at the printed times; nothing above is required to get the look,
only to script it.
