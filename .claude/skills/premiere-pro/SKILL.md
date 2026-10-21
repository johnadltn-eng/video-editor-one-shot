---
name: premiere-pro
description: "The PRIMARY finishing path — hand the rough cut to Adobe Premiere Pro, where you do the real editing and project work. Rebuilds the rough cut AS separate, trimmable clips on the Premiere timeline — it replays the edit decision list (cuts.json) against the raw footage, NOT a single flattened export — so every cut is a real edit point you can ripple/slip/slide. Triggers: send to premiere, open in premiere, finish in premiere, hand off to premiere, add the rough cut to premiere, edit this in premiere, take it into premiere."
---

# To Premiere — Rough Cut Handoff

**The primary path (2026-07-27) — and the zero-instruction DEFAULT (2026-08-28).** The standard process for all videos is that edits and project work happen inside a video editing app, Premiere by default: a bare "do a rough cut" with nothing else means the job comes here automatically after the cut (pipeline step 2) — never infer the chat-only lane from a job's content or premise. Clients finish in their own app (`capcut` / `davinci-resolve`); a client with no app gets asked before chat-only runs. Drop the cut into a ready-to-edit Premiere project, run the audio polish (step 3, below), and the real work continues there. HyperFrames stays the graphics engine feeding this timeline (alpha overlays) and the explicit-opt-in chat lane.

**This skill's own job is the HANDOFF:** get the cut onto a Premiere timeline as real, trimmable edit points, plus the step-3 audio polish and the step-4 grade. It is not the whole edit. **On a long-form `youtube/default` job the graphics pass (pipeline step 5) then runs here as the DEFAULT next step, unprompted**, see § Step 5 below. Captions are short-form only; the final render stays your. **Colour is no longer your by default (2026-08-31):** the grade is pipeline step 4, one adjustment layer on V2 under the graphics, run before the graphics pass, the mechanics are scripted AND the look is locked (Autumn-Rec709 as a Creative Look at Intensity 70 / Saturation 115, 2026-09-01), so no hand step remains.

**The cut is rebuilt AS cuts — not dropped in as one flat clip.** This is the whole point of the hand-off. The rough-cut skill already decided every edit (which raw clip, in/out points) and saved it as an EDL (`cuts.json`). This skill *replays* that EDL against the **raw footage**: each kept segment becomes its own clip on V1, end-to-end, landing at the exact same edit points the rough cut produced. So you open Premiere to the same tight cut you approved — but every boundary is a real edit point you can ripple, slip, slide, or re-trim against the original takes. Importing the flattened `outputs/<job>.mp4` as a single clip is the *fallback*, not the path (see Fallback below).

## 🔒 STEP INDEX: what this lane does at each pipeline step

**This skill carries HOW, never WHAT.** The look, the numbers and the definition of done for every
step live in the format's preset ([`presets/youtube/default/README.md`](../../../presets/youtube/default/README.md)
for long-form). Read the preset for the target, then the row below for the mechanics.
Cross-lane status: [`LANES.md`](../../../LANES.md).

| # | Step | On this lane | Where |
|---|------|--------------|-------|
| 1 | Intake | universal, no Premiere involvement | CLAUDE.md § Pipeline |
| 2 | Rough cut → replay | ✅ scripted, EDL replayed as separate trimmable clips on V1 | § Step 2 below |
| 3 | Audio polish | ✅ scripted: `audio-polish.py --apply`, the measured gain + Hard Limiter as clip effects, readback-verified; then `joint-fades.py --apply`, a 2-frame Constant Gain on every A1 joint | § Step 3 below |
| 4 | Color grade | ✅ scripted: `grade-layer` then `grade-lut.py apply`, hands-off | § Step 4 below → [`lanes/premiere/premiere-grading.md`](../../../lanes/premiere/premiere-grading.md) |
| 5 | Graphics | ✅ scripted: place alpha movs on the graphics track, bake footage moves | § Step 5 below |
| 6 | SFX | ✅ scripted: `place-sfx.py` puts the universal plan on A2–A4, readback-verified (validated on two reference jobs, 2026-09-03) | § Step 6 below |
| 7 | Review | ✋ the creator's. The run pauses here. | (none) |
| 8 | Export | ✋ the creator renders, AME is banned, nothing here renders a deliverable | § Step 8 below |

Captions are short-form only (long-form takes YouTube CC). Background music is opt-in and lands on
the music track by hand.

## When to use
- you say any trigger phrase above, OR
- A rough cut exists and you want to finish manually in Premiere instead of HyperFrames.

If there's no rough cut yet, run `rough-cut` first **with `RENDER=0` on the splice** — the EDL + canonical transcript generate in ~8 seconds without a flat render, and this skill consumes nothing else. **Never render a flat MP4 for a Premiere-finish job** (2026-07-22 — a 4K render gated the handoff by 20+ minutes for zero benefit). Time-to-timeline = transcription + cuts + seconds. (You *can* import raw footage instead if you explicitly ask, but the point of this handoff is the tightened cut.)

## What it needs first — the bridge must be live

This skill drives Premiere through the **`premiere-pro` MCP server** (wired in `.mcp.json`). That server only does anything when Premiere is open with the bridge panel running.

