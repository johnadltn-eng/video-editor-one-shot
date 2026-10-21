---
name: edit-review
description: "The automated defect loop (step 5c, welded to Graphics): after graphics-build's first pass, the deterministic gate (workflows/graphics-qa.py, must be green) then fresh-eyes subagent review rounds (two dimensions, cap 3) converge the edit to ZERO objective defects before it ever reaches the creator. Defects only, never taste. Reviewers and skeptics run one tier BELOW the session's own model (Fable → Opus, Opus → Sonnet, Sonnet → Haiku, read the current model, never hardcode; `model` must be passed explicitly or agents inherit the session tier); the main session keeps creative judgment and adjudication. Stops on the first full round that finds nothing, then runs the final gate (real render + audio/framing verify) and reports. Triggers: polish loop, polish the edit, review the edit, dial it in, edit review, run the review rounds, converge the edit, one-shot finish."
---

# Edit Review: the defect loop (step 5c, the automated half of Graphics)

Runs after the `graphics-build` first-pass QA and BEFORE the creator sees anything. The builder
grading its own work is why first passes ship flaws; this skill puts fresh eyes on the draft in
review rounds until the objective defects dry up. It replaces waiting for the creator to call the
obvious fixes.

**This is a sub-step of Graphics (5), not a step of its own — it is never deferred (2026-08-31): "some of the mistakes Claude should be able to fix on its own before it ever becomes
my problem to review."** Graphics is not finished when the last comp is placed; it is finished
when this loop has run dry. The creator's own review is **pipeline step 7**, it comes after SFX,
and by the time you open the timeline every *objective* defect should already be gone — your pass
is taste, and only taste. A defect that reaches you are a defect this loop failed to catch.

**The contract: defects only, never taste.** The loop converges because defects are binary and
finite; taste never converges. A reviewer that suggests redesigns makes the edit oscillate, not
improve.

## Defect classes: the ONLY valid findings

Each is checkable against evidence (a frame, a timestamp, the plan):

1. **Face/subject covered** by a graphic on any sampled frame.
1b. **Band break (long-form):** an under-the-face overlay whose ink leaves the measured low band
   (`presets/youtube/default/default-overlay-style.md` § THE LOW BAND) — above the chin floor is
   the defect that matters; a DOWN arrow reaching the floor is legal. Objectively checkable, so
   it is a defect, not taste.
1c. **Dead prop glow (long-form):** an accent prop (progress fill, dot, chip, meter segment)
   whose glow renders ZERO pixels — almost always a `box-shadow` trapped inside an ancestor
   `overflow:hidden`. Check by measuring accent-coloured light OUTSIDE the prop's box, not by
   reading the CSS; the rule is `default-overlay-style.md` § THE PROP GLOW. Glowing type on a
   BASIC text animation, card headline, eyebrow or caption is the same defect
   inverted — but type is default-off, not banned: a graphic whose subject emits light (neon, an
   LED readout, a terminal accent) may glow its type, so flag only the basic-animation case.
   Both are measurable, so both are defects, not taste.
1d. **Off-registry entrance or exit (long-form):** an in/out that is not one of the
   `animations.md` presets, an exit that is not `riseOut` without a stated reason, a `slide`
   used for an element that never leaves the frame (that is a `rise`), a full-screen graphic
   holding blank frames before a NEAR-FULL-FRAME first element (that entrance must start on
   frame 0 — count blanks on the render with a heavy-downscale structural diff so grain does not
   read as content; the defect scales with the element's size, so a small first element after a
   short beat is fine, and a word-synced one is exempt since its fix is a clip trim), a
   retired move (1.45× punch, ±2° wiggle, stepped card in/out), a `flash` on a 12 fps graphic,
   or an entrance split that does not track ROLE — peers in a graphic share one entrance and the
   odd element out takes the contrast, so a different move on every element is the defect, not
   the fix. This is a deviation FROM the preset spec, which the motion-character
   ban explicitly still allows you to flag — you are not judging the spec, you are checking
   conformance to it.
1e. **Misaligned arrowhead (long-form):** an arrow whose head does not continue its shaft — the
   head's axis more than ~1° off the path's end tangent, or its base sitting clear of the
   stroke end. Always a hand-authored `<polygon points="…">` instead of the computed
   `arrow()` helper (`animations.md` § The arrow). Measurable on the render, so it is a
   defect. Look hardest at CURVED arrows: a straight one can be eyeballed correctly, which is
   why the bug ships.
1f. **Single-frame state change (long-form):** a visible state change that switches rather than
   animates — a background darkening, a blur arriving, a panel lighting up. Objectively checkable
   frame-to-frame on the render; the rule is `animations.md` § State changes ANIMATE. Registry
   entrances whose opacity CUTS by design, and hard punch-cuts, are exempt (authored cuts).
1g. **Missing film grain (long-form):** a full-screen GRAPHIC without the film-grain pass baked
   (`creative-moves.md` § Placement mechanics; the rendered-bed route ships grainless).
   Measurable as per-pixel noise variance on a flat area of the render. **Section title cards are
   exempt** — their locked builder does not bake grain.
