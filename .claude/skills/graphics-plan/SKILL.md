---
name: graphics-plan
description: "Storyboards the graphics for a video BEFORE any are built — the creative-direction step (5a) between the graded cut and the build. Reads the finished-script transcript, builds a narrative beat sheet, probes the footage, then storyboards every graphic (exact copy, placement, timing, motion) and self-reviews the whole plan so the FIRST pass ships at review quality. Outputs graphics-plan.{json,md}. Does NOT create graphics. Triggers: plan the graphics, graphics plan, where should graphics go, ideate graphics, what graphics for this, graphic direction, storyboard the graphics, beat sheet, plan visuals for this reel."
---

# Graphics Plan — beat sheet → storyboard → self-review

**Step 5a of the pipeline.** Rough-cut already produced the finished script (the cut-aligned
transcript). This skill turns that script into a **storyboard**: a beat-by-beat plan of
graphic-or-not, what exactly appears, where, when, and how it moves — *before anything is built*.
The creation step (5b) builds from this plan; captions come after. The colour grade is step 4 and
is already on the timeline before this plan is written.

**The bar: one-shot quality.** The plan must be good enough that the build needs no
back-and-forth — every correction you would make on a review pass, this skill makes on itself
in Step 4 before you ever sees the plan. A plan that needs "you should have made this a graphic"
afterward is a failed plan, not a draft.

**This skill decides graphics. It does not create them.** No rendering, no HyperFrames, no HTML.

---

## 🔒 STEP 0 — resolve the preset + the tier (before any planning)

**The preset is decided by format, automatically.** Format was auto-detected at intake (horizontal
raw → long-form YouTube; vertical → short-form, explainer vs TikTok/raw read from the content).
Each format has exactly one default preset, and presets are fully independent — read ONLY the
chosen preset's own docs, never another preset's:

| Format | Default preset | Read |
|---|---|---|
| long-form YouTube | `presets/youtube/default/` | its `README.md` + `default-overlay-style.md` + **`creative-moves.md` (the default vocabulary AND § THE DENSITY NUMBERS — the per-minute cadence you plan to)** |
| short explainer | `presets/instagram/explainer/` | its `default-overlay-style.md` |
| TikTok/raw | `presets/tiktok/raw/` | its style doc — **hook card only, plan nothing else** |

**A named preset overrides the default** — "edit this in the Vox style" → `presets/youtube/vox-collage/`
(and its `motion-craft.md` craft layer), "liquid-glass" → `presets/youtube/liquid-glass/`. Only an
explicit name switches presets; nothing else does.

> **"Do a graphics pass" = the BASIC tier. Always. Assume nothing bigger.**

| Tier | Trigger | What it is |
|---|---|---|
| **Basic** ← DEFAULT | "edit this video", "do the graphics", "graphics pass" | the preset's `default-overlay-style.md`: 4–7 cards per intro/section from its templates. Face never covered. |
| **Full** | asked for **by name** — "go all out", "full graphics pass", names a look | takeovers, bespoke art, higher density, whatever the named preset's doc says |

**A tier is never inferred from how good the footage is.** An exciting script is not permission to
escalate. When a beat genuinely wants more than the tier allows, note it in the plan in one line
and plan within the tier anyway — upgrading is your call.

**Two things require an explicit ask (one line, at plan time, never mid-build):**
1. **EXTENDED full-frame coverage** — long takeovers, bespoke scenes, background replacement,
   anything covering your face at length. State the total second-count and get a yes. (Short
   PUNCH-CUT full-screens are part of the long-form DEFAULT since 2026-08-29 — plan them
   without asking, just state their seconds in the plan summary.)
2. **A non-default look** you didn't already name.

---

## Step 1 — the BEAT SHEET (understand the video before decorating it)

```bash
uv run .claude/skills/graphics-plan/scripts/segment-script.py projects/<job> /tmp/video-editor/<job>/beats.json
```

