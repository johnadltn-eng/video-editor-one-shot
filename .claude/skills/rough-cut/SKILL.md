---
name: rough-cut
description: "Rough-cuts videos from raw clips, every format (short-form reels and long-form YouTube alike, the universal step 2). Transcribes with WhisperX (large-v3 + wav2vec2 word-level alignment), kills filler + dead air, keeps only the essential lines, stitches with FFmpeg. No captions, no B-roll — just a tight rough cut ready for final polish. Triggers: rough cut, cut this video, trim this, chop this up, rough-cut, make a rough cut, tighten this cut. (Whole-line phrasings — 'edit this video', 'do the whole edit', 'edit the latest project' — belong to `edit-video`, the orchestrator: this skill is step 2 of that line.)"
---

# Rough Cut — Transcript-Driven Edits

Turns raw talking-head clips into a tight rough cut. You transcribe, you decide the cuts, FFmpeg stitches. The goal: **shortest possible reel that still delivers the value.** Respect the viewer's time.

## How to Trigger
- **"edit the latest project"** → finds the newest job folder, edits it
- **"rough cut [job name]"** → edits a specific job folder
- **"cut this reel"** with a path → edits that folder

---

## Folder Contract

The skill operates out of `/video-editor/` at the repo root.

```
video-editor/
├── projects/
│   └── <job-name>/              ← one folder per reel
│       ├── raw/                 ← raw clips (any name, any count)
│       │   ├── clip-01.mov
│       │   └── clip-02.mov
│       ├── audio/               ← OPTIONAL — music beds / audio assets
│       ├── assets/              ← OPTIONAL — refs, screen recordings, B-roll sources
│       ├── thumbnails/          ← OPTIONAL — thumbnail source images/working files
│       ├── outputs/             ← rendered deliverables for this job
│       │   └── <job-name>.mp4
│       └── intent.md            ← OPTIONAL — what the reel is about
```

**Naming a new job:** name the folder after the **video's content** — a short, made-up kebab-case title that describes what the reel is about (e.g. `my-first-video`, `cold-dm-teardown`). NEVER name it after the camera/source file (`C1840.MP4` → ~~`c1840-roughcut`~~) or a date. If the content isn't obvious yet, skim the transcript first, then name it. No stage suffixes (`-roughcut`, `-final`) — one folder is the whole content piece across all stages.

The canonical transcript (`words.json`) and cut sheet (`cuts.json`) persist durably to `projects/<job-name>/transcript/` — read those when iterating. Encoded segments and other scratch live in `/tmp/video-editor/<job-name>/`, which macOS clears, so never depend on anything living solely in `/tmp`.

**Intent is derived, never asked.** If `intent.md` exists, read it. Otherwise work the hook + takeaway out from the footage itself: read the FULL transcript first, identify the hook (the strongest curiosity/tension line, often filmed mid-take and re-orderable to the front) and the takeaway (the one thing the viewer should leave with), then cut to serve those. No usable dialogue (a visual-only edit)? Sample a few frames per clip (`ffmpeg -ss <t> -i <clip> -frames:v 1 <out.png>`) and infer the subject + arc from what's on screen; harder, but a best-effort read beats a blocking question. State the hook + takeaway you inferred in one line of the report; the creator corrects you there if you read it wrong.

---

## The Edit Philosophy (non-negotiable)

**Short and snappy, max value per second, respect the viewer.**

Every cut decision runs through this filter:
1. **Does this line deliver value?** If not, kill it.
2. **Is this the tightest version?** If there's a shorter take, use it.
3. **Would a viewer skip past this?** If yes, it's dead.

**RELEVANT IS NOT NECESSARY — this is the #1 filter (2026-08-28, after a first cut
ran 3:32 that should have been 2:00):** "just because it's relevant doesn't mean that it's
necessary... stuff that's like okay, cool, good to know, instead of need to know right now,
is fluff." A line survives only if the viewer NEEDS it right now — for understanding or for
the flow of the script. Good-to-know context, how-I'll-do-it teases, second statements of a
point already made, and warm-up framing are all relevant and all dead. On an emphasis-heavy
multi-take talking head, expect to kill 60-75% of the raw; a first cut keeping more than
half the footage is a red flag, not a draft. An intro especially is pure momentum
(claim → problem → rules → stakes → go) — every beat that doesn't advance it goes.