**Engine (migrated 2026-07-18): `vendor/premiere-mcp/` — a pinned local clone of [hetpatel-11/Adobe_Premiere_Pro_MCP](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP)** (pinned at commit `12684e3` = **v1.2.3**, bumped 2026-08-28 from `cc57eb4`; 283 tools). The old `premiere-pro-mcp` npm package was a knockoff republish of this repo (its "official repo" link 404s) with a broken hand-rolled CEP `CSInterface` shim — the all-null bridge failure of 2026-07-09 was knockoff damage, not a Premiere bug. The clone IS the pin: update only via deliberate `git pull` + re-run the verification pass + record the new hash here. Rebuild after pull: `npm install && npm run build` in `vendor/premiere-mcp/`, re-copy `cep-plugin/` to the CEP extensions dir if it changed (re-apply `lanes/premiere/premiere-templates/cep-bridge-autostart.patch` first — it applied clean on v1.2.3), then restart Premiere.
   - **v1.2.3 bump notes (2026-08-28):** the v2 server rewrite kept the module API `premiere-bridge.mjs` imports (`dist/bridge/index.js` `PremiereProBridge`, `dist/tools/index.js` `PremiereProTools.executeTool`) — no bridge.mjs changes needed. File protocol unchanged (`command-<id>.json`/`response-<id>.json`); responses now written atomically (staging + rename), panel drops a `bridge-heartbeat.json`, dead bridge fails fast instead of timing out, evalScript-timeout double-fire fixed. **Telemetry (added upstream v1.2.2, default-on, POSTs tool-call events to the maintainer's worker) is OFF here two ways:** `"telemetry": false` in `~/.premiere-mcp-bridge/config.json` (the server reads this file too) + `PREMIERE_MCP_TELEMETRY=0` in `.mcp.json` env. Telemetry lives only in the MCP entry (`src/index.ts`) — bridge.mjs never touches it. Verified post-bump on Premiere 26.3.2 / your-job: autostart ping, ES round trip (35/35 V1+A1 clips read), Amplify + Hard Limiter readback intact, bridge `frame` grab correct at 5.0s. The MCP-session tools pick up the new dist on the next Claude Code restart; bridge.mjs runs it immediately.

1. **MCP tools available?** The `premiere-pro` tools (`mcp__premiere-pro__*`) load at Claude Code session start. If you don't see them, the `.mcp.json` was added after this session began — tell you to **reconnect/restart Claude Code** once, then retry. **No MCP tools at all (session rooted outside this repo)?** Drive the bridge headless instead: `node lanes/premiere/premiere-bridge.mjs <tool> '<json>'` calls the same tool handlers directly via the file bridge — same panel requirement, no MCP session needed. It also batches the whole step-7 replay in one command.
2. **Bridge connected?** Call `ping` first. If it errors or times out, the panel isn't running. **"Is Premiere running?" is answered ONLY by `lanes/premiere/premiere-pid.sh`** (prints the app binary's pid, `--name` prints its process name), never by a hand-typed `pgrep`: the process is year-suffixed (`Adobe Premiere Pro 2026`), so `pgrep -x "Adobe Premiere Pro"` reports "not running" with the app on screen (2026-09-02, said so to you with the panel live), and `pgrep -f` on the path over-matches crashpad, the CEP helpers and AdobeIPCBroker. A running app with a dead panel is still unreachable, so the pid answers "running", only `ping` answers "drivable". If ping fails, tell you, in one line:
   > Open Premiere Pro → **Window → Extensions → MCP Bridge (CEP)** → click **Start Bridge** (temp dir defaults to `/tmp/premiere-mcp-bridge`).
   **Try the scripted launch FIRST — it usually removes the ask:** `./lanes/premiere/premiere-up.sh [projects/<job>/premiere/<job>.prproj]` launches Premiere with the CEP autostart patch so the bridge comes up on its own; re-`ping` after it settles and only fall back to the manual line above if that still fails. (`--restart` never force-kills — a non-graceful exit makes Premiere treat it as a crash, and the crash dialog blocks the panel.)
   Then retry `ping`. Don't proceed until it returns ok.

The temp dir in the panel **must match** `PREMIERE_TEMP_DIR` in `.mcp.json` (`/tmp/premiere-mcp-bridge`) — that shared folder *is* the bridge. Protocol is `command-<id>.json`/`response-<id>.json` files (the knockoff used `cmd_*.jsx`/`res_*.json` — old panel and new server can NOT interoperate).

## Step 2: the EDL replay (the handoff itself)

1. **Resolve the job.** Newest folder under `projects/` unless you named one.
2. **Locate the EDL + raw footage.** The EDL is `projects/<job>/transcript/cuts.json` (persisted durably by `splice.sh`); if it's missing there, check `/tmp/video-editor/<job>/cuts.json`. The raw clips are in `projects/<job>/raw/`. **Both must exist** — they're what we replay. If `cuts.json` is gone from both spots, you can't rebuild the cuts; take the **Fallback** path instead and tell you why (the EDL wasn't persisted for this older job).
   - Read `cuts.json`. It's `{ "segments": [ { "clip": "clip-01.mov", "start": 1.24, "end": 4.60, "transcript": "..." }, ... ] }`. Segment order = timeline order. `start`/`end` are seconds **in the raw clip** (raw timeline), which is exactly what the Source Monitor in/out points take.
3. **Preflight** the bridge (`ping`) per above.
4. **Create the project** at `projects/<job>/premiere/<job>.prproj` (`create_project`). If it already exists, `open_project` it instead of clobbering your in-progress work — ask if unsure.
5. **Import the raw clips** (`import_media`) — every distinct `clip` referenced in `cuts.json`, from `projects/<job>/raw/`. (Not the flattened `outputs/<job>.mp4` — that's the fallback only.) Note each imported item's id/name for the Source Monitor. **New-engine arg (2026-07-18): `import_media` takes `filePath` (a single string) — one call per file.** The old `file_paths` array form was the knockoff.
6. **Build a matching sequence.** On Premiere 26.x `create_sequence` without a preset is broken (`createNewSequence` now needs a second arg → "Not Enough Parameters"). The working path: `create_sequence_from_clips` with the imported raw clip (or DOM-direct via `execute_extendscript`: `app.project.createNewSequenceFromClips(name, [item])` + `app.project.activeSequence = seq` — verified 2026-07-18) — the sequence inherits the footage's exact dimensions/framerate — then empty the timeline before the replay. **`remove_selected_clips` returns `available:false` on the new engine** — clear via ES instead: loop every video/audio track backwards, `track.clips[i].remove(false, false)`. Confirm with `get_sequence_settings` (e.g. 1920×1080, videoFrameRate 0.0417s = 23.976).
7. **Replay the EDL onto V1 — one segment at a time, in order.** This is three-point editing, the same move a human editor makes. For each segment:
   1. `open_in_source` the segment's raw clip (`item_id` = the imported clip's id/name).
   2. `set_source_in_out` with `in_seconds = segment.start`, `out_seconds = segment.end`.
   3. `overwrite_from_source` onto `video_track_index: 0` (V1).
   - **The playhead does NOT auto-advance on Premiere 26.3 (verified 2026-07-17)** — every overwrite lands at the current playhead, so without advancing it each segment clobbers the last (symptom: final duration = longest segment, fragment clips). Before EACH overwrite, `set_playhead_position` to the cumulative sum of prior segment durations (frame-snap the sum at the sequence fps), and read `get_playhead_position` back to confirm it moved. The param is **`time_seconds`** — a wrong key (e.g. `seconds`) interpolates `undefined` into the ExtendScript and silently no-ops; bridge handlers don't validate args, so always read state back after a write.
   - Easiest: run the whole loop in one command — `node lanes/premiere/premiere-bridge.mjs replay projects/<job>/transcript/cuts.json <clipName>` does set-playhead → in/out → overwrite per segment with the playhead check built in, then saves.
   - **`setInPoint`/`setOutPoint` FLOOR at tick conversion (measured 2026-07-18):** frame-grid times are repeating decimals, and a double that serializes a hair below the exact tick value lands one frame EARLY (one out-point came up a full frame short on an on-grid EDL). The `replay` command nudges every boundary +1e-4s (0.24% of a frame — floor resolves to the intended frame, off-grid EDLs unaffected); do the same in any hand-written ExtendScript that sets in/outs from EDL seconds, and always verify with `get_sequence_structure` against the EDL afterward.
   - **Result:** N separate clips on V1, each a real edit point. you can ripple/slip/slide/re-trim any of them against the full raw take — the original heads and tails are still there in the source, just trimmed off by the in/out. Verify with `get_sequence_structure`: clip N's `startSeconds` == clip N-1's `endSeconds` (no gaps), and each clip's `inPointSeconds`/`outPointSeconds` within one frame of the EDL.
