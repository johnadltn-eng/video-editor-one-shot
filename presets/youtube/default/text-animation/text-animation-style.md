# Text Animations — the animated emphasis-text default

Word-synced emphasis text for long-form YouTube: emphasize a phrase, punch a claim, or fill a
dead stretch with some editing. Each word rises in and settles into place,
timed to the spoken word. Locked 2026-08-29 on the your-job intro — you dialed
every value live against the timeline. **Text animations are the default sprinkle-in:
when a stretch needs something and nothing else is called for, reach for a text animation.**

**The preset IS the animation + the fonts + the layout law.** Color, glow, and position
flex per animation; the motion, the type, and the spacing rules never do.

## 🔒 THE LOCK

- **Font:** Helvetica Bold (system), lowercase, tight tracking — letters almost touching
  with a hair of space (−4.4% of size). Ink `#eef4ff` off-white. All px metrics
  (tracking, word gap, glow blur, rise) are ratios of the line's font size.
- **Size & layout = THE LAYOUT LAW (2026-08-29; band re-measured 2026-08-31):**
  the block lives in **THE LOW BAND, y765 → y1030** (`TOP_MIN`/`BOTTOM_MAX` — the numbers are
  MEASURED per shoot, authoritative spec + re-derivation via `chin-line.py`:
  `default-overlay-style.md` § THE LOW BAND), centered
  on **cy 850** inside it. Line-height 1.05, descender allowance below the last line.
  Each line is SOLVED to a target width (**default 1250px**) so the type fills the
  screen — sizes are derived, never picked. **Lines balance to the same width**: a short
  last line automatically gets bigger type (capped at 2× its sibling — past that reads
  broken), so a multi-line block is a clean rectangle. ⚠ The one-big-word treatment is
  for a genuinely SHORT standalone last line ("one big word in the emphasis font");
  splitting a normal phrase to force it "looks bad" — regular phrases break into
  near-equal lines at near-equal sizes.