**Format is auto-detected from the raw footage, never asked.** Probe every clip
(`ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 <clip>`):

- **Vertical** (height > width, e.g. 1080×1920) → **short-form**.
- **Horizontal** (width > height) → **long-form YouTube**.
- **Mixed folder** → the clips carrying the substance decide: the main dialogue/talking takes vote, screen recordings and b-roll inserts don't. Vertical main takes → short-form; horizontal main takes → long-form.

State the detected format in the report (one word is enough for the creator to override). The explainer-vs-TikTok/raw call (short-form finishing) is likewise inferred from content at the Graphics step (teaching/system walkthroughs cut like explainers, casual talk-to-camera stays raw) and stated, not asked.

**Target length depends on that format:**
- **Short-form** (9:16 Reels/TikTok/Shorts) → aim **1–2 minutes.** The "shortest version that still delivers" filter still governs — 1–2 min is the target *after* ruthless cutting, not permission to ramble. If the value fits in 40s, ship 40s.
- **Long-form** (16:9 YouTube) → **no length cap** — but no cap is not license: the necessity filter above still governs, and on emphasis-heavy raw 60-75% should still die. Cut for retention and structure, not to hit a number. Kill dead air and filler, keep the substance.

---

## Auto-Kill Rules (always apply)

When building `cuts.json`, automatically remove:

| Kill | Why |
|------|-----|
| Filler words: *um, uh, like, you know, so yeah, basically* (when vestigial) | Dead weight |
| Stutters + false starts: *"I- I was gonna-"* | Breaks flow |
| Restarted takes | Keep the **last** take, kill the rest — you always want the latest take of a repeated line (warmest delivery). Don't compare takes; default to the last one. |
| Emphasis echoes: the same claim re-stated for punch (*"one prompt, one shot, one go... it was literally one prompt... I didn't have to prompt back and forth"*) | Keep the STRONGEST single statement of each claim; every echo after it is fluff. A hook montage of restatements collapses to one claim + at most one punch ("One shot."). Half the 90 s of bloat on your-job's first cut was kept echoes (2026-08-28). |
| Silences > 0.4s | Dead air |
| Tangents + asides that don't serve the hook/takeaway | Respect viewer time |
| Throat-clears, "okay let me start over", etc. | Production noise |
| Orphan low-prob word before a kept take | A lone low-confidence word (prob ≲ 0.3) with a ≥1s gap immediately before a kept take is a false start WhisperX half-missed (it transcribed only a fragment of the abandoned attempt and hid the repetition). Kill the whole fragment and start the segment at the real take; never keep the orphan as its own segment. The refiner recovers any words the aligner dropped at the retake's onset. |
| Preamble before the hook lands | Every reel opens ON the hook |
| Trailing verbal tics after a landed point: *"...5X more usage, okay?"* → cut at "usage" | The point already landed; the tic is a ~0.5s tax. Mid-sentence tics are rhythm — keep those. |
| Meta-signposts about the video's own structure: *"so now what I'm going to do is cover..."*, *"you can skip to the next section"*, and how-I'll-do-it teases: *"my plan is to build a preset, we'll go into it"* | The content announces itself. All three flavors die — the preview, the skip-ahead courtesy, AND the method tease (2026-08-28: "it's just fluff... obviously I'm gonna explain how I do it later in the video"). Relevant-but-not-needed-NOW is still fluff; in an intro especially, keep the momentum: claim → problem → rules → stakes → go. |
| Self-referential flexes: *"personally, I'm on the $200 a month plan"* | Status talk, not information. |

**Preserve the creator's cadence though.** Don't surgical-kill every "like" — some are rhythm, some are filler. Taste call.

