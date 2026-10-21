---
name: 20k
description: "Road to 20K Day N reel, start to finish, in John's locked Day 6/7 look: point it at a folder of clips (and an optional editor-prompt.md) and it copies, transcribes, cuts, builds the Premiere timeline, lays the DAY N mark, word captions, b-roll timestamps and pops, applies the audio chain with 2-frame joint fades, verifies, and stops before export. Also handles the follow-ups on a Day N job: re-sync captions after hand edits, swap/reorder beats, export at -14 LUFS. Triggers: /20k, 20k preset, road to 20k, day N video, make day N, new day reel."
argument-hint: "<folder with the day's clips, e.g. ~/Movies/Road to 20K/Day 008>  [notes]"
---

# /20k — a Road to 20K Day N reel in the locked look

The spec (every number) is **`presets/road-to-20k/README.md`** — read it first, every time. This file is the
run order. Worked examples to copy from: `projects/day-007-road-to-20k/` (RUN.md, transcript/author_edl.py,
hf-graphics/build_overlays.py) and `projects/day-006-road-to-20k/`.

**Inputs:** `$ARGUMENTS` = the folder (usually `~/Movies/Road to 20K/Day NNN/` with `1-clips/`, maybe
`editor-prompt*.md` / `selects.md` / `3-edit/transcripts/`), plus any notes typed after it. The newest
`editor-prompt*.md` in that folder is the brief and wins over `selects.md`; John's chat notes win over both.
No brief → read the transcripts, find the hook / the honest numbers / the work / the lesson / the close, and
state the story you picked in the report. **Ask nothing up front**; state choices, John corrects with a word.

**Job:** `projects/day-NNN-road-to-20k/` (NNN from the folder name). If it already exists, read its `RUN.md`
and continue from there — never restart done work, never re-replay over John's hand edits without
`dump_timeline.py` + a diff first.

## The run (each step finished before the next)

1. **Intake.** `mkdir -p projects/<job>/{raw,broll/processed,premiere,hf-graphics/renders,transcript,outputs}`.
   COPY (never move) talking clips → `raw/`, picture-only b-roll → `broll/` (so WhisperX skips it). Probe every
   file: rotation, fps (120 fps slo-mo and 24 fps clips exist), creation time (→ timestamps). Look at a contact
   sheet of every clip before using it. Files outside the day folder (Downloads, call recordings) are copied
   in the same way; anything private on a screen gets blurred (see README).
2. **Transcribe.** `bash .claude/skills/rough-cut/scripts/transcribe.sh projects/<job>` (WhisperX, background it).
   A clip added later: transcribe it as a section (`projects/<job>/sections/<name>/raw/<clip>` symlink) and merge
   its entry into `transcript/words.json`. A processed copy (denoised `-dn.mov`, a blurred 9:16 call) needs a
   words.json alias entry under its own clip name.
3. **Cut.** Copy `presets/road-to-20k/templates/author_edl.py` → `transcript/author_edl.py`, write one `seg()` per
   kept phrase in timeline order, comment what was cut. `python3 transcript/author_edl.py` →
   `AMPLIFY_DB=0 RENDER=0 bash .claude/skills/rough-cut/scripts/splice.sh projects/<job>`. Then **slice-ASR the
   assembled audio of every section** (ffmpeg concat of the cuts → `uvx --from mlx-whisper mlx_whisper … turbo`):
   hidden "like"s inside WhisperX words, clipped first/last words, f-words. Fix with measured edges (5–20 ms RMS
   envelope) pinned `no_refine`, re-splice, re-check. Avoid < 6-frame slivers (they flash): drop or merge them.
4. **Premiere.** `python3 presets/road-to-20k/tools/setup_premiere.py <job>` (project, 1080x1920 30 fps sequence,
   fps pins) → `node lanes/premiere/premiere-bridge.mjs replay projects/<job>/transcript/cuts.json <anyClip>`
   (split the EDL into parts and lay a slate between them if footage is still to come) →
   `python3 presets/road-to-20k/tools/dump_timeline.py <job>`. Other projects may be open: the tools activate yours
   by path.
5. **B-roll prep.** Speed changes and fills are pre-rendered with ffmpeg into `broll/processed/` at 1080x1920 30 fps
   (8x timelapse: `setpts=PTS/8`; a short clip stretched to fill: `setpts=PTS/0.7,minterpolate=fps=30:mi_mode=blend`;
   16:9 into 9:16: blurred fill behind the fitted frame). Blur private screens before they go anywhere.
6. **Overlays.** Copy `presets/road-to-20k/templates/build_overlays.py` → `hf-graphics/`, fill the JOB CONFIG block
   from the timeline frames (DAY, END_F, HOOK_F, BROLL_F, CAP_Y_F, TIMESTAMPS, POPS) and the caption fixes keyed off
   `outputs/<job>.transcript.json` (CAPS key words, casing, punctuation, mishears like "cloud"→"Claude"). Pick each
   shot's caption height from a program-frame band check (998 / 1340 / 1500). `uv run hf-graphics/build_overlays.py all`,
   then read `hf-graphics/captions-sheet.txt`: no one-word orphans, no lowercase sentence starts, nothing missing.
7. **Place.** Write `premiere/place.json` (rows: `[track, "path", start_frame, n_frames, src_in_or_null]`; V2 b-roll,
   V3 captions from their start frame, V4 "DAY N" + pops, V5 timestamps; **no end card**) →
   `python3 presets/road-to-20k/tools/place.py <job>`.
8. **Audio.** `uv run workflows/voice-gain.py projects/<job>` (read the kept-speech LUFS) →
   `uv run lanes/premiere/audio-polish.py projects/<job> --apply --gain <dB> --limit -2` (+ `--verify`; aim the voice
   around −16 to −18 LUFS in-timeline) → clip Volume trims for sources that sit apart → 
   `uv run lanes/premiere/joint-fades.py projects/<job> --apply` (+ `--verify`: every joint, 2 frames, Constant Gain).
9. **Check.** Program frames across the whole reel (`node lanes/premiere/premiere-bridge.mjs frame '{"time":t,"out":...}'`)
   with the safe-zone guides drawn: title in the hook band, captions off the face and on beat, timestamps on b-roll,
   nothing private visible. Fix and re-check.
10. **RUN.md + report, then STOP before export.** Log the timeline (frames), every deviation from the brief and
    why, and open questions. Report in plain words: the order, what was cut, anything John should decide.

## Follow-ups on a Day N job
- **John hand-edited the timeline** (ripple deletes, reorders, added music): `dump_timeline.py` first, read every track,
  then re-render captions (they re-map through the real clip positions) and swap V3. Keep his edits and his A2 music.
- **Swap / reorder beats:** edit `author_edl.py` (or write an order file), re-splice only if words changed, rebuild by
  replay (clear tracks, replay, place, audio) — NEVER `TrackItem.move()`. Back up the .prproj first.
- **Export (only on John's word):** `python3 presets/road-to-20k/tools/export.py <job>` → `Day NNN/4-final/<job>-final.mp4`
  at −14 LUFS / true peak < −1 dBTP, verified, or it refuses to write.