8. **Save** (`save_project`) and confirm: report the `.prproj` path, the segment count on V1, and that the rough cut is rebuilt as individual edits ready for you to fine-tune in Premiere.

## Step 3: audio polish, immediately after the replay verifies

**Run it now (2026-08-28), not at picture lock.** The timeline should never sit unpolished
waiting for picture lock; a later rebuild just re-runs the pass. Target: the preset § Audio polish.

```
uv run lanes/premiere/audio-polish.py projects/<job> --apply     # measured gain (voice-gain.py) + limiter on every A1 clip, read back, save
uv run lanes/premiere/audio-polish.py projects/<job> --verify    # exit 1 on any clip off the chain
uv run lanes/premiere/audio-polish.py projects/<job> --apply --gain 15   # a named gain, when you call one
uv run lanes/premiere/joint-fades.py projects/<job> --apply      # 2-frame Constant Gain on every bare A1 joint, read back, save
uv run lanes/premiere/joint-fades.py projects/<job> --verify     # exit 1 on any A1 joint with no transition
```

Validated 2026-09-03: the value writes on your-job (35/35), the effect-ADD path on a
scratch sequence (chain added to 2 bare clips, read back, removed again). Mechanics it encodes:

- **House standard (John, 2026-10-16): a 2-frame Constant Gain on EVERY A1 joint** (`joint-fades.py`),
  centred on the cut; it smooths the jump in the voice. Keep it at 2 frames: a centred fade plays half
  its length of the audio past the cut, and at 9 frames that faded removed words back in on tight cuts
  ("30", "like", "that", measured on day-005). Joints that already carry a transition (the editor's own,
  any type or length) are skipped, never replaced. A re-replay drops transitions: re-run `--apply`.
- **No per-section audio work during the cut itself (2026-07-30):** no clip gain or
  level-matching between sections while authoring/laying the cut, even when one reads several dB
  quiet. Measuring levels as information is fine, acting on them is not.
- **The chain, as clip audio effects on every A1 clip:** the gain from `workflows/voice-gain.py`
  (kept speech to −17 LUFS pre-limiter), then QE `addAudioEffect("Amplify")` + `addAudioEffect("Hard Limiter")` and
  DOM property writes: Amplify Left+Right `v=(dB+96)/144` (+10 → 0.73611), Hard Limiter "Maximum
  Amplitude" `v=(dB+100)/100` (−6 → 0.940; leave Input Boost/Look-Ahead/Release at defaults). Read
  every value back after writing (validated 2026-08-28, 31/31 clips). One pass over the whole
  timeline; effects stay hand-tweakable.
- **A timeline rebuild (clear + re-replay) discards clip effects**, after ANY re-replay of the EDL,
  re-apply the chain to every A1 clip and re-verify before saving; a recut that skips this ships
  unpolished audio silently.
- **ES audio effect params are normalized 0..1 over the slider range (2026-07-30):** Amplify
  Left/Right dB = `v*144 − 96` (range −96..+48; beware: the wrong guess −48..+24 ALSO puts 0 dB at
  0.66667, so a 0 dB sanity check cannot distinguish them, and a +7 wrote as +14 in the UI before
  this was caught). Hard Limiter Maximum Amplitude: `v = (dB+100)/100` (range −100..0). For any NEW
  param, verify the domain by writing a NON-zero, off-center value and reading the UI or a frame
  grab back before batch-applying; two candidate ranges can agree at one point.

## Step 4: the grade, BEFORE graphics and underneath them

**Full lane recipe and every trap: [`lanes/premiere/premiere-grading.md`](../../../lanes/premiere/premiere-grading.md).**
Read it before touching a grade here, three separate failures in this area all present as "the
grade does nothing" and none of them is visible in a readback.

The whole step on this lane is two commands' worth of work:

1. `node lanes/premiere/premiere-bridge.mjs grade-layer` with the job's sequence active. Provisions the
   V1/V2/V3/V4 tracks, mints an adjustment layer **at the frame size it reads off the sequence**,
   lays one instance on **V2** spanning V1, names it `GRADE`, adds Lumetri, and saves. Idempotent.
2. `./lanes/premiere/premiere-up.sh --quit` → `uv run lanes/premiere/grade-lut.py apply <job>.graded.prproj`
   (a COPY) → `./lanes/premiere/premiere-up.sh <job>.graded.prproj` → frame delta with the layer toggled →
   quit → swap the copy over the job file. The file must be CLOSED while the tool writes it, and it
   is written into a copy so a refused open is a file that did not open, never a modal on the job.
   After any refused open, nothing else is opened until `./lanes/premiere/premiere-dismiss.sh --check`
   reports zero (lane doc § 2, the hard gate).