**The keep/kill line (learned from your 2026-07-29 hand pass): persuasion and personality are CONTENT — meta-narration is not.** Objection-handling ("can I do this on the free plan?"), the pitch, the value stretch, the walk-back for budget viewers, section preambles that set context — all of that stays, even in an "essentials only" cut. What dies is talk *about the video* (signposts), talk *about the creator's status* (flexes), and tics. When asked to cut harder, tighten inside lines (tics, restarts, grafts) before deleting persuasion beats — an "absolutely essential" filter that strips the selling is the wrong cut.

---

## The Pipeline

### Step 1 — Transcribe

Find the job folder. Run:

```bash
bash .claude/skills/rough-cut/scripts/transcribe.sh <job_dir>
```

This runs WhisperX (large-v3 ASR + wav2vec2 forced alignment) with true word-level timestamps and writes `/tmp/video-editor/<job-name>/words.json`. Word timestamps are tighter than plain faster-whisper, so cuts land more precisely.

**Hardware is auto-detected.** An NVIDIA GPU (Windows/Linux) runs the model on CUDA float16, several times faster than CPU, behind a full runtime ladder (cuda float16 → cuda int8_float16 for ~4 GB cards → cpu int8) so a broken CUDA stack (old driver, missing cuDNN, OOM) degrades with a ⚠ warning instead of blocking the edit. Apple Silicon stays CPU int8 (locked: GPU torch is still flaky there, and CPU is never silently wrong). `WHISPERX_DEVICE=cpu|cuda` overrides the pick. A venv built before GPU support prints a one-line rebuild hint (`rm -rf` the venv + re-run) rather than surprise-downloading the ~3 GB CUDA stack.

**This is the ONE transcription for the entire pipeline — rough cut AND finishing captions.** The transcript is persisted canonically to `projects/<job>/transcript/words.json` and **reused forever**: re-running `transcribe.sh` skips WhisperX and reuses the canonical copy (pass `--force` to re-transcribe). Nothing downstream transcribes this footage again — the locked caption presets (`presets/instagram/explainer/build.py`, `presets/tiktok/raw/build.py`) and `graphics-plan` consume the derived `outputs/<job>.transcript.json` instead (see Step 3 + Handoff). WhisperX large-v3 is the most accurate engine we have, so it's the single source of truth.

**Add `--diarize`** to label each word with a speaker (multi-person clips). Requires `HUGGINGFACE_TOKEN` in env and accepting the pyannote/speaker-diarization-3.1 model on HF.

**Run in background** if expected >2min (CPU numbers; CUDA lands several times faster):
- ~30s of clip = ~10-20s wall time (first run is slower — alignment model downloads)
- ~5min of clip = ~2min wall time

For total clip length >3min, use `run_in_background: true` and Monitor.

### Step 2 — Read the transcript + decide cuts

Read `/tmp/video-editor/<job-name>/words.json`. Each clip has a `words` array of `{w, start, end, prob}` (plus `speaker` when `--diarize` was used).

Apply the auto-kill rules and the edit philosophy. Output `/tmp/video-editor/<job-name>/cuts.json` in this shape:

```json
{
  "segments": [
    { "clip": "clip-02.mov", "start": 1.24, "end": 4.60, "transcript": "Are you still paying a VA three grand a month" },
    { "clip": "clip-02.mov", "start": 4.95, "end": 8.10, "transcript": "to do shit Claude Code can do for free in five minutes" },
    { "clip": "clip-01.mov", "start": 12.20, "end": 18.80, "transcript": "..." }
  ]
}
```