That gives the mechanical grid (sentence beats + timestamps). The beat sheet is what you ADD to it —
read the whole script first and answer, in order:

1. **The arc.** What is this video actually about, in one sentence? What are its 2–3 biggest
   moments (the hook, the core reveal/demo, the payoff)? The storyboard is built around these;
   everything else supports them.
2. **Per beat, its narrative role:** `hook` · `promise` · `setup` · `point` · `evidence` ·
   `demo` · `payoff` · `punchline` · `transition` · `aside`. Merge or split the mechanical beats
   freely when the story says so — the grid is a starting point, not a contract.
3. **Per beat, the showables:** every concrete noun the line contains — a number, a name, a
   product, a process, a before/after, a list. These are the graphic candidates. A beat with no
   showable almost never earns a graphic.

Write the roles into the plan (`role` field). The beat sheet IS the first deliverable — a wrong
beat sheet makes every downstream choice wrong.

## Step 2 — look at the footage (never storyboard blind)

```bash
uv run .claude/skills/graphics-plan/scripts/probe-frames.py projects/<job> /tmp/video-editor/<job>/beats.json
```

One frame per beat lands in `projects/<job>/plan-frames/` (regenerable scratch; works from the flat
render or, on app-finish jobs, straight from the raw via the EDL). Actually look at them. They decide:

- **Screen-recording beats already show the thing** — a demo that's on screen needs an annotation
  or nothing, never a card summarizing what's visible. This is the #1 wasted-graphic mistake.
- **Placement** comes from where you actually is in frame (side to place a card, where your head is),
  not from a guess.
- **Gestures** — a point/hold toward one side is an anchor for that beat's graphic.
- **Energy** — a big delivery moment on camera may land harder plain.

## Step 3 — STORYBOARD the graphics (the creative core)

Walk the beat sheet in story order and decide each beat. **Big moves must earn their slot** — a
full graphic gets planned only when:

- it's the **hook** (the hook always gets the strongest visual in the video),
- it's a **payoff/punchline** worth underlining,
- it has a **showable** the frame isn't already showing (stat, name, list, process, artifact),
- it's a **structure beat** a diagram/flow would make instantly clearer.

Leave BIG moves off: connective tissue, transitions, asides, emotional delivery, rhetorical
setup — those land harder on your face. But on long-form, "plain" is bounded by the RHYTHM LAW
(below): a stretch that would sit bare past ~10s gets a text animation. And **never let two graphics
collide on adjacent short beats**: merge them or let one breathe.

**Spend the creativity where it counts.** For the hook and each major payoff, draft **2–3 distinct
options** and keep the strongest (say why in one clause). Ordinary beats get one good idea, not a
brainstorm. Visuals over text everywhere: the motion/footage/data carries the point; words are a
label, a number, or a hook line. Reserve text-forward cards for hook + punchlines, and remember
**captions come later** (short-form) — don't fill the frame with text a caption will collide with.

**Every `graphic:true` beat is a complete storyboard cell** — the build must need zero guesses:

- **`kind`** — from the vocabulary below, **`template`** — which of the preset's templates it uses (basic tier).
- **`copy`** — the EXACT on-screen words/numbers. Not "a stat card about the revenue" — `"$4,700 / mo"`.
- **`region` + side** — from the Step-2 frame, inside the format's safe zones. **On long-form,
  anything CENTERED under your head goes in THE LOW BAND** (`presets/youtube/default/default-overlay-style.md`
  § THE LOW BAND): the whole stack fits between the measured chin floor and the bottom margin,
  and a two-line block is therefore SMALLER and LOWER than a one-liner. Side callouts keep their
  own zones; full-screens have no face to clear.
