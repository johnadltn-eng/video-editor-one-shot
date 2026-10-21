# Road to 20K — the Day N reel preset

The locked look and finish of John's "Road to 20K" Day N reels, as approved on **Day 6 and Day 7** (Oct 2026).
`/20k` (`.claude/skills/20k/SKILL.md`) runs a new day with it; this file is the spec, the numbers live here.

## Format
- Instagram Reel / TikTok / Shorts, **9:16 1080x1920**, Premiere lane, sequence at **exact 30 fps** (ticks 8467200000).
- iPhone clips carry −90 rotation: respect it (upright). Pin every clip's frame rate to its nominal rate
  (29.998→30, 119.95→120, 23.998→24): `tools/setup_premiere.py` does it.
- Length: whatever the brief says (Day 6 ≈ 34 s, Day 7 ≈ 49 s); no padding, no filler.

## Story + cut
- Raw vlog, jump cuts, picture **in sync with its own audio**. B-roll only under VO where John isn't talking to
  camera (or is too far/small to lip-read). To change the picture on a phrase without b-roll: the in-sync clip with
  a hard punch-in (~120%, scaled about the face) — keep the mouth out of the caption band.
- Kill filler and dead air ("like", "you know", "I mean", false starts, pauses > ~0.3 s). Repeated line → the
  LAST take. Cut every f-word (keep "ass"/"shit" unless the brief says otherwise). Never show client names,
  numbers, logins, DMs: blur them (tracked blur on screens, full blur on a shared screen; faces can stay when OK'd).
- Cut edges are **measured**, never trusted: WhisperX word times run late and swallow fillers ("isn't" with a
  hidden "like" inside). RMS envelope + a slice-ASR of every assembled section before it ships.
- Briefs' timestamps run early/late by up to ~1 s: follow the briefed WORDS, not the numbers, and say so.

## Look (TikTok Sans from `assets/fonts` only — the builder asserts the family; never a system fallback)
| element | spec |
|---|---|
| **Day mark** | "DAY N" only (no "$20K a month" line since Day 6). TikTok Sans **Bold 118 px, +20 px letter tracking, 3 px black outline**, white, centred in the hook band (y182–447), **static**, on from frame 1 of the Day N hook through its end |
| **Captions** | word-by-word: each phrase pre-laid at full width, words pop in on their own beat. **Bold 58 px, white, 4 px black outline**, no box, centred. ≤ 4 words / 24 chars per line, breaks on punctuation, pauses > 0.35 s and picture changes, no one-word orphans. **Key words in CAPS** (DOWN, RIGHT, BRUTAL, SALES, COOK…). Captions run the whole video |
| **Caption height** | **per shot**, from a program-frame band check, never one height for the reel: **998** chest band when the face sits high (balcony, wide) · **1340** just under the chin, over b-roll, or under a fitted 16:9 frame · **1500** selfies where the chin sits ~y1320 |
| **Timestamps** | on b-roll only: the clip's creation time ("11:52 AM"), **Bold 44 px, 4 px outline**, bottom-left (x100, baseline y1600), 2 s |
| **Text pops** | Bold, white + outline (60 px line / 112 px number), centred, top y300, **5-frame scale pop** 0.70→0.88→1.06→1.02→1.00, hold, hard out |
| **End** | **NO end card.** The reel ends on the live close (John says the CTA himself) so it loops seamlessly — a frozen end-card still "looks really bad" |
| **Graphics** | none beyond the above: no boxes, no lower thirds, no shadows. Raw |
| **Safe zone** | key visuals inside x92–988 / y163–1670; nothing in the IG right rail or the bottom 13 % |

## Audio
- Voice: measured with `workflows/voice-gain.py`, then **Amplify + Hard Limiter −2 dBFS** on every A1 clip
  (`lanes/premiere/audio-polish.py --apply --gain <dB> --limit -2`; Day 6 +2 dB, Day 7 +5 dB). Level-match sources
  that sit apart (car/wind audio −6 dB, a call recording −3.5 dB, a quiet cutaway +4 dB) with clip Volume.
- **Every A1 joint: a 2-frame Constant Gain** centred on the cut (`lanes/premiere/joint-fades.py --apply`). Never longer
  on tight cuts (a centred fade plays half its length past the cut and brings cut words back).
- Light noise reduction on car/outdoor audio: bake `afftdn=nr=8:nf=-50:tn=1` into a `-dn` copy, video stream-copied.
- Music only if John adds it (he lays it on A2 himself): never touch it, keep it when rebuilding.
- Final: **−14 LUFS integrated, true peak under −1 dBTP**, landed by `tools/export.py` (the in-timeline mix sits a
  little under on purpose).

## Premiere rules learned the hard way
- **Never move clips with `TrackItem.move()`**: it corrupts the track model (QE sees clips out of order with phantom
  empty regions) and leaves transitions behind. To reorder: rebuild — replay the EDL in the new order, re-place,
  re-apply audio. Back up the .prproj first.
- After ANY timeline change (John's hand edits included): `tools/dump_timeline.py` → re-render captions. Captions map
  every word by its source time through the real clip positions in `premiere/timeline-clips.json`, so they survive ripple deletes, trims, splits and reorders.
- B-roll lays its own audio on A2+: `tools/place.py` removes only that, never a music bed.
- Several Premiere projects can be open at once (other sessions): activate yours by path, and say so if another one
  was active.
- Stop before export; export only on John's word.

## Files
- `tools/setup_premiere.py <job>` — project + 1080x1920 30 fps sequence + raw imports with fps pins
- `tools/dump_timeline.py <job>` — `premiere/timeline-clips.json` (V1 as it sits now; run after every timeline change)
- `tools/place.py <job>` — lays `premiere/place.json` rows (b-roll V2, captions V3, title/pops V4, timestamps V5)
- `tools/export.py <job>` — the −14 LUFS / < −1 dBTP export into `Day NNN/4-final/`
- `templates/author_edl.py` — the EDL from word anchors · `templates/build_overlays.py` — the look (one JOB CONFIG block)
- Worked examples: `projects/day-006-road-to-20k`, `projects/day-007-road-to-20k` (RUN.md, author_edl.py, build_overlays.py)