**Timestamp rules:**
- Trust WhisperX word-level timestamps for WHICH words to keep. Their edges are soft though: word STARTS run ~50-100 ms late vs the real acoustic attack, word ENDS run early vs the real decay — which is why exact boundaries are dialed by the splice-time refiner (below), not by you.
- **A low-probability boundary tail means the TIMESTAMP is fiction, not just soft (your-job, 2026-08-28).** A cluster of prob ≲ 0.3 words at a segment's edge ("of p0.25 the p0.38 way p0.00 there. p0.58" crammed into 0.46s) is the aligner giving up — the real speech ran ~750 ms past the claimed word end and any decay search capped relative to that end lands MID-WORD, then falls through to a "continuous speech" cut that chops the line ("...90% of the way th—"). When a boundary word or its 1-2 neighbors carry prob < 0.3: the real acoustic edge must be measured on the raw envelope with a WIDE window (up to the next raw word, not word.end + 300 ms) with an actual sustained drop required before cutting. Related check: a mid-speech "graft" cut is only legitimate when the adjacent word is KEPT — a graft-style cut against a KILLED region means the measurement failed, never that the cut is fine. **Both rules are enforced by `polish-boundaries.py` (Step 3.4) — run it every job; its ⚠ lines are these exact cases surfacing.**
- **Merged repeats: an immediately repeated word ("However... However,") can collapse into ONE transcript entry spanning every utterance** — the text shows a single word, so a cut keeping it keeps the stutter. `transcribe.sh` flags long-span words (>1.0s) at transcription time — check the audio before trusting them. The refiner auto-fixes boundary cases (segment starts on one → snapped to the LAST utterance, prefer-last-take; ends on one → trimmed to the first) and warns on mid-segment ones, which need you to split the segment. **On screen-recording footage (OBS) the auto-fix fails SILENTLY:** room tone/fan noise keeps the inter-utterance pause above the burst scan's drop threshold, so it reports "no-gap" and misses real repeats (measured 2026-07-31: 1 caught of 4 real). Treat every ⚠ long-span word on a segment boundary as unverified there: measure the raw with a 10 ms RMS envelope, then pin the boundary in cuts.json as explicit start/end + `"no_refine": true` (without the flag the refiner searches from the bogus word end and undoes your hand-set boundary). Mid-segment repeat: split the range at that word. Interior ⚠ words and quiet runs under ~0.3s are fine.
- Start on the first word you want, usually `word.start - 0.03` to `0.08`.
- End after the last word you want, usually `word.end + 0.04` to `0.10`.
- **Segments must never overlap in the source — a continuous split shares ONE boundary time.** When you split a take with nothing removed between the two halves (a long section carved into separate timeline clips, a sentence break), those pads point at each other: `word.end + 0.08` on the way out and `next_word.start - 0.04` on the way in put the SAME source frames in both segments, and they play twice as a 1-15 frame stutter. Write `"end": T` on one and `"start": T` on the other, one shared value in the inter-word gap. Padding is for a real cut, where material was removed and the two pads open outward into different silences. `refine-cuts.py` detects continuous splits from transcript adjacency and repairs overlaps, and `splice.sh` hard-aborts on any that survive — but the abort names YOUR segment numbers, so author it right.
- Don't cut mid-word. If a transition feels clipped, adjust `cuts.json` manually and rerender.
- Segments CAN cross clips in any order — that's the whole point.
- **The graft — splice restarts mid-sentence, don't cut at sentence boundaries.** When the speaker restarts a thought ("...we need Claude Code. Okay, we need Claude Code for it to..."), end segment A *through* the repeated phrase in take 1 and start segment B in take 2 *right after* the restated words (at "for it to..."). One continuous sentence, zero duplication. Keeping both restatements (or nuking one whole sentence) is the amateur cut; the graft is what a human editor does. Prefer-last-take governs *full retakes*; the graft governs *mid-thought restarts*.
- **Orphaned connectives — when you kill a line, kill the words that answered it (you caught this on your-job, 2026-08-28).** Rebuttal/contrast frames ("But the reality is...", "That's why...", "Which is exactly...", "So instead...") exist to respond to the PREVIOUS sentence; cutting the claim while keeping its counter leaves a "but" that contradicts whatever now sits before it ("They all lack autonomy. But the reality is Claude can edit..."). After authoring, re-read the cut sheet as one continuous script and check every segment's FIRST few words: does the connective still refer to something that survived? If not, start the segment after the connective (the graft moves in, e.g. straight to "Claude can edit the entire video..."). Same check on deictics ("that video", "this one") — their antecedent must still exist in the cut. **And the reverse: a beat that only makes sense WITH its framing clause dies whole when the clause dies.** Cutting "In order to achieve this," off "I'm going to have to do a little vibe coding" left a line that contradicted the rules stated seconds earlier — partial salvage of a marginal beat produces nonsense; if the frame has to go, ask whether the beat survives without it, and usually kill both.
- **NEVER author extra tail for emphasis — every tail is uniform (RETIRED 2026-08-31, you).** There used to be an `"air": <sec>` field that extended a segment's out-point to give a punchline or a reveal room to breathe. It is gone: the rule only ever produced pauses you had to fix, and both airs on your-job's timeline read as the speaker hanging ("weird extra space") rather than as a beat. `polish-boundaries.py` no longer reads the field, so a stray `"air"` in an old `cuts.json` is inert — never add one, and never hand-extend an out-point for dramatic effect instead. Every boundary is the measured decay + 70 ms, on every segment, with no exceptions. If a beat genuinely needs room, that is your call on the timeline, not the rough cut's.
- These pads are a starting point, not the final cut: `splice.sh` runs `refine-cuts.py` first, which measures each boundary word's actual acoustic onset/offset on the raw audio and nudges the cut just outside it (in = onset − 40 ms, out = offset + 50 ms), clamped so it never crosses an adjacent word, leaves the local gap, or lands further out than a real acoustic edge can be (250 ms before its word, 300 ms after). Continuous mid-flow splits are detected from transcript adjacency and given a single shared boundary instead of two pads. Joints are then resolved PAIRWISE — the two sides of one cut are measured independently and can otherwise cross, duplicating frames. Watch its `[refine]` report — `cut was N ms INTO "word"` lines are the clipped attacks it just saved. `REFINE=0` disables the pass; `"no_refine": true` on a segment pins that segment's authored boundaries (joint resolution honors the pin too: an overlap against a pinned side moves the UNPINNED side only).
- **Refinement is NOT idempotent — repair a shipped EDL with `refine-cuts.py --repair-only`, never a second full pass.** The refiner measures from the authored cut, so re-running it on an already-refined EDL re-measures from the moved boundaries and drifts tails further out (+0.4s observed on a section with nothing wrong). `--repair-only` runs ONLY the pairwise joint resolution with zero re-measurement, so only overlapping joints move.