- **THE BAND IS THE HARD FRAME, and type size is what gives.** A block too tall for the
  265px band scales down WHOLE until it fits. That is not a fallback, it is the rule
  that makes **a two-liner smaller and lower than a one-liner** (2026-08-31:
  "when the text animation is just one line those are pretty much already fine as is,
  but mostly for the two liners they need to be smaller and further down — they're too
  close to my chin"). Two lines in the same band means ~115px type where one line gets
  ~150px, and that is correct: two lines of 115 still carry more ink than one of 150.
  Never widen the band to keep a two-liner big — the chin is the reason the band exists.
- **Emphasis sprinkling:** mark 0-2 power words with `*asterisks*` in the text.json
  phrase → they set in Playfair Italic w700 at x-height parity. Adds variation and
  styling; if it's not needed, don't do it. Display text renders AS TYPED (a capitalized
  proper noun stays capitalized); transcript matching ignores case.
- **Entrance:** small rise easing to rest (**22px at 90px type**, ratio-scaled) —
  `power3.out`, 0.55s: fast off the mark, curves, slowly rests into place. **No
  fade-in** — the word cuts to full opacity the instant it starts. Nothing else moves.
- **Sync:** word start times come from the canonical transcript
  (`outputs/<job>.transcript.json` — never re-transcribe), each led **80 ms early** so
  the settle lands on the audio. This lead is what makes it feel on time; without it the
  rise reads late.
- **Glow (default on):** a faint black glow behind each word for pop + readability —
  **stacked blurred duplicates of the word, never text-shadow** (the house glow rule):
  wide layer blur 24/90 of size @ 1.0 + tight layer 9/90 @ 0.80, both black
  (bumped from 21/8 @ 1.0/0.70 on your call, 2026-08-29).
- **Exit:** the whole block fades + drifts up 18px over 0.35s, ~0.7s after the last word
  lands (`hold` knob). Tighten the hold when the next spoken beat needs the frame clear.

## The two-font system (2026-08-29)

**Helvetica Bold is the standard text font. Playfair Display Italic at weight 700 is
the emphasis font** (locked 2026-08-29 after A/B-ing Instrument Serif and DM Serif
against your reference sample) — for the one power word / proper noun in a phrase
("edited by *Claude*"). Emphasis can also be an underline or a highlight animation; the
font swap is the go-to. The exact recipe, all four locked:

- **File:** `PlayfairDisplay-Italic-VF.ttf` from `assets/fonts/` (variable font — copy
  into the job and `@font-face` it with `font-weight:400 900; font-style:italic`, then
  use `font-weight:700`; a system name silently falls back).
- **Size = X-HEIGHT PARITY, measured not guessed:** Playfair sits large on its body, so
  it runs at nominal **×1.033** next to Helvetica (126px beside 122px Helvetica). Verify
  by lowercase ink height (PIL on the TTFs), never by eye — the old "+15-20%" rule was
  an Instrument Serif artifact and oversized Playfair by 16%.
- **Tracking:** −2.8% of font size (−3.5px at 126px) — the tightest before the serifs
  collide. The surrounding Helvetica keeps its own −4.4% lock.
- **Style:** italic always; the weight-700 axis is the bold, no stroke hacks.

## Variety-law knobs (added 2026-08-29, your-job rest-of-intro)

- **`~tildes~` mark a RED word** (`#ff4d5e`, the negation/danger accent): "i ~didn't~ have
  to babysit", "~defeats~ the purpose". One red treatment per animation, never stacked with serif
  on the same word.
- **`"entrance": "pop"`** — the house pop per word (0.90 → 1.10 over 3 frames, snapping to
  1.00 on frame 4); **`"slam"`** for the heavier stamp (1.16 → 1.00 over 7 frames), for beats
  like "one shot." `"punch"` is a legacy alias that still resolves to `pop` — the retired 1.45×
  one-frame shape it used to name is gone (see animations.md § Retired).
  **`"entrance": "flicker"`** — the whole block strobes in on the locked 7-frame 20%-pulse
  pattern (for stakes/legal-vibe beats). Default stays the rise (= `riseIn`).
- **`"tilt": -2`** — rotates the block (the air-quotes skeptic treatment: "\"fully automated\"").
- **`"display": "..."`** — render different words than were spoken, 1:1 token map ("*never*
  been built before" over the spoken "ever been built before"). The caption is the MEANING;
  use when the spoken fragment reads broken out of context.
- **`"place": <t>`** — clamp the animation's timeline place to a clip-head V1 cut so it can't
  bleed backward across the edit; word 1 just loses part of its 80 ms lead.

## The pop + motion blur (2026-08-31)

Two saved entrance shapes, both defined in `build.py`'s `POP_PRESETS`:

| `entrance` | Shape | Use |
|---|---|---|
| **`pop`** | scale **0.90 → 1.10 over 3 frames (power2.out), then snap to 1.00 on frame 4** | The SCALE entrance, opt-in per spec. The builder's default is the RISE (`riseIn`) — see the note above the table. |
| **`slam`** | scale **1.16 settling to 1.00 over 7 frames**, power2.out | The occasional heavier hit. Not the default. |

`punch` is the legacy spec name and still maps to `pop`. Per-pop overrides:
`pop_from` / `pop_over` / `pop_frames` / `pop_ease` (`pop_over: 0` = settle shape).

**The pop's beat is the SNAP BACK, not the growth.** Coming in under size is the
wind-up; overshooting past 1.0 and then correcting on a single frame is what reads
as a text animation. The grow **eases out** rather than running linear, so it leans into 1.10
and hangs there a beat before the correction — that makes the snap hit harder
(tested both ways against each other, 2026-08-31). The old shape (start big, settle down) reads as a slam landing, which is
a different and heavier feeling — that's why both are kept.

**Motion blur is OPTIONAL and off by default (2026-08-31: "forget about the
motion blur, that's adding too much complexity").** The shapes above are authored to
read correctly unblurred. The flag still exists if a specific graphic wants it, but
do not reach for it by default, and see the 12 fps warning below before combining:

```bash
MBLUR=1 ./render.sh <id>          # MBLUR_SHUTTER=4 for more blur
```

It is TRUE motion blur, not a blur filter: the renderer supersamples at
`MBLUR_SS` (5) x the target rate, averages `MBLUR_SHUTTER` (3) consecutive frames
into each output frame, then decimates back — about a 216-degree shutter. It does
NOT need Premiere. Three things it gets right, each of which was a real bug first:

- **Averaging happens on PREMULTIPLIED pixels**, then unpremultiplies back to the
  straight alpha Premiere and Resolve expect. Averaging straight alpha fringes
  every soft glyph edge.
- **`tmix` uses a TRAILING window**, so the shutter centred on output frame `m` is
  sample `m*SS + (SHUT-1)/2` — not `m*SS`.
- **The supersampled stream ends mid-group** (both rates `ceil()` independently),
  so the tail needs `tpad=stop=SS` or the last output frame vanishes silently.

Verify any change to that chain against a no-blur render of the same comp: same
frame count, same onset frame. A shifted onset means the text animation no longer lands on
its word.

**Verify STRUCTURE, not bit-equality — the renderer is not reproducible on motion
frames (measured 2026-08-31).** Two runs of a byte-identical command differed on 8
of 45 frames, every one of them a frame where something was moving, up to 108/255 on
glyph edges (about 0.27% of pixels; visually identical, sub-pixel sampling jitter).
Static frames come back bit-identical, and most run pairs match exactly, so the
jitter is intermittent — which makes it a trap: a clean A/B "proves" nothing and a
dirty one is not evidence of a regression. Compare frame count, onset frame, and
measured positions instead. When you need to prove a script change is a no-op, diff
the RESOLVED commands (`bash -x`), which is deterministic, rather than the output.

## Flex per animation (the "sometimes" knobs)

- **Placement:** `center` is the default and follows the layout law (low block, cy 850);
  `left`/`right` — beside the face, x120 from the edge, default y300. Pick the side away
  from the speaker's head; check a frame, don't guess. `width` widens/narrows the fill target;
  `cy`/`y` shift the block; `size` forces a fixed size and disables the solving.
- **A text animation never bleeds across a V1 cut (2026-08-29), and the builder enforces
  it (2026-09-02).** The text belongs to its shot. `build.py` reads `transcript/cuts.json` and
  ends every comp ON the next V1 cut by itself (`"until"` overrides: a number, or `null` to
  disable). Two exits are then possible and it picks: if the last word can settle and hold
  ≥ 0.25s before the cut, the rise-out plays (two frames before the end, hard-killed on the last
  frame); if not, **the cut IS the exit**, no fade, the picture cut carries it, exactly as a hard
  cut to a full-screen is its entrance. `<id>.meta.json` says which (`"exit": "riseOut" | "cut"`)
  and nothing is trimmed by hand any more. A cut that falls INSIDE the phrase is a ⚠ (split the
  phrase).
- **Color:** black variant (`"color": "#111"`) for bright backgrounds.
- **Glow off** (`"glow": false`) when the text already contrasts hard with what's behind it.
- **Line breaks:** `lines` splits the phrase; default is one line. Break so no line
  crowds the 1920 frame (~100px breathing room each side).
- Never cover the face; during the outro keep the right side + bottom clear (end screens).

## Usage

```
cp -R presets/youtube/default/text-animation projects/<job>/hf-graphics/text-animation
cd projects/<job>/hf-graphics/text-animation
cp text.json.example text.json   # phrase per animation; knobs optional
./render.sh                      # → renders/<id>-alpha.mov + the PLACE TIME per animation
```

- Build reads the job's canonical transcript automatically (folder position derives the
  job; `--job <dir>` overrides). It prints where each animation goes on the timeline (also in
  `compositions/<id>.meta.json`) — place the alpha mov on the graphics track (**V3** on this
  preset's map: V1 footage, V2 grade, V3 graphics) at exactly that time.
- Straight alpha, correct for Premiere/Resolve (drop it on an overlay track in any other app
  the same way). A lane that composites premultiplied converts on its own side — see
  `LANES.md` § step 5.
- Render at the **timeline's** rate: `FPS=30000/1001` default, override to match, and build
  with the same rate (`python3 build.py --fps 24000/1001`): the two-frame exit margin and the
  hard-kill frame are computed from it.
- **Phrase = the words as SPOKEN; markers are punctuation-aware** (`*official*.` and
  `*official.*` both show "official." in emphasis). A filler the copy leaves out ("well over,
  you know, six months") is skipped automatically, up to three; a paraphrase is not: on a miss
  the builder prints the closest transcript run with timestamps. `display` renders different
  words over the spoken timing (1:1 token map).
- The band fit accounts for the rise-in travel: a block is sized so its ENTRY frames (22px
  below rest, ratio-scaled) stay above y1030, not just its rest position.
- **Re-renders get a new filename** (`VER=b ./render.sh p1`) and a fresh import — never
  overwrite a mov an editing app has placed.

Provenance: locked on `your-job` — hand comp iterations a→h (textpop1), then the
v2 builder (intro-pop / fully-auto) carrying the layout law. When to reach for a text animation and
how it combines with the other moves: [`../creative-moves.md`](../creative-moves.md).