1h. **Rhythm / variety break (long-form):** a bare stretch past the preset's bound with no visual
   event, or overall density outside `creative-moves.md` § THE DENSITY NUMBERS (measured
   per minute against that table), or the same FULL-SCREEN treatment / card template **twice in a
   row** (the ANTI-STALE LAW). **Text animations are exempt from the anti-stale half** — they are
   the connective tissue that carries the density floor and legitimately run back to back. Both are measured against the plan and the preset's stated
   laws, so they are objective — this is the cross-graphic class the per-graphic loop
   structurally cannot see. **These two are the ONE exception to "never more or fewer graphics"**
   (below): a rhythm break's only fix is adding the text animation the law already requires, so
   report it with the beat and the fill it needs, and the main session adjudicates.
2. **Safe-zone break.** Short-form: key content in the top 200 px or bottom 300 px bands.
   Long-form: copy at the very edge of the frame (~100 px breathing room), or the outro's
   right side + bottom blocked (end-screen cards land there).
3. **Copy defect**: typo, truncated/clipped text, or copy that differs from the storyboard cell.
4. **Timing**: a graphic's in/out off its word anchor (check against the canonical
   `outputs/<job>.transcript.json`), or a duration that doesn't match the cell.
4b. **Short hold on a READABLE graphic (long-form):** a graphic whose point is content the viewer
   reads or screenshots (prompt, command, code, config, quote) that holds the COMPLETE content
   for under ~2s — the reveal ate the slot (`creative-moves.md` 4d). Count it on the render:
   frames where the text is fully present, measuring neutral-bright text pixels only, since an
   accent cursor's blink otherwise reads as incomplete. Measurable, so it is a defect.
5. **Caption collision** (short-form): a graphic in the locked caption zone.
6. **Motion/render artifact**: pop at entrance/exit (missing hard-kill), frozen `<video>`,
   black/blank flash, alpha fringing, duplicated frames at a joint.
7. **Plan fidelity**: the built graphic deviates from its cell (template, side, region, copy)
   with no `⚠️` deviation note in the build report.

**Banned findings:** redesigns, "this could be better/cooler," different template or copy
phrasing, more or fewer graphics (except a 1h rhythm break, which the laws themselves require
filling), tier escalation, and motion-FEEL opinions. Motion character
(fps stepping, easing, hold lengths) is **preset-owned** (2026-08-27): the preset's motion spec IS
the look, tailored deliberately. A reviewer flags only a deviation FROM the preset spec, never the
spec itself. Findings in banned categories are discarded unadjudicated.

## 🔒 The gate comes first: `graphics-qa.py` green is a precondition (2026-09-02)

```bash
uv run workflows/graphics-qa.py projects/<job> --json projects/<job>/hf-graphics/qa-report.json
```

**Non-zero exit = no review round starts.** The retro on your-job measured it: of the 21
defects five full rounds fixed, 17 were deterministic (a rise-out landing a frame short, a missing
float, a rise-in under the band, an em dash in a label, a cut end 42 ms off) and the
composition/face/band reviewer found ZERO fixes in five rounds because its method was a pixel sweep,
not looking. The script sweeps every frame of every render in seconds: band and edge, exit
completeness, cut alignment, holes and overlaps, plan reconciliation, copy vs spec, the registry
constants, float coverage, the 12 fps form, zero-frame pins, arrowheads, grain, density.

**Everything the script owns is OFF-LIMITS to the reviewers.** A reviewer who believes an unchanged
graphic is wrong in a class the script checks reports it as a **MISSING ASSERTION** (what the script
should have caught, with the evidence), never as a per-graphic defect; the main session adds the
assertion. **Deviations are `hf-graphics/qa-waivers.json`, never prose:** a deliberate deviation is
a waiver keyed by graphic and check, with its reason, and the report shows it as `waived`. A
sentence in a build report is not evidence (round 2 dismissed a real 83 ms cut-end flash because the
report called it planned).

## The loop

Each **full round**:

1. **Evidence.** Per graphic, grab composite frames at in+2 frames, midpoint, and out−2 frames
   (entrance/exit pops live at the edges; the hold lives in the middle). Lane methods:
   chat-only = ffmpeg frames off the assembled render; Premiere = the bridge `frame` command
   (never front the app); Resolve = a real render (never `get_thumbnail_image`); CapCut = an
   export or window `shot`. Reuse frames across reviewers: grab once per round. Hand every
   reviewer the `qa-report.json` too, so they know what is already proven.