Include the `transcript` field for each segment so the creator can read the cut sheet and sanity-check it without watching.

### Step 3 — Splice

**The editing-app finish IS the default (2026-08-28): a bare "rough cut" with no lane named means EDL-only mode + automatic Premiere handoff. NEVER render:**

```bash
RENDER=0 bash .claude/skills/rough-cut/scripts/splice.sh <job_dir>
```

~8 seconds: boundary refine + frame-snap + persisted EDL + corrected canonical transcript, no ffmpeg encode. The timeline replay (`premiere-pro` skill) consumes only those — nothing on an editing-app path ever reads the flat MP4. Go straight from this to the timeline (for clients, their app: `capcut` / `davinci-resolve`), then run the **audio polish** (pipeline step 3 — the house chain as clip effects, see the `premiere-pro` skill). The full render below is **only** for the chat-only/HyperFrames lane — which is never inferred: it runs only when a client with no editing app has explicitly said to do it in chat.

```bash
bash .claude/skills/rough-cut/scripts/splice.sh <job_dir>
```

First dials every cut boundary against the raw audio (`refine-cuts.py` — see Timestamp rules), then writes `projects/<job-name>/outputs/<job-name>.mp4` from the refined cuts in a **single FFmpeg filtergraph** — one `trim`/`atrim` per kept segment → `concat` → static gain → limiter, encoded once. Audio rides through the cut **lossless (PCM in-graph)** and is polished **once** on the assembled track (a measured amplify (workflows/voice-gain.py, kept speech → −17 LUFS pre-limiter) → −6 dBFS hard limiter, AAC encoded once at 256k); it is **never** encoded per-segment (that caused boundary click-pops). Video and audio are trimmed from the same in/out and concatenated together, so A/V stay locked by construction.