**Do it before a single graphic is placed.** The track is free at setup and expensive to insert
later, and the graphics QA measures contrast and glow against whatever the footage looks like.
Retrofitting onto a timeline that already has graphics is one QE `addTracks` call, not a re-lay, 
see the lane doc. Then verify from a bridge `frame` grab with the layer toggled, never from the
effect readback, and read every track's mute state first.

☠️ **Never use the MCP's `apply_lut` tool.** It is a measured no-op that reports success, and on a
clip that already carries a Lumetri (which every GRADE layer does) it writes into the wrong
instance and resets it. Reasons and evidence: the lane doc.

## Fallback — flat clip import

Only when the EDL is unavailable (old job, `cuts.json` lost from both durable and `/tmp` spots) or you explicitly ask for "just the flat cut as a reference":

1. `import_media` the `outputs/<job>.mp4`.
2. `create_sequence` matching its dimensions/framerate.
3. `add_to_timeline` at the start of V1 (one clip).
4. Save and tell you it's the **flattened** cut — the individual edit points aren't recoverable, so re-trims mean razoring by eye. If you want real edit points, re-run `rough-cut` so a fresh `cuts.json` gets persisted, then hand off again.

## Step 5: graphics on the timeline (validated 2026-07-18, `your-job`)

**The preset you are on IS the architecture — read it first and treat its track map as authoritative.** Long-form default → [`presets/youtube/default/README.md`](../../../presets/youtube/default/README.md) (V1 footage / V2 grade / V3 graphics / V4 accents, at source resolution, grade UNDER the graphics and run at pipeline step 4). The lane-agnostic Premiere craft — keyframe laws, clip lifecycle, b-roll placement — lives in this skill, below. **Every preset-specific timeline architecture lives in its own preset folder**, including the vox-collage 4K / adjustment-layers-on-top stack ([`presets/youtube/vox-collage/premiere-lane.md`](../../../presets/youtube/vox-collage/premiere-lane.md)) — that one is opt-in by name and its grade placement is the inverse of the default's, so never read it on a default job.

**On a long-form `youtube/default` job the graphics pass is part of the DEFAULT edit, not an extra** (CLAUDE.md step 5 routes horizontal footage to that preset and applies its vocabulary unprompted) — so after the EDL replay, the audio polish (step 3) and the grade (step 4), this flow runs WITHOUT being asked. The whole pipeline-step-5 flow runs here — plan → build → place → bake → converge — with every graphic left hand-editable (separate graphics-track clips + real keyframes):