2. **Review fan-out: TWO dimensions, not four (2026-09-02).** Two subagents one tier below the
   session, one per dimension (not per graphic):
   - **Copy, plan fidelity and depiction**, the irreducible LLM dimension, prompted exactly as
     before. It alone found the invisible icon on its own plate, the caps on a number-completing
     fragment, the tie hanging below the body, the missing "=" between two totals.
   - **Motion and rhythm adjudication**: receives the QA report and reviews only intent,
     cross-graphic rhythm, density feel and role-tracked entrances; it does NOT re-measure
     anything the report already measured.
   The composition/face/band and timing dimensions are retired from the fan-out: face coverage,
   the band sweep and word-anchor timing are the script's. Each prompt is self-contained: the
   defect-class list, the plan JSON, the frame paths, the transcript slice, the QA report. Never
   the whole CLAUDE.md, never this repo's history. Findings must carry evidence: graphic id, frame
   path or timestamp, expected vs actual.
3. **Verify.** Each finding gets ONE skeptic (same tier) prompted to refute it from the same
   evidence. The main session adjudicates disputes. Unverified findings are dropped: a
   hallucinated defect that reaches the fix stage burns a render for nothing.
4. **Fix.** The main session fixes verified defects only, part-by-part per the `graphics-build`
   incremental mechanics: edit the one comp, re-render the one part, re-place
   (`place-graphics.py --apply` swaps the versioned file). Never a full re-render for one fix.
   **Fix the root cause everywhere it appears, not the instance reported** (round 2 named
   `g4.html:58` and round 3 re-raised the same thing on its neighbour).
5. **Targeted re-check: MANDATORY, never skipped (see the stop condition).** Re-run
   `graphics-qa.py --ids <changed>` on the changed graphics, then ONE agent re-reviews only their
   windows before the next full round, so a bad fix cannot survive into the round that ends the
   loop. Reviewers get a changed-since list and must not re-measure unchanged comps.

**Stop condition: the script green AND one full round with zero verified findings (2026-09-01, gate added 2026-09-02).** A clean round costs two reviewers plus an evidence grab, and
a second identical fan-out finding what the first missed is a low-probability event, the
reviewers are stochastic, not sharper on a re-run.

**What that shifts, and the one thing to hold onto:** the fixes from the last defective round get
**one** full review, so **step 5 above is load-bearing rather than a nicety.** The targeted
re-check is what still catches a fix that broke its neighbour, and skipping it turns the stop
condition into shipping a repair nobody looked at twice. Run it after every fix batch, without
exception.

**Expected shape: 2 full rounds. Hard cap: 3.** If a third round still finds something, the next
move is a new assertion in `graphics-qa.py`, not a fourth round; stop and report what is open
(something structural is wrong; a human call is needed). Projected on the reference job,
this ships the identical edit for roughly a fifth of the tokens and an hour less wall clock.

## Final gate: after the loop dries

- Produce the real deliverable: chat-only = final assemble; Resolve/CapCut = the app's export
  (their skills' locked settings). **Premiere lane stops at placed + verified**: the creator
  renders and finishes there (AME stays banned).
- `audio-qa.py` on the final file where the lane renders one; `face-frame.py --verify` on
  explainer jobs (must print ✓ PASS).
- **Report:** rounds run, found→fixed per round, per-`⚠️` deviations that stand, and the final
  render linked with the full repo-root path. Then hand off for the creator's watch.

## Token efficiency: the rules

- **Every subagent runs one tier below the session** (Fable → Opus, `model: opus`; Opus →
  Sonnet). The main session keeps the creative work: adjudication, fixes, final judgment. Never fan
  out at the session's own tier, `agent()` inherits it unless `model` is passed.
- **The script runs first and is free.** A full round on your-job cost about 1M subagent
  tokens; five of them found 21 defects, 17 of which `graphics-qa.py` now catches in seconds.
- Reviewers are per-DIMENSION (2 per round), not per-graphic. Skeptics spawn only per finding,
  so a clean round costs 2 agents and nothing more.
- Grab evidence once per round; don't re-send unchanged frames. Targeted re-checks before full
  rounds keep round count down.
- Lots of graphics (a long-form job, ~10+): orchestrate the fan-out as one Workflow
  (review dimensions → per-finding skeptics as pipeline stages). A handful: plain Agent calls.

## Handoff: where this skill ends

When the loop dries, **step 5 (Graphics) is done and the job moves to step 6 (SFX)** — not
straight to the creator. That order is deliberate: SFX are aligned to graphic beats, so any
graphic this loop retimes would silently orphan its sound if the sound were already laid.
(The handoff is step 6: `uv run workflows/sfx-plan.py projects/<job>` then the lane's placer, or hand-placing from the cut sheet on a lane with none. Never skip it in silence.)

The moment the creator starts calling live adjustments at **step 7**, this loop is over. Those
tweak rounds follow the second-pass rule: edit, render, show, no self-QA frame grabs (the fixes
get called live from the review).

## Not this skill

Reviewing the rough cut — the `rough-cut` skill carries its OWN fresh-eyes second pass
(Step 3.8: one script-flow + one mechanical reviewer, both one tier below the session's model,
run before the cut ships; added 2026-08-28) — this loop starts after graphics · deciding or building graphics (5a/5b) ·
captions, music, export mechanics · anything in the banned-findings list.