- **`start` / `end`** — snapped to word timestamps: in ON the word that names the showable (not the
  sentence start), out before the next thought begins. 2–5s on screen for a CARD; a card that overstays reads as a mistake.
  A SCENE that depicts an unfolding process runs as long as the process does (the shipped chat
  ping-pong graphic holds 8.6s) — the limit there is the beat, not the clock. **A READABLE graphic needs more:** if the beat shows something the
  viewer is meant to read or screenshot (a prompt, a command, code, a config, a quote), the slot
  must fit a **2–3s hold of the COMPLETE content** on top of its reveal — say so in `content` and
  size the slot for it, or flag `⚠️` that the text is too long for the beat.
- **`content`** — one tight paragraph: what's on screen, the hierarchy, the hero element, and the
  motion (what animates, in what order). Written so the build step can build it without asking.
- **`reason`** — why this beat earns it (the second pass reads these).
- **`bg`** (full-screen / punch-cut cells only) — `"dark"` or `"light"`. It is not decoration: it
  drives locked render flags (**bg-dark = `STEP_FPS=12` + the glow pass; bg-light = neither**) and
  the anti-stale law says the field must ROTATE — never ride one for the whole video.
- **`push_in`** (long-form A-roll beats) — `true` where the footage should push in on the
  emphasized phrase (**100 → 108 over 12 frames cubic**, `creative-moves.md` move 5). This is a
  DEFAULT move, so plan it rather than waiting to be asked, but ration it: **2–4 per intro/section,
  on the beats carrying the strongest claims** (the shipped `your-job` timeline carries 4 across 121s = 2.0/min — see `creative-moves.md` § THE DENSITY NUMBERS).
  Pick them from the SCRIPT — the line that lands the claim, the reveal, the stakes — and pair each
  with the text animation of that phrase. Everything else stays still; a push-in on every emphasis
  reads as a wobble.

| Kind | Use it for |
|------|-----------|
| `screen-rec` | the thing actually working — a demo, the agent running (real footage, not a card) |
| `b-roll` | illustrative motion footage over a claim (generate one with your AI-video tool if none exists) |
| `screenshot` | the real artifact — a post, a report, a DM (zoom/pan/annotate it, never park it) |
| `diagram` / `flow` | how it works — steps/pipeline, drawn ON as you talk |
| `data-viz` | numbers in motion — a chart drawing in, a count-up, a ranking |
| `stat-callout` | a single number as a beat — counted up / popped, never static |
| `icon-row` / `list` | a set of things, revealed in sequence |
| `quote` / `comment` | a comment, tweet, DM, testimonial |
| `lower-third` | a name / title / label (long-form) |
| `kinetic-title` | hook + punchlines only — the words ARE the payoff |
| `text-animation` | long-form's default sprinkle — word-synced emphasis text in the low band (the rhythm-law filler; uncounted against the card budget) |
| `punch-cut` | long-form default: hard cut to a short full-screen graphic on a locked background at a power phrase, hard cut back (creative-moves move 2) |
| `annotation` | arrow/highlight/circle pointing at something already on screen |
| `enacting-overlay` | the line is about the FOOTAGE itself (recorded, filmed, captured, live) — add capture UI (viewfinder brackets, a REC dot, a timecode) so the untouched shot reads as that thing, plus a text animation for the words. Purely additive, face never covered, no transform on the footage. Model: g20 |

**Density — long-form youtube/default runs the RHYTHM LAW (2026-08-29): at least one
visual event every ~10 seconds, no bare stretches.** Big moves (punch cuts, cards, charts, props)
on the beats that earn them; **text animations fill every gap** that would otherwise sit empty — they
are the always-available default. A stretch where the script DESCRIBES something visual gets
CONTINUOUS graphics for its whole run (30s of visual storytelling = 30s of visuals). The 4–7
budget still scopes the CARD count per intro/section; pops and creative moves ride on top,
uncounted. Short-form keeps 4–7 per section; TikTok/raw: exactly the hook card. Full-tier
densities live in the chosen preset's own doc.