1. **Plan** with `graphics-plan` as usual — it resolves the preset itself (horizontal long-form → `presets/youtube/default/`; `liquid-glass` and the other looks are opt-in BY NAME only). Anchor beat times to the refined EDL / canonical transcript word timestamps.
2. **Author comps** in `projects/<job>/hf-graphics/gfx/compositions/` and render with the job's `render.sh` (copied from `presets/youtube/default/reference/fullscreen-render.sh`): **`render.sh <id> alpha`** for overlays (ProRes 4444 straight alpha) and **`render.sh <id> full`** for full-screen graphics (opaque mp4, film grain baked; bg-dark adds `STEP_FPS=12`). Comp gotchas and the QA gates live in the **`graphics-build`** skill — that skill owns the build; `lanes/chat-only/incremental-graphics.md` is the CHAT-ONLY assemble lane and does not apply here. (Universal comp rule: ALL CSS inline, no `<link>`.)
3. **Place overlays on the GRAPHICS track** with **`uv run lanes/premiere/place-graphics.py projects/<job> --plan --write` then `--apply`** (2026-09-02: owns `hf-graphics/placement.json`, derives rows from the plan + the newest render version, places what is missing, swaps stale versions, reads every write back; `--verify` / `--sync-plan` / `--remove <id>`). Underneath it is `importFiles` + `seq.videoTracks[N].overwriteClip(item, startSeconds + 1e-4)` (the tick-floor nudge) + `clip.end = t`. ⚠️ **N is 2 (V3) on the youtube/default map**, V1 footage, V2 grade, V3 graphics, not the `videoTracks[1]` this step used before the grade layer existed. Read the preset track map, never hardcode from memory. Alpha composites natively: no keying, no effects needed. Two traps, each paid for: **a re-render is a NEW filename + a fresh import** (overwriting a placed path half-stales Premiere's frame index and random frames come back transparent), and **a same-track overwrite then trim leaves a crater** (placing a clip over a neighbour's head and trimming back does NOT restore the neighbour; re-lay it, then read the track back, which `place-graphics.py --verify` does). Program grabs come from the bridge `frame` command, never by fronting the app.
4. **Bake footage moves on V1** (they mirror the comp's motion): the `zoom` command for punch-ins; custom ES for reframe pushes — per-frame keys on Transform Scale H+W and Position (normalized [x,y] arrays), all key times in **source-clip time** (`clip.inPoint.seconds + offset`). A move that crosses a V1 edit is split: first clip pushes in and HOLDS to its tail, next clip starts held and releases (frame-aligned local key offsets on each).

   **The `zoom` command** takes the preset's numbers straight:
   ```
   node lanes/premiere/premiere-bridge.mjs zoom '{"clip":0,"from":107,"to":100,"frames":10,"ease":"cubic","fps":"30000/1001"}'          # opening zoom-out, starts at the in point
   node lanes/premiere/premiere-bridge.mjs zoom '{"clip":8,"from":100,"to":108,"frames":12,"ease":"cubic","fps":"30000/1001","at":28.3}' # emphasis push-in, starts at a word
   ```
   `fps` = the sequence's exact rational rate; a wrong rate stretches the ramp. `at` is a
   **sequence** time in seconds: feed it the word timestamp (minus ~2 frames) and the command
   resolves it into the clip's source-time domain itself. `offset` takes frames past the clip's in
   point instead. Omit both and the ramp starts at the in point.

   Three things the command handles that a hand-rolled bake gets wrong, each of which cost time
   before it existed:
   - **Keys BEFORE the ramp survive.** Clip 1 can carry the opening zoom-out *and* a push-in in the
     same property track; the command clears only from the ramp start onward, so re-baking a push-in
     cannot destroy the opening move. (At the default offset that is still a full clear, so the
     opening zoom-out behaves exactly as before.)
   - **It refuses rather than half-writes.** A ramp that would start before the clip or run past its
     end errors with the measured numbers and changes nothing.
   - **Motion and Transform are different effects.** The bake is on Transform, on both `Scale Height`
     and `Scale Width`; querying `Motion/Scale` across a track reports zero keyframes and reads as
     "there are no push-ins here."

   Verify by reading back: on a 12-frame cubic ramp the midpoint (frame 6) must be exactly
   **107.00**: a linear bake reads 104.00 there.
5. **QA every graphic from the real program render**: `node lanes/premiere/premiere-bridge.mjs frame '{"time":<sec>,"out":"/abs/path-no-ext"}'` — full composite (keyframes, alpha overlays, unsaved state) with zero AME involvement. Iterate: edit comp → `render.sh <id>` (media auto-relinks by path; mtime change invalidates Premiere's cache) → re-grab → done.
6. **Watchable preview only when needed — NEVER via AME (your hard rule, 2026-07-20)**: `export_sequence` queues into AME, so it is off-limits for everything (full exports, QA bounces, audio checks — all of it). Render through Premiere itself instead: `sequence.exportAsMediaDirect(outPath, presetPath, workAreaType)` via `execute_extendscript` (synchronous, in-Premiere, system `.epr` presets like `.../systempresets/4E49434B_48323634/YouTube 1080p HD.epr` or the WAV preset under `3F3F3F3F_57415645/` still apply — verify the export on first use, it's untested on the new engine). Frame QA stays the bridge `frame` command; often the right move is no render at all — read state back and let you play the timeline.

7. **Converge with `edit-review` — step 5c, and it is part of the graphics step, not an optional extra.** The build's own first-pass QA (5) is the builder grading itself; this is fresh eyes. Run the loop until a full round comes back clean, fixing part-by-part, and only then move to step 6. **Objective defects must never reach your review (step 7)** — that pass is taste, and only taste.

### Keyframe & effect laws (hard-won, lane-agnostic, do not relearn)

These hold on every Premiere job regardless of preset — they were distilled from the shipped
`your-job` intro but none of them is a look choice.

- Clip keyframes live in **source time**: `inPoint + offset`. Synthetic media (adjustment layers) has inPoint ≈ 3600 s, and it RISES when the head is trimmed.
- **Baked keys are the standard** for any scripted motion: one key per frame (or per 2 frames) sampled off the curve, all linear. Eases via scripting are broken/limited; bake the shape.
- Point params (Position/Anchor) are **normalized** (0.5,0.5 = center — for offsets divide px by frame dims); scalars read/write in display units. Always read back after writing.
- Effects apply via QE: `qe.project.getVideoEffectByName` + `qclip.addVideoEffect`; **walk `getItemAt(i)` for `type === "Clip"`** — gaps are items, so a clip that doesn't start at 0 is not item 0.
- **Adjustment layers: intrinsic Motion is inert on the image** (it moves only the layer's bounds). Image moves = the **Transform effect**; set Scale Height AND Width explicitly (the uniform toggle is untrusted). Prove any new transform assumption with an exaggerated offset + frame grab BEFORE baking hundreds of keys. (Minting the layer itself: Notes below.)
- **Rendered preview files DROP AI-masked layers (Premiere 26.x)** — green-bar playback lies, yellow is truth. Delete render files (`qe.project.deletePreviewFiles("228CDA18-3625-4d2d-951E-348879E4ED93")`) and never tick "Use Previews" on export. Real renders (bridge `frame` grabs, direct exports) composite correctly.

### Graphics clip lifecycle (also lane-agnostic)

- **Place** — `import_media`, then ES `videoTracks[n].overwriteClip(item, edlTime)`; trim the renderer's +1 pad frame via `c.end = t`. Graphics land ON the EDL cut times (frame-snapped splice ⇒ EDL == timeline).
- **Iterate** — edit the comp → re-render the ONE affected part → `refresh_media` (same duration = in-place, keys/effects survive; duration changed = refresh twice in separate calls, then re-place). Never re-render the whole family for one tweak. **If the re-render changed CONTENT or duration, version the FILENAME (`<id>-b.mov`) and import fresh instead of overwriting the placed path (2026-08-01):** `refreshMedia` over a same-path rewrite left Premiere's frame index half-stale — *specific frames* rendered as nothing (program monitor AND `frame` exports; frame 126 perfect, frame 135 fully transparent) while the mov itself scanned clean.
- **Anchor beats to MEASURED audio, not raw WhisperX** — word starts run ~50-100 ms late; scan a 5 ms RMS envelope of the base cut around the WhisperX time and land on the acoustic attack, snapped to the frame grid.
- **The editor re-trims between sessions** — read the LIVE timeline before computing anything against it, never docs or memory for clip spans.
- **Re-timing or swapping a graphic orphans its SFX silently** — SFX are aligned to graphic beats, so check the SFX tracks in that window and surface affected clips to you rather than moving your sound design unasked. (This is why SFX is pipeline step 6, after the graphics defect loop.)
- **Generated b-roll:** `videoTracks[n].overwriteClip` + `audioTracks[n].overwriteClip` at the same time so the voice on A1 stays untouched. Which track depends on the preset's map, and whether the clip should take the grade (above the grade layer = ungraded, usually right for a generated clip).

Engine arg quirks measured on this run: `refresh_media` needs `projectItemId` (skippable — replaced media re-reads by path), `export_sequence` REQUIRES `presetPath` (.epr), `remove_selected_clips` unavailable, `import_media` takes `filePath` singular.

## Step 6: SFX on the timeline (built 2026-09-03; placed and readback-verified on two reference jobs (120/120 and 122/122 rows, the second reviewed and hand-tuned by ear the same day))

WHAT: [`presets/youtube/default/sfx.md`](../../../presets/youtube/default/sfx.md). The plan is universal
and already written by the time this lane is involved: `uv run workflows/sfx-plan.py projects/<job>`
→ `hf-graphics/sfx-plan.{json,md}`. This lane only places it.

```
uv run lanes/premiere/place-sfx.py projects/<job> --apply     # place, set levels, read back, save
uv run lanes/premiere/place-sfx.py projects/<job> --verify    # readback vs the plan (exit 1 on drift)
uv run lanes/premiere/place-sfx.py projects/<job> --remove    # clear every library SFX clip before a re-plan
uv run lanes/premiere/place-sfx.py projects/<job> --diff      # the creator's hand edits vs the plan (MOVED / REMOVED / LEVEL / SLICE / ADDED): the input for the next rule
```

Mechanics, each read back before it is believed: the library file is imported ONCE into an `sfx`
bin and found by media path afterwards; audio tracks are provisioned with QE
`addTracks(0, 0, 1, 1, numAudioTracks, 0, 0)` (appends, nothing placed moves); the slice is set as
the project item's in/out (`setInPoint(t, 4)`), `audioTracks[n].overwriteClip(item, at + 1e-4)` (the
replay's floor nudge), then the in/out are cleared; the level is the clip's intrinsic Volume >
Level, `v = 10^((dB − 15) / 20)` (the encoding read off eleven whole-dB values on your-job:
0 dB = 0.17783, −12 = 0.04467, +5 = 0.31623). A run stops on the first readback mismatch. A timeline
rebuild (re-replay) drops these clips like it drops the A1 chain: re-run `--apply` after one.

## Step 8: export (the creator's, not this lane's)

**Where the automated work ends:** the graphics pass and its defect loop finish at *placed +
verified* on the timeline. The final render and the export are your own Premiere work, by design.
**AME is banned** (2026-07-20), `export_sequence` queues into it, so nothing here renders a
deliverable. A watchable bounce, when one is genuinely needed, goes through
`sequence.exportAsMediaDirect(outPath, presetPath, workArea)` via ES; frame QA stays the bridge
`frame` command.

**When you render, the settings lock is CBR, not VBR.** Premiere's H.264 exporter on Apple Silicon
runs through VideoToolbox, whose VBR treats the target bitrate as a **ceiling**: a 27-min 4K
sequence set to VBR 50/65 landed at 17.6 Mbps average. Set `ADBEVideoBitrateEncoding` to **0 (CBR)**
in the `.epr` and it hits 50.0 Mbps exactly. **50 Mbps IS the measured quality ceiling** (VMAF
against a ProRes 422 HQ reference: CBR 50 = 97.44, CBR 65 = 97.44 to 6 dp, VBR 50/65 = 96.63,
software x264 CRF 14 = 97.21), more bits change nothing. Full recipe and the `.epr` patching
gotchas: CLAUDE.md Lab Notes § YouTube export.

**Then `./finalize.sh <job> --apply`**: but only once a real final file exists in `outputs/`.
**Never render one just to close the step.**

## Notes
- **When you references live timeline state — "the in and out points I set", "the highlighted clip", "what I selected", "at the playhead" — QUERY PREMIERE FIRST, before any interpretation (2026-08-28, you had to demand it).** The sequence carries your marks and selection and they are one call away: `seq.getInPoint()`/`getOutPoint()` (seconds as strings), `clip.isSelected()` across tracks, `get_playhead_position`. Guessing which section you mean from conversation context instead of reading your marks caused a wrong segment to be diagnosed AND deleted. Your timeline state IS the instruction; the conversation is only commentary on it. After acting on marks, clear them (`setInPoint(0)`/`setOutPoint(0)`) so stale marks don't mislead the next pass.
- **Colour is NOT the creator's any more (2026-08-31)**, the grade is pipeline step 4, an adjustment layer on V2 laid before the graphics pass. You picked the LUT once (`Autumn-Rec709.cube`, 2026-09-01, chosen over London) and it is applied headlessly by `lanes/premiere/grade-lut.py`, no hand step remains. Where the automated work DOES end is the render and the export: § Step 8 above.
- Keep the HANDOFF itself surgical: import raw + matching sequence + the EDL replayed onto V1. (On a long-form `youtube/default` job the graphics pass then runs as the default next step — see Graphics in Premiere above. On other jobs it is triggered by the plan.)
- **Why rebuild from the EDL instead of importing the flat MP4?** So the cuts are *real edit points*, not baked pixels. A flattened clip forces you to razor by eye to adjust any boundary; replaying the EDL gives you every cut as a trim handle with the full raw take behind it. This is the standard hand-off for every app-finish job: the editor-grade hand-off.
- **Audio rides along.** `overwrite_from_source` lays the clip's audio onto A1 in lockstep — no separate audio step. The EDL's segments stay A/V-synced because in/out points apply to the source clip as a whole.
- **Section color-coding: set the project item's label BEFORE the replay** (`item.setColorLabel(idx)`, 0–15: Violet Iris Caribbean Lavender Cerulean Forest Rose Mango Purple Blue Teal Magenta Tan Green Brown Yellow). Timeline clips STAMP the label at insert time and track items expose no label API at all (verified 2026-07-23: DOM trackItem has zero label/color methods, QE only `setBorderColor`, the MCP's `select_clips_by_color` is a stub) — changing the item's label later does NOT recolor laid clips; the only scripted recolor is wipe + re-replay. **Label NAMES lie about rendered color (2026-07-31):** Caribbean renders olive/lime green (nearly collided with an existing Green section), Rose failed at ΔRGB 14.5 from Magenta, Teal sat Δ≈31 from both Iris and Green. Never pick by name: read every laid item's `getColorLabel()`, test the candidate with ONE throwaway clip (`setColorLabel` → single `overwriteClip` → `window-grab.sh` → sample the V1 row; the RGB distance to each laid section must beat the tightest existing pair), then remove the test clip. Reach for the missing hue family, never a neighbour of an existing band.
- **Job projects live at `projects/<job>/premiere/<job>.prproj`, always.** Never let a project be born from Premiere's own save dialog — its default location is the rotating Auto-Save folder, which Premiere prunes (two real job projects were rescued from there 2026-07-17). Superseded drafts go in `premiere/archive/`. A project that ended up in the WRONG job folder relocates in ONE call: ES `app.project.save(); app.project.saveAs(newPath)` — verified 2026-07-29 moving `your-job.prproj` out of `your-job/premiere/` with the project open and a live timeline: `app.project.path` switches, all media stays online (media paths are absolute), scratch/Auto-Save follow to the new folder on the next save, and the CEP bridge survives. This supersedes the cp + `openDocument` + `closeDocument` dance below for relocations (that dance is still the only route if `saveAs` ever regresses — and note the DOM `saveAs` is NOT the same as the `save_project_as` MCP tool, which is still untested). Delete the stale copy at the old path afterward.
- **Engine verification pass (2026-07-18, new engine on Premiere 26.3):** FIXED vs the knockoff: `list_available_effects` (real list), `apply_effect` (works — args are `clipId`/`effectName`), `undo` (works, verified removing an applied effect), `export_frame` (works via QE — args `sequenceId`/`time`/`outputPath`/`format`; it APPENDS the format extension to outputPath, so pass a path without one). **⚠ but its TIME argument is broken (root-caused 2026-07-18): use `node lanes/premiere/premiere-bridge.mjs frame '{"time":<sec>,"out":"/abs/path-no-ext"}'` instead.** QE's `exportFramePNG` accepts ONLY a timecode STRING: numeric seconds THROW ("Illegal Parameter type"), so the vendored tool's fallback chain lands on `String(seconds)`, which QE parses as a FRAMES timecode — `time: 18` silently exports frame 18 (~0.75s), not 18s (a ticks string is equally wrong). Fed a proper `HH:MM:SS:FF` timecode, the QE grab renders the FULL current program state — keyframed effects, fresh unsaved keys, and alpha overlay tracks all composite correctly (verified against an AME export of the same frame) — so it IS the right QA tool, no AME needed. The bridge `frame` command does the seconds→timecode conversion off the active sequence's fps. `export_sequence` works (system `.epr`, queues in AME asynchronously) but is BANNED — AME is off-limits (house rule, 2026-07-20); use `exportAsMediaDirect` via ES when a render is truly needed. Args are zod-validated — wrong keys fail loudly with the expected schema, so the silent-no-op class is dead; note arg names vary per tool (`clipId` vs `node_id` — the validator tells you). `--desc` prints raw zod internals; read the schema in `vendor/premiere-mcp/src/tools/index.ts` instead. STILL OURS: `add_keyframe` writes raw SOURCE time exactly like the knockoff (raw API behavior — keep computing `inPoint + offset`; the `zoom` command does). UNTESTED on the new engine: `save_project_as`, `create_bars_and_tone`, `delete_project_item` — verify before first use. `remove_effect` is intentionally absent from their catalog and no-arg QE `removeEffects()` returns true but removes NOTHING — but real removal IS scriptable (found 2026-07-23, batch-removed 126 DeNoise instances): QE `item.getComponentAt(i)` returns a live component whose methods include **`.remove()`** — match `comp.name`, iterate indices BACKWARDS (they shift on removal), then verify survivors via DOM `clip.components`. Sibling effects and their values survive. (DOM components expose no removal — `.remove()` exists only on the QE side; a component's bypass checkbox is DOM `properties[0]`, the unnamed boolean, when a soft-off is enough.) The CSInterface re-patch instruction is OBSOLETE — the new panel ships Adobe's real CSInterface.
- **Premiere 26.3 bridge quirks (2026-07-17, measured on the OLD knockoff engine):** `save_project_as` is fully broken — it returns `saved: true` but writes NOTHING and doesn't switch the open project (never trust it; verify with `app.project.path` + `ls`). To relocate a project: `cp` the saved .prproj on disk to the new path under a DIFFERENT filename, `app.openDocument(newPath)` (opens as a second project and becomes active), then `closeDocument` the old one — Premiere refuses to open a path whose filename matches an already-open project, and closing the LAST open project drops Premiere to the Home screen and KILLS the CEP bridge (the editor must reopen a project, then Window → Extensions → MCP Bridge → Start Bridge), so always keep one project open through the swap. `export_frame`/`capture_frame` (`exportFramePNG` gone), `create_bars_and_tone`, and `delete_project_item` (`deleteProjectItem` gone) are all broken on 26.3 — verify visually via the program monitor instead, and have the editor delete panel items by hand. `undo` (`app.project.undo is not a function`) and `multiple_undo` (silently returns `undone: 0`) are broken too — there is NO undo through the bridge, so revert experiments with inverse writes (e.g. `remove_keyframe_range` + `setTimeVarying(false)` via `execute_extendscript` to clear a stopwatch). Motion-effect control verified working 2026-07-17: `add_keyframe`/`get_keyframes`/`set_keyframe_interpolation`/`remove_keyframe_range` on Motion (Position/Scale/Rotation/Anchor Point/Crop) and Opacity all land and read back correctly. `apply_effect` and `list_available_effects` are broken on 26.3 ("Effect not found" / empty list) — apply effects via `execute_extendscript` QE instead: `app.enableQE(); item.addVideoEffect(qe.project.getVideoEffectByName("Transform"))` (walk `track.getItemAt(i)` for `type === "Clip"`). Once applied, the normal keyframe/property tools drive it fine — verified with a Transform zoom-out + motion blur (keyframe Scale Height AND Scale Width identically instead of trusting Uniform Scale; crank `Shutter Angle`, e.g. 360 — measured 2026-07-17 on 26.3: blur renders with `Use Composition’s Shutter Angle` (U+2019 curly apostrophe in the name) checked OR unchecked, so don't fight over that box). **Clip keyframe times are in SOURCE-CLIP time, not clip-relative time (bit hard 2026-07-17):** `add_keyframe`'s `time_seconds` says "relative to clip start" but passes straight through to `addKey`, whose domain starts at the media's frame 0 — on a trimmed clip the keys land before the in-point: invisible in Effect Controls, stopwatch on, no motion (value sits at the last key). Always add keys at `clip.inPoint.seconds + offset` (frame-snap the offset at 1001/24000 for 23.976), and use the same domain for `get_keyframes`/`set_keyframe_interpolation`/`remove_keyframe_range`. Read keys back with `prop.getKeys()` via `execute_extendscript` when the UI and API disagree. `set_keyframe_interpolation` only maps linear/hold/bezier; the ExtendScript enum for `prop.setInterpolationTypeAtKey(timeObj, mode, 1)` is 0=Linear, 1=EaseIn(obsolete), 2=EaseOut(obsolete), 3=Hold, 4=Bezier, 5=Time — on 26.3 the obsolete ease modes return success but SILENTLY WRITE LINEAR (verified 2026-07-17: linear keys confirmed in the UI). The Ease In/Out right-click presets are NOT reachable via scripting; to script an ease, BAKE it — one key per frame sampled off the easing function (e.g. `100 + 30*Math.pow(1-t,3)` for a decelerating landing), all keys linear; renders identical to the preset. Baking is THE standard method for scripted motion shapes (locked 2026-07-17): any curve works (GSAP-style eases, overshoot/settle, spring — shapes handles can't make), one ExtendScript call per clip, works on any numeric property. Trade-off: baked moves aren't hand-tweakable — adjust by re-baking from feedback; lay down 2-key bezier instead when the editor wants to sculpt the curve by hand. **The opening-zoom preset is a command:** `node lanes/premiere/premiere-bridge.mjs zoom '{"clip":0,"from":107,"to":100,"frames":10,"ease":"cubic","fps":"30000/1001"}'` (all opts optional; ease: cubic/overshoot/linear) — applies Transform + shutter 360 if missing, bakes, saves. Native .prfpset presets can NOT be applied via scripting — they're for hand editing only. Curve HANDLE geometry is also not readable/writable — hand-sculpted eases are invisible to scripting.
- **Adjustment layers: scripting can't CONSTRUCT one, but it can MINT one from the repo template (solved 2026-07-22).** No constructor exists anywhere in the scripting surface: QE has none (full `qe.project` method list reflected — only bars/black/matte/transparent/leader), the MCP's `add_adjustment_layer` and `export_as_project` are accepted-but-no-op stubs, and a hand-crafted FCP XML with `<mediaSource>AdjustmentLayer</mediaSource>` imports as an OFFLINE ghost (red Media-Offline slate) — the real serialization is an `<AdjustmentLayer>true</AdjustmentLayer>` flag, not a mediaSource. **The scripted route:** `app.project.importSequences("<repo>/lanes/premiere/premiere-templates/adjustment-layer.prproj", ["b2440d0d-b8dc-4899-adf9-40cf306269a6"])` — silent (no import dialog), returns true, and lands a working ONLINE "Adjustment Layer" item at project root plus a junk "adj-template" sequence (delete the sequence, keep the item; verified: places, takes effects, renders passthrough). **MINT IT AT THE SEQUENCE'S SIZE, always (2026-09-02): `uv run lanes/premiere/premiere-templates/mint-adjustment-layer.py <W>x<H>` prints a patched template plus the sequence UUID to import.** The donor's layer is a fixed 3840×2160, which covers any 16:9 timeline but is a latent trap on a VERTICAL one: with Premiere's media preference on "Set to frame size" a 16:9 layer scaled to fit 1080×1920 leaves the top and bottom ungraded, silently (the preference reads **None** on your machine, so the 4K layer would have covered — this is a portability fix and good practice, not a live bug). The script rewrites exactly one thing structurally, the `FrameRect` of the VideoStream reached by `MasterClip[IsAdjustmentLayer] → VideoClip → VideoMediaSource → Media → VideoStream`; it also re-UUIDs (uuid5 off the size, so re-minting is byte-identical and re-importing is idempotent) and renames item + junk sequence to `… <W>x<H>`, so a 1080×1920 layer cannot dedupe against a 3840×2160 one already in the project. ClassIDs are untouched and the ref graph stays whole (14 uuid defs = 14 refs, 132 int defs = 132 refs, zero dangling). Leave the stream's `FrameRate` alone: the media is `IsStill`/`IsContinuousTime`/`Infinite`, so there are no frames to conform — **size is the layer's only meaningful property**. Sized templates are gitignored (regenerable); the donor is tracked. Validated end to end 2026-09-02 on a 1080×1920 sequence: minted → imported → placed → Lumetri → Autumn Look, and an Exposure +2 control moved rows y0..y1919 and cols x0..x1079, i.e. edge-to-edge coverage. The template was built by placing a UI-born adjustment layer on a scratch sequence and calling `sequence.exportAsProject(path)` (the ES method works; the MCP tool of the same name is the stub). If the template is ever lost, rebuild it the same way from any project containing an adjustment layer — only the very first one ever needs the UI. Once the item exists: `overwriteClip` to place, trim via `c.end`, QE `addVideoEffect`, property writes in display units (read back to confirm). Its `inPoint` sits at ~3600s (infinite synthetic media), so clip keyframes go at `inPoint + offset` like any trimmed clip. Film-feel recipe validated on your-job: Lens Distortion (slight negative Curvature, Fill Alpha on) + VR Chromatic Aberrations (defaults ±10 are glitch-loud; start small) + a position random-walk wiggle on twos. **The wiggle MUST live on a Transform EFFECT, never intrinsic Motion (caught 2026-07-22): on an adjustment layer, Motion transforms only the layer's own bounds — visually a silent no-op — while the Transform effect warps the composite passing through (verify any such assumption with an exaggerated offset + frame grab before baking 500 keys).** Transform Position is normalized like Motion's; set Scale Height AND Width explicitly (uniform toggle untrusted) to ~101 to hide the shifted edges; QE track items include gaps, so walk `getItemAt(i)` for `type === \"Clip\"` — a head-trimmed layer's clip is NOT item 0.
- The MCP exposes 266 tools (track targeting, effects, markers, export, etc.). Run `get_project_info` to discover state when you need more than the basic handoff.
- Engine: `vendor/premiere-mcp` (pinned clone, see the bridge section above) → CEP/ExtendScript file bridge. Reinstall the panel by re-copying `vendor/premiere-mcp/cep-plugin/` to `~/Library/Application Support/Adobe/CEP/extensions/MCPBridgeCEP/` + restarting Premiere. The clone is gitignored (machine-local, like `.mcp.json`); restore = `git clone` + checkout the pinned hash + `npm install && npm run build`.