It also writes **`outputs/<job-name>.transcript.json`** — the cut-aligned caption transcript, derived by remapping the kept words through `cuts.json` (via `export-transcript.py`). Same large-v3 quality, timestamps rebased to the edited timeline, **zero re-transcription.** This is what finishing/captions/graphics all consume.

**Spelling/brand fixes happen HERE, once.** `export-transcript.py` applies [`transcript-corrections.json`](../../../transcript-corrections.json) to the canonical transcript as it writes it — `auto` entries (non-word mishears + brand/name casing, e.g. a mis-heard product or person's name) are replaced silently; `flag` entries (real words that might be mishears, e.g. `cloud` for a mis-heard product name) are printed to eyeball. Because this is the one source of truth every downstream step reads, the fix propagates to graphics-plan, both caption formats, and long-form — not just burned-in captions. The raw `transcript/words.json` is left untouched. Per-video one-offs go in `projects/<job>/corrections.local.json` (same `{auto,flag}` shape, merged on top). Watch the splice log for `auto-fixed:` and `⚠ REVIEW` lines; add new mishears to the dictionary so they're fixed everywhere forever.

**Always run in background** — renders take 15-45s for 60s output.

### Step 3.4 — Polish the boundaries (ALWAYS, every job — added 2026-08-28)

```bash
uv run .claude/skills/rough-cut/scripts/polish-boundaries.py <job_dir>
bash .claude/skills/rough-cut/scripts/splice.sh <job_dir>     # RENDER=0 on app-finish jobs
```

The refiner leaves two classes of boundary unmeasured (dead-air kills between adjacent
transcript words get classified "continuous split" and skipped; and its absolute
thresholds clip soft decays / count breaths as tails). This
script re-derives EVERY boundary with the peak-relative measure (run the FIRST splice with
`RENDER=0` on every lane, chat-only included — the real render belongs AFTER this step, or
the first encode is always thrown away) (local floor, threshold
`max(floor+10dB, peak−28dB)`, decay capped at word.end+300ms, uniform out = decay+70ms /
in = onset−40ms, the same tail on every segment), widens the search on low-probability boundary words (their
timestamps are fiction), and pins everything. Segments that arrive already hand-pinned (`no_refine`) are left
untouched, which also makes the step idempotent. **Heed its ⚠ lines** — they are clipped
words, merged repeats, and possible flubbed takes; each one gets verified (slice-ASR the
span — see Step 3.8 — or fix the boundary by hand) before the cut ships. Then re-run
splice.sh to consume the pinned EDL. you heard every one of these defect classes on the
first one-shot test; this step exists so you never do again.

### Step 3.5 — Dynamic transcription QA (auto, every run)

The static dictionary only fixes mishears it already knows. This step catches the **new** ones — names/brands WhisperX mangled that aren't in the dictionary yet — and auto-applies the safe fixes. **Run it every job, right after splice:**

```bash
uv run .claude/skills/rough-cut/scripts/scan-transcript.py <job_dir>
```

(On Windows run it as `python`, not `python3` — Windows has no `python3` name, only a fake Store stub. No system wordlist exists there either, so the scan reports nothing and you skip this step.)

It compares every transcript word against a 235k-word English wordlist (+ inflection stripping) and the dictionary, and prints only the **suspects** — words that are neither ordinary English nor already-handled terms. On a clean transcript this is empty; otherwise you get a short list with context, e.g. `higsfield  ×1  …built it on higsfield and pushed to…`.

**Judge each suspect in context, then act:**
- **Real mistranscription, single token, recurring name/brand** (e.g. `higsfield → Higgsfield`) → add to [`transcript-corrections.json`](../../../transcript-corrections.json) `auto` so it's fixed everywhere forever.
- **Real mistranscription, one-off for this video** → add to `projects/<job>/corrections.local.json`.
- **Multi-token mishear** (e.g. "higs field" → "Higgsfield", two words → one) → do **not** auto-apply (it would change word count and break per-word timestamps). Flag it in the report for you instead.
- **Already-correct proper noun** (a real name, your term like LARP) → skip.

Then re-apply (instant, timings + cuts untouched):

```bash
bash .claude/skills/rough-cut/scripts/reapply-corrections.sh <job_dir>
```

**Hard rule:** only ever auto-apply **single-token, whole-word** swaps — the dictionary mechanism enforces this, which is exactly why it can never shift a timestamp or alter a cut. When unsure whether a word is a mishear or correct, flag it; don't guess.

### Step 3.8 — Fresh-eyes second pass (ALWAYS, every job — 2026-08-28)

The author grading their own cut is why first cuts ship flaws. Before reporting (and on
app-finish jobs, before the timeline replay), fan out **two subagents one tier below this session's model** (pass `model` explicitly — agents inherit the session tier otherwise) — one pass,
not a convergence loop (that's `edit-review`'s graphics territory):

1. **Script-flow reviewer.** Input: the cut sheet's transcript column assembled as ONE
   continuous prose script (+ this skill's taste rules, self-contained in the prompt).
   Finds only: orphaned connectives (a "But/So/That's why" answering a killed line),
   deictics with dead antecedents, emphasis echoes kept more than once, fluff
   (good-to-know vs need-to-know-NOW), a beat stripped of its framing clause, meta-
   signposts/method teases, and momentum breaks (a plan tease wedged between a list and
   its button). Findings must quote the exact lines.
2. **Mechanical reviewer.** Input: the polish-boundaries ⚠ list, the transcript, and the
   words.json probabilities. Verifies every ⚠ by slice re-ASR: extract the boundary's
   raw-audio span (±4s) with ffmpeg and transcribe it independently (`uvx --from
   mlx-whisper mlx_whisper --model mlx-community/whisper-large-v3-turbo`), then diff what
   was actually said against what the cut keeps — this catches fictional tails, missing
   sentence completions, and flubbed takes (an alignment-collapse cluster + an
   untranscribed speech burst nearby = a bad take to kill, not a boundary to fix).

Main session adjudicates: mechanical defects get fixed (boundary moved, take killed,
graft moved), flow findings are judgment calls decided against the taste rules, and only
the CHANGED segments get re-checked. Then report. The one-shot test needed five of
your review rounds to reach "80-90% there" — this pass is those rounds, run before you
ever watches.

### Step 4 — Report back

Show the creator:
- The detected format + the hook/takeaway you inferred (one line; this is where they correct a wrong read)
- Final duration vs raw total (e.g., "3:47 → 0:48, 79% cut")
- The cut sheet (clip + timestamp + line) to review
- Path to the MP4

### Step 5 — Learn from the hand pass (Premiere-finish jobs)

When the creator hand-adjusts the cut on the Premiere timeline afterward, **diff their edit against the EDL and fold the delta back into taste** — their trims ARE the ground truth this skill is trying to approximate:

```bash
node lanes/premiere/premiere-bridge.mjs diff-edl projects/<job>/transcript/cuts.json [more cuts.json...]
```

It matches every timeline clip to its EDL segment by source overlap and prints deletions, boundary trims/extensions (with the words at each moved boundary), grafts (an extension on one side of a joint paired with a head-trim on the other), and any new material. Read the deltas, then: recurring pattern → new Auto-Kill row or timestamp rule here; one-off → note in the job's notes. The 2026-07-29 rules above (tics, signposts, flexes, grafts) came from exactly this diff. After a hand pass the **timeline is the source of truth** — never re-replay the EDL over it.

---

## Output Format

After the cut lands, report like this:

```
✂️ ROUGH CUT DONE

📊 3:47 → 0:48 (79% cut)
📁 projects/<job-name>/outputs/<job-name>.mp4

CUT SHEET:
1. [clip-02 @ 1.24-4.60] "Are you still paying a VA three grand a month"
2. [clip-02 @ 4.95-8.10] "to do shit Claude Code can do for free"
...
```

Keep it tight. If a segment feels weak, flag it: **"⚠️ segment 3 is borderline — consider killing."**

---

## Gotchas

- **`-c copy` alone doesn't work on arbitrary cut points** — causes A/V desync. `splice.sh` re-encodes each segment with hardware accel, which is still fast (~15s for a 60s reel). Don't "optimize" to pure stream copy.
- **Don't auto-snap cuts to silence.** WhisperX word alignment is the unlock. Automatic silencedetect snapping can move intentionally chosen boundaries into filler words or awkward pauses. (The splice-time boundary refiner and `polish-boundaries.py` are NOT this: they keep the chosen word fixed and only dial the cut against that word's measured acoustic edge, clamped inside the local gap — they can never relocate a cut to a different pause or word.)
- **Whisper can mishear.** Always cross-check the transcript before killing a line — sometimes "Claude" becomes "cloud" or "Cloud" and the line looks wrong when it's fine.
- **`splice.sh` reads `/tmp/video-editor/<job>/cuts.json`, NOT `transcript/cuts.json`**, and then overwrites the job copy with what it spliced. Re-cutting a job that was already cut (a re-recorded take) therefore replays the STALE `/tmp` EDL and silently clobbers the new cut sheet. Write the new cuts to the `/tmp` path (delete `cuts.refined.json` + `cuts.snapped.json` alongside it) before running.
- **Transcribe.sh auto-skips** when `projects/<job-name>/transcript/words.json` exists — it's the canonical transcript, reused forever. Use `--force` only if the raw footage actually changed. Transcribing is the slowest step; this guarantees it runs once per video.
- **Multi-section jobs: each newly filmed section runs as its own sub-job under `projects/<job>/sections/<name>/`** (raw symlinked from the parent's `raw/`, its own `transcript/` + `outputs/`). This exists precisely because of the auto-skip above: point a new section's transcribe at the main job dir and it silently reuses the WRONG `words.json`/`cuts.json`. (Same nesting the clipper uses for `clips/`.)
- **Clip order in `cuts.json` = final order in the reel.** You're writing the script sequence.
- **Questions are a last resort, not a step.** Intent (hook/takeaway) comes from the transcript (or sampled frames on a visual-only edit) and format comes from the clips' aspect ratios (see the top of this file). Never ask for those; infer, state your read in the report, and let the creator correct it. Ask only when something is genuinely undecidable from the footage, and then one question, one sentence.

---

## Handoff

The cut lands on the finish surface (Premiere by default — the replay in the `premiere-pro` skill; the flat render only on an explicit chat-only job), then the pipeline continues (the repo-root `CLAUDE.md` has the full eight-step flow): **audio polish** (step 3, immediately after the replay — house chain as clip effects on every A1 clip, `premiere-pro` skill; the chat-only render already has it baked by splice) → **graphics** (`graphics-plan` → `graphics-build`) → **captions** (short-form only) → optional **background music** → **export** (`finalize.sh`). **Finishing differs by format** — each preset's own style doc carries its geometry and safe zones:
- **Short-form**: 9:16 reframe + top-half graphics inside the platform safe zones, then **burn-in captions from the locked presets** — explainer → [`presets/instagram/explainer/captions-style.md`](../../../presets/instagram/explainer/captions-style.md), TikTok/raw → [`presets/tiktok/raw/tiktok-raw-style.md`](../../../presets/tiktok/raw/tiktok-raw-style.md).
- **Long-form**: stays 16:9, full graphics/hook treatment, **no captions** (YouTube CC only) — [`presets/youtube/default/`](../../../presets/youtube/default/README.md).

Reframe, graphics, and inserts run through the vendored HyperFrames toolkit (`general-video`/`hyperframes`). Captions are built by the **locked PIL preset builders** (`presets/instagram/explainer/build.py`, `presets/tiktok/raw/build.py`), not by re-transcribing — they read the canonical `outputs/<job>.transcript.json` this skill already produced (transcribe-once: same large-v3 words, timestamps rebased to the cut timeline). After export, posting/distribution happens **outside this repo**.

This skill does ONE thing: cut the reel down to the essential lines (audio is normalized as part of the cut). It does not do captions, B-roll, zoom effects, or vertical reframing.