**Long-form structure beats** are part of the plan too: the section title cards, the cold-open, and
chapter boundaries come from `presets/youtube/default/README.md` — the storyboard places graphics
AROUND that structure (a section's cards cluster early in the section where its claim lands).

**Safe zones (short-form, never break):** every key visual inside y `200 → 1620` (top 200 px and
bottom 300 px are platform chrome); full geometry in the preset's style doc. **Long-form has NO
platform safe bands (retired 2026-08-27):** the rules are never cover the face or important
on-screen content, ~100 px breathing room at the frame edge, the outro's right side + bottom
clear for end-screen cards, and every under-the-face overlay inside THE LOW BAND (measured per
shoot with `workflows/chin-line.py` — spec in the preset's `default-overlay-style.md`).

## Step 4 — SELF-REVIEW (run the review pass you would otherwise run)

Re-read the finished storyboard top to bottom as a reviewer, not the author. Fix everything below
BEFORE writing the plan — these are the exact corrections past first passes needed:

1. **Missed showables** — walk the script once more: any number, name, list, or artifact that got
   no graphic and no `reason` for staying plain?
2. **Wasted graphics** — any card restating what the frame already shows (screen recordings!), or
   summarizing instead of showing?
2c. **A line about the footage itself given a CARD?** "I recorded this", "I filmed the whole
   thing", "this is live" — those want an `enacting-overlay` (capture UI over the untouched
   shot + a text animation), which enacts like a scene at a card's cost. See
   `default-overlay-style.md` § the overlay that enacts.
2b. **Card where a SCENE was needed** — for every `graphic:true` beat, does the line state a
   fact/number/name (card) or describe an action/process/back-and-forth (scene that shows it
   happening)? A card on an action beat narrates instead of depicting. The tell is decoration
   shaped like data — a meter with no scale, a bar with no metric. See
   `presets/youtube/default/default-overlay-style.md` § CARDS NAME, SCENES ENACT.
3. **Rhythm** — graphics evenly clumped or breathing with the story? A payoff needs a beat of air
   after it, not a new CARD on top of it, and no two cards butt end-to-end. **Text animations are
   exempt** — they are the connective tissue that keeps the ~10s floor, and they legitimately run
   back to back (see `creative-moves.md` § THE DENSITY NUMBERS). Check the plan against that table:
   **11–13 events per minute, longest bare stretch ≤ 6s, full-screens ≤ 25% of runtime.**
4. **Variety** — three of the same template in a row reads as a stamp. Vary template, side, and
   scale across neighbors.
5. **Timing** — does each `start` sit on the word that earns it? Does anything overstay?
6. **Copy** — every word on screen exact, short, and in your voice (no marketing
   speak, no em dashes on screen). **Case depends on what the copy IS:** captions and
   text animations stand in for speech and keep the lowercase-casual register; a LABEL inside
   a graphic (card title, nameplate, eyebrow, axis) is not speech and takes title case.
   A leading article drops only when the label NAMES a thing ("Claude Video Editor", never
   "the claude video editor") — in a short descriptive label the article is part of the
   phrase and stays ("The Goal", the eyebrows THE BUILD / THE RULES). Test: answers "what
   is this thing called?" → drop it; answers "what is this number/row?" → keep it
   (default-overlay-style.md § Copy case, you 2026-08-31).
7. **Scope** — count per section within tier, zero unplanned full-frame, face never covered,
   captions zone clear (short-form).
7b. **The band** (long-form) — every under-the-face cell sits inside the low band, and no cell
   is sized as if it had the whole frame. If a beat's copy needs two lines, the plan says two
   lines and expects smaller type; it does not ask for big type AND two lines.
8. **The two asks** — full-frame seconds + non-default look, each stated in one line if present.

Revise the plan, then output. If a beat is genuinely 50/50, keep your call and flag it `⚠️` — one
flag you can answer beats a timid plan.

## Step 5 — write the plan + report

**The gate (2026-09-02): a plan that fails this is not written.**

```bash
uv run .claude/skills/graphics-plan/scripts/validate-plan.py projects/<job>
```

It asserts what the build and the review loop otherwise pay for later: every text-animation cell
STARTS on the first word of its own copy (word − 0.08, within 0.15s, not the sentence, not a guess);
every full-screen edge within 8 frames of a `cuts.json` boundary sits ON it to the frame (off by
one flashes the outgoing shot, g2, g11 and g7 all shipped that way; an edge far from any cut is a
cut back mid-take and passes); a cell flagged `"readable": true` holds ≥ 3.0s; no em dash in copy;
text animations keep the lowercase register; ids unique, fields present; and it prints the density
block against § THE DENSITY NUMBERS. Write the copy AS IT WILL BE SPOKEN for text animations (the
builder matches the transcript verbatim; a filler mid-phrase is skipped automatically, a
paraphrase is not).

Write two reviewed artifacts to the job folder:

- **`projects/<job>/graphics-plan.json`** — machine-readable, consumed by the build (schema below).
- **`projects/<job>/graphics-plan.md`** — the storyboard for your review, and what the second pass
  edits: the arc line, the beat sheet, then per-graphic cells (`# · time · line · role · template ·
  copy · placement · motion · why`), plain beats listed with their reasons.

Report tight: **the preset + tier**, the arc in one line, beats total / graphics count,
**face-covered seconds**, the 2–3 strongest cells, any `⚠️` flags, and the explicit asks if any.

### `graphics-plan.json` schema

```json
{
  "job": "your-job",
  "format": "short-explainer",
  "tier": "basic",
  "preset": "<the chosen preset's style-doc path>",
  "compositor": "premiere",   // the app finish; "resolve" | "capcut" | omit = chat-only
  "duration": 136.56,
  "arc": "one sentence: what the video is and its biggest moment",
  "face_covered_seconds": 0,
  "beats": [
    {
      "id": 1, "start": 0.05, "end": 5.03,
      "line": "I just built this Claude skill that can predict exactly what you need to post to go viral.",
      "role": "hook",
      "graphic": true,
      "kind": "kinetic-title",
      "template": "label card",
      "region": "top-half",
      "copy": "predict what goes VIRAL",
      "content": "Hook title, hero word 'VIRAL' in a royal boxed chip that stamps in last; two-line stack, stepped entrance.",
      "bg": "dark",            // full-screen/punch-cut cells (long-form); omit on short-form
      "push_in": false,        // long-form A-roll only; omit on short-form
      "readable": false,       // true when the viewer is meant to READ it (prompt, code, quote): the slot must hold ≥ 3.0s
      "reason": "the hook — must open on the strongest visual in the video"
    },
    {
      "id": 2, "start": 5.17, "end": 6.49,
      "line": "And yeah, it works.",
      "role": "punchline",
      "graphic": false,
      "reason": "delivery beat — lands harder on your face, air after the hook"
    }
  ]
}
```

Keep `graphic:false` beats in the array (with `role` + `reason`) so the plan is a complete map of
the script — the second pass needs the plain beats too.

---

## Handoff

The plan feeds **step 5b: the `graphics-build` skill owns the whole build** — it builds each
`graphic:true` beat at its `start`/`end` in its `region` per `template` + `copy` + `content`,
renders, places, and QAs. **On an app finish** set
`"compositor"` so the build knows the target: `"premiere"` (alpha overlays on the preset's graphics track + baked
footage moves, per the `premiere-pro` skill), `"capcut"` (`lanes/capcut/capcut-bridge.py`), or `"resolve"`
(the `davinci-resolve` skill's `place.py` pattern). `b-roll`/`motion-graphic` beats with no real
footage go through your AI-video tool, then composite like any part. Then the **second pass** adjusts,
and **captions** (short-form) come after.

This skill does ONE thing: decide the graphics. It never renders.
