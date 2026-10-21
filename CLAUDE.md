# CLAUDE.md — Video Editor

Your **video production & editing department** — and **only** that. Raw filmed footage comes in,
a finished exported cut goes out. This system is self-contained: you point it at a raw clip and it
takes that clip from **raw → fully edited → exported.** What happens to the export afterward
(posting, scheduling) is out of scope — this repo's job ends at the rendered file.

Not a traditional code repo — a content system where **Claude IS the editor.** Each stage runs
through a skill in `.claude/skills/`.

---

## 🪟 On Windows? One check first

This system runs natively on **macOS, Windows, and Linux** — no WSL, no virtual machine. On Windows
the `.sh` scripts run through **Git Bash** (installed with **Git for Windows**), which is the same
shell Claude Code itself uses on Windows.

**Figure out where you are** — run `uname -s` in the shell:
- `Darwin` (macOS) or `Linux` → you're set, skip to **FIRST RUN** below.
- `MINGW…` / `MSYS…` → **Windows with Git Bash working** — also set, skip to **FIRST RUN**.
- Command-not-found / PowerShell-looking output (`C:\…` paths) → **Git for Windows is missing.**
  Have the user run `winget install Git.Git` in PowerShell, restart Claude Code, and re-check
  before continuing.

> Windows notes: installs go through **winget** (`./check-setup.sh` prints the exact command per
> tool); after each install, open a new terminal and restart Claude Code once so PATH updates.
> Python on Windows is `python`, never `python3` (that name is a fake Microsoft Store stub — the
> pipeline scripts already handle it). Apple's hardware video encoder is a Mac-only speed perk;
> Windows/Linux render with software encoding (same result, a bit slower). An NVIDIA GPU is
> auto-detected and transcription runs on CUDA there (several times faster, automatic CPU fallback
> if the GPU path fails). Nothing else differs.

---

## 🚦 FIRST RUN — onboarding gate (read this before doing anything else)

**This is the first thing to handle when the project opens.** A SessionStart hook
(`.claude/hooks/setup-check.sh`) injects a reminder for as long as setup is incomplete. Trigger this
flow whenever the user says **"run the setup"** / **"set me up"** / **"continue setup"**, **or** asks
to edit/cut/process any video while the tools are not installed yet (an edit cannot run without
ffmpeg).

**Is setup done?** One deterministic check: the marker file **`.setup-complete`**, one line,
`lane=<premiere|resolve|capcut|chat-only|pending>` (`./setup.sh` writes it once every core tool
verifies, and fills in the lane):
- **Missing** ⇒ the tools are not verified yet. Run the full flow below.
- **Present, `lane=pending`** ⇒ the tools are done but the which-app question (step 2) is still
  open: several editing apps are installed. Ask it, then record the answer with
  `./setup.sh --lane <pick>`. The SessionStart hook keeps reminding you until this is settled.
- **Present with a real lane** ⇒ setup is done. The user just opening the project or asking for an
  edit ⇒ skip this gate and work normally. The user said **"continue setup"** (mid-flow, back from
  a restart) ⇒ don't redo step 1: re-run `./setup.sh` once (instant, it reports lane state), then
  verify the lane (step 2) and make step 3's one-line brand-kit offer.

That `lane=` line is also what every edit reads to know the finish surface (see The Pipeline).

**The goal: core editing working, fast, with near-zero effort from the user.** Personalization
(brand kit) is OPTIONAL and comes last. Never block editing on it: the presets ship with a neutral
bundled look (Inter fonts, a generic starter palette, no handles), so nothing of anyone else's brand
can leak into a video.

1. **Tools: run `./setup.sh` yourself.** Don't ask first (installing the tools is the whole point of
   this gate) and don't hand the user a command list; announce what it's doing as it goes. It
   auto-detects the OS (macOS → Homebrew, Windows → winget), installs every missing core tool,
   bootstraps the render engine (`npx hyperframes@0.8.16 browser ensure`, which downloads the
   headless browser; the npm and telemetry notices it prints are noise, and the version is pinned
   on purpose: never run `hyperframes upgrade`), verifies with `./check-setup.sh`, then probes for
   installed editing apps (step 2). It is **idempotent: re-run it after any interruption** and it
   picks up where it left off. Handle its exits:
   - **exit 0** with an `ACTION FOR CLAUDE` line in the output: several editing apps are installed.
     Go to step 2 (ask which one).
   - **exit 0** without one: done; `.setup-complete` says which lane. Go to step 3.
   - **exit 2:** this session cannot see something just installed: Windows tools after a winget
     install, or Homebrew's PATH on a Mac (setup.sh added it to the login profile itself). Walk the
     user through a Claude Code restart (see the restart walkthrough below), then re-run `./setup.sh`.
   - **exit 3:** it wired an editing-app lane into `.mcp.json`. Walk the user through a Claude Code
     restart, then verify the lane (step 2).
   - **exit 1:** something needs fixing first; read the output. Homebrew missing (macOS) → the user
     runs the printed one-liner themselves (it needs their password), then you re-run `./setup.sh`;
     it finds the new Homebrew in `/opt/homebrew` or `/usr/local` on its own and puts it on PATH, so
     never ask the user to do that. Tools still missing after the installs (a brew install that
     failed, or Linux, where nothing auto-installs) → `check-setup.sh` printed the exact brew/apt
     command per tool: run the brew ones yourself; apt needs sudo, so the user runs those. A lane
     installer failed → read its error, fix it, re-run `./setup.sh --lane <that app>`.
   Loop until `./check-setup.sh` shows every core item ✓. (Manual per-OS command list: `SETUP.md`.)
2. **Editing app lane: auto-detected, at most one question.** `setup.sh` probes for Premiere Pro,
   DaVinci Resolve, and CapCut, and records the outcome as the `lane=` line:
   - **One app found** → it already settled the lane: Premiere/Resolve ran their installer
     (`./setup-premiere.sh` / `./setup-resolve.sh`) and exited 3; CapCut needs no install (lane
     recorded, done, no restart). After a restart, verify the lane (below).
   - **Several apps found** → ask ONE line (e.g. "You've got Premiere, Resolve and CapCut: which one
     do you edit in?"), then run **`./setup.sh --lane <pick>`** yourself: `premiere` / `resolve`
     install that app's MCP lane and exit 3 (restart walkthrough + verify below); `capcut` and
     `chat-only` just record the answer. The pick is final: later `setup.sh` runs only note the
     other installed apps as available; never switch unless the user asks (then
     `./setup.sh --lane <other>` does it).
   - **No app found** → `lane=chat-only`. Say so in one line and move on; don't ask about apps, and
     never re-ask at edit time.
   **Verify a wired lane after the Claude Code restart.** First the MCP itself: its tools must be
   present in the session. If they are not, the project's `.mcp.json` servers were not approved:
   on reopening, Claude Code asks whether to enable them and the user must answer **yes**; a "no"
   is remembered across restarts, so the fix is `claude mcp reset-project-choices` (run it
   yourself), one more restart, and a yes. Then the app:
   **Premiere** → on macOS run `./lanes/premiere/premiere-up.sh` yourself (launches or relaunches
   Premiere; the patched panel starts the bridge with nothing to click) and confirm
   `node lanes/premiere/premiere-bridge.mjs ping` answers; on Windows have the user restart
   Premiere, then ping. Only if the ping fails, fall back to **Window → Extensions → MCP Bridge
   (CEP) → Start Bridge**.
   **Resolve** → ask the `davinci-resolve` MCP for the Resolve version (Resolve must be running; you
   can launch it). **Do NOT send Resolve users into Preferences up front**: External scripting =
   Local is Resolve's shipped default. Check that setting only as troubleshooting, if the
   connection still fails once the MCP approval above is confirmed.
3. **Brand kit: OPTIONAL. Offer once, never block.** Tell the user the editor already works with the
   neutral bundled look, and that whenever they want captions/graphics/thumbnails to sound and look
   like them, they can fill in `brand-kit.md` and say **"apply my brand kit"** (you then follow the
   exact file-by-file map in `brand-kit.md` Part B and render one quick test). Don't walk them
   through it during setup unless they ask for it.

**Restart walkthrough (both restart points; be exact and friendly):** tell the user: *"Quit Claude
Code completely (Cmd+Q on Mac / close the app on Windows), reopen it, open this same folder, and say
**continue setup**."* After an MCP was wired (exit 3), add: *"When it reopens and asks whether to
enable the MCP servers in this project, answer yes."* When the session resumes, pick up where the
flow stopped: re-run `./setup.sh` (it skips what's done) and continue. Never assume a restart loaded
anything; verify (`./check-setup.sh` for tools, a ping/version call for an MCP lane).

> **Face refs are optional** — they're only used for long-form YouTube *thumbnails*. When the user first
> asks for a thumbnail, have them drop 4–8 photos of their own face into `assets/face-refs/` (see that
> folder's README). Short-form-only creators never need them, so don't block onboarding on this.

---

## Brand Kit

The editor's voice and look come **entirely from [`brand-kit.md`](brand-kit.md)** and the presets it
feeds. Captions and on-thumbnail copy should sound like the creator described there; the signature
look is locked in [`presets/instagram/explainer/signature-style.md`](presets/instagram/explainer/signature-style.md). Apply those verbatim.

> Filling it in is OPTIONAL: the presets ship with a neutral bundled look (Inter fonts, a generic
> starter palette, no handles, no hook text), so editing works before any personalization and nothing
> of anyone else's brand can end up in a video. Offer the brand kit once after setup; apply it
> whenever the user asks.

---

## The Pipeline — one linear flow, every time

Every job runs the **same eight steps, in order**, raw → done — and the finish surface is an
editing app **by default**: a bare "rough cut" with no lane named means the lane setup recorded in
`.setup-complete` (`lane=premiere`, `resolve` or `capcut`; Premiere only when that line says so).
A machine setup recorded as `lane=chat-only` is already on the chat-only finish: never re-ask. On
a machine WITH an app, chat-only runs only on an explicit yes to "want this done straight in
chat?", never inferred from a job's content or premise.
**The eight steps below are the line for EVERY job on EVERY lane** — what
changes per lane is only WHERE a step happens (steps 4–7 run on the app timeline on an app finish,
and in the bundled render engine + ffmpeg on the chat-only lane). Format does **not** change the
flow either — it only changes how **Graphics (step 5)** behaves and whether the **Captions**
conditional pass runs at all. So don't "pick a workflow" up front. Run the line; branch only
inside that one step.

🔒 **At every step the route is the same two reads: the PRESET for WHAT (the target and the
numbers, which are the same in every editor), then [`LANES.md`](LANES.md) for HOW (the row for that
step names your app's status and points at the section in that app's skill).** That is what makes
one preset produce the same video whichever app you edit in. A step your app has no recipe for is
done by hand from the preset's numbers and **said out loud**, never done a different way in
silence, and never with another app's mechanics.

| # | Step | Skill | What happens |
|---|------|-------|--------------|
| 1 | **Intake** | _(copy)_ | Point to a raw file (often in `~/Downloads`). **Copy** it into `projects/<job>/raw/` — never move, never touch the original, so the source clip is safe if a render goes sideways. Name `<job>` after the content (see Job naming). |
| 2 | **Rough cut** | `rough-cut` | Always, every format. WhisperX large-v3 transcribe + word-align → kill filler/dead air (**the #1 filter: relevant ≠ necessary — good-to-know is fluff, only need-to-know-NOW survives**) → stitch (**frame-snapped cuts + J-cut audio crossfades** — see the splice quality note below) → **`polish-boundaries.py`** (peak-relative word edges, uniform tails) → **fresh-eyes second pass** (two subagents ONE TIER BELOW this session's model, `model` passed explicitly: script-flow + mechanical/slice-ASR, one pass before the cut ships) → **normalize audio with a STATIC chain (a MEASURED amplify from `workflows/voice-gain.py`, kept speech → −17 LUFS pre-limiter, → −6 dBFS hard limiter — NOT dynamic loudnorm, which pumps)** → **`audio-qa.py` self-check** (read its ⚠ lines). Produces the cut **and the finished script** (the kept-words transcript) — the source of truth for everything downstream. On an app finish this step runs `RENDER=0` and ends with the EDL replayed onto the app timeline. |
| 3 | **Audio polish** | _(in-app / baked by splice)_ | **Every job, immediately after the cut lands on its finish surface.** Premiere lane: ONE command, `uv run lanes/premiere/audio-polish.py projects/<job> --apply` (`--verify` reads it back): the gain is MEASURED by `workflows/voice-gain.py` (the raw's kept speech to −17 LUFS integrated before the limiter, so a quiet shoot gets more and a hot shoot less), the Hard Limiter is always −6 dBFS. The chain lands as clip audio effects on every A1 clip — Amplify (Left/Right `v=(dB+96)/144`) + Hard Limiter at −6 dBFS (`v=0.940`) via QE `addAudioEffect` + DOM property writes, **readback-verified**, ONE pass over the whole timeline; effects stay hand-tweakable, and **any timeline rebuild discards them — re-apply after every re-replay**. Then the house joint fade, ONE command: `uv run lanes/premiere/joint-fades.py projects/<job> --apply` puts a 2-frame (00:00:00:02) Constant Gain centred on every A1 joint that has no transition yet (never longer: a centred fade plays half its length past the cut, and 9 frames faded removed words back in), readback-verified; also re-applied after every re-replay. Resolve lane: `lanes/resolve/resolve-audio-polish/` (its API has no audio-FX surface). CapCut lane ⚠️: no audio-FX surface in the bridge — bake the chain into the SOURCE file with ffmpeg before `replay`, so the draft is built against polished media (`capcut` § Step 3, unvalidated). Chat-only lane: nothing to do — `splice.sh` already bakes the same chain into the render. Never per-section gain during the cut itself. Per-lane mechanics: [`LANES.md`](LANES.md) § step 3. |
| 4 | **Color grade** | _(in-app)_ | **Long-form, before graphics — and it lives UNDERNEATH them.** ONE adjustment layer spanning the whole timeline, on the track directly ABOVE the footage and BELOW the graphics (Premiere: V1 footage → **V2 grade** → V3 graphics), carrying a LUT plus a couple of colour dials. **On the Premiere lane that layer is one command — `node lanes/premiere/premiere-bridge.mjs grade-layer`, with your sequence active** — which provisions the tracks, builds the layer **at the frame size it reads off your sequence** (so a vertical project gets a vertical layer, never a 16:9 one scaled to fit with the top and bottom left ungraded), spans it across the footage, names it `GRADE` and adds Lumetri. Re-running it is safe. Then the look, one command with the project CLOSED while it writes: `uv run lanes/premiere/grade-lut.py apply projects/<job>/premiere/<job>.prproj` applies the locked house Look, Autumn-Rec709 at Look Intensity 70 and Creative > Adjustments > Saturation 115, everything else default; every trap lives in `lanes/premiere/premiere-grading.md`. There is NO colour-correction step: properly shot footage needs none, and a correction, if a clip ever needs one, is a manual call made before the Look. Footage-only is the requirement: the graphics already ship the exact colours the preset locks, and a grade over the top shifts all of them invisibly. **It runs BEFORE graphics for two reasons.** (1) That track is free at project setup; created afterward it means inserting a track *underneath* clips already placed, which Premiere does not do cleanly. (2) The graphics QA measures contrast and glow off program renders, so grading afterward invalidates every one of those measurements. **Clip transforms are unaffected** — zooms and push-ins are applied on the footage clip before the layer sees the composite. Resolve needs no track shuffle: a color group covers only its members, so the footage joins the group and the graphics track does not. Recipe: [`presets/youtube/default/README.md`](presets/youtube/default/README.md) § Grade. ✅ **A LOOK ships, and the whole step is automatic — you do nothing.** The library in [`assets/luts/`](assets/luts/README.md) carries 30 cubes (15 Rec709 + 15 LOG), and the house look **Autumn-Rec709** is captured and ready, so `grade-lut.py apply` replays it on job one with no setup. The captured params EMBED the cube, so the look travels with the package and works on your machine without you ever opening the LUT menu. **To use a DIFFERENT cube as your default,** it needs one hand-application, once, ever: apply it on a grade layer in Premiere (Lumetri → Creative → Look → Browse to the cube, set Look Intensity and Creative Saturation how you like them), save, then `uv run lanes/premiere/grade-lut.py capture <that>.prproj --slot look` writes a `<Name>.lookparams` beside it. From then on `apply <job>.prproj --lut <Name>` replays it on any job with the project CLOSED (reopen after); set `DEFAULT_LUT` at the top of that script to make it the default. That one hand step is unavoidable — Premiere's LUT menu is not reachable from a script and it validates a proprietary hash on the payload, so the settings have to be captured from a real application and replayed verbatim. `grade-lut.py luts` lists every cube and says which ones already replay. |
| 5 | **Graphics** | `graphics-plan` → `graphics-build` → `edit-review` | **Default = the BASIC tier: the format's own `default-overlay-style.md`** ([`presets/youtube/default/`](presets/youtube/default/default-overlay-style.md) long-form · [`presets/instagram/explainer/`](presets/instagram/explainer/default-overlay-style.md) short explainer; TikTok/raw stays hook-card-only): clean UI cards **over** the footage, 4–7 of them, the speaker's face never covered, ~30 min. Anything bigger (full-frame takeovers, bespoke art, another look) is opt-in **by name**, a request for "a graphics pass" never means the big version. On long-form the default also carries the **creative-moves vocabulary**, word-synced text animations, short punch cut-to-graphic beats, scene slides, vector props, emphasis push-ins, per `presets/youtube/default/creative-moves.md` (applied unprompted; extended takeovers still opt-in). Two sub-steps. **(a) Plan** (`graphics-plan`): beat sheet → footage probe → storyboard → self-review: reads the rough-cut transcript, maps the narrative arc + per-beat roles, grabs a frame per beat, then storyboards each graphic completely (template, exact copy, placement, timing, motion) and self-reviews before presenting. Writes `graphics-plan.{json,md}`. **(b) Create** (`graphics-build`): the build OWNER: harness, assets, comps per storyboard cell, browser probe, part renders, placement, first-pass QA. For the split-frame explainer preset, **measure the face crop first**, `uv run workflows/face-frame.py projects/<job>/outputs/<job>.mp4` prints the exact `#head` `object-position` (locked standard: median hair top 50 px below the y960 seam, measured, never guessed). The *content* diverges by format (below); the step doesn't. **(c) Converge** (`edit-review`): the automated defect loop, welded to this step and never deferred to your review: a deterministic gate first (`uv run workflows/graphics-qa.py projects/<job>` sweeps every frame of every render: band and edge, exits, cut alignment, holes, plan reconciliation, copy, registry conformance, grain, density, it must be green before any review round), then fresh-eyes subagent review rounds (two dimensions: copy/depiction and motion/rhythm) drive the draft to ZERO objective defects before you ever see it, defects only, never taste; stops on the first clean round, hard cap 3. **The mistakes the system can find, the system fixes, they never become your problem to review.** Deviations from the plan are recorded in `hf-graphics/qa-waivers.json`, never in prose. Review subagents run ONE TIER BELOW this session's model, with `model` passed explicitly. |
| 6 | **SFX** | `workflows/sfx-plan.py` → lane placer | Sound design synced to the graphics. The PRESET says what: `presets/youtube/default/sfx.md` + `sfx.json` (motion event → sound class → library slice → target peak, three SFX tracks by layer depth; every registry call, every text-animation word and every cut INTO a full-screen is an event; exits and cuts back to the face are silent). `uv run workflows/sfx-plan.py projects/<job>` reads the PLACED graphics and writes `hf-graphics/sfx-plan.{json,md}`, a reviewed cut sheet. Placement is per lane (`LANES.md` § step 6): Premiere `uv run lanes/premiere/place-sfx.py projects/<job> --apply` (readback-verified); other lanes hand-place from the cut sheet and say so. The library ships in full in `assets/sfx/`, so every file the map names is present; to use your own sounds, drop them in and point `sfx.json` at them — a missing file is a ⚠ in the cut sheet, never a silent skip. **It runs after graphics deliberately** — sounds are aligned to graphic beats, so a graphic retimed later orphans its sound; re-run the plan and re-place after any graphic moves. Before any re-place, `place-sfx.py --diff` reports the hand edits already on the timeline so they are kept, and a re-run is `--remove` then `--apply`. |
| 7 | **Review** | _(manual)_ | You watch and call adjustments — cut this graphic, swap that one, move it, redo. You are watching a draft that already has zero *objective* defects (5c caught those), so this pass is **taste**, and only taste. **Iterate incrementally:** re-render ONLY the changed part, never the whole video — the loop + stale tracking live in the `graphics-build` skill (chat-only recomposite mechanics: [`lanes/chat-only/incremental-graphics.md`](lanes/chat-only/incremental-graphics.md)). |
| 8 | **Export** | _(render → `finalize.sh`)_ | Render the final, then **finalize** so the folder is unambiguous: `./finalize.sh <job>` (dry-run; `--apply` to act) promotes the latest render to the **one** canonical deliverable **`projects/<job>/outputs/<job>.final.mp4`**, retires dead drafts, and **drops an export copy in `~/Downloads/`** (ready to grab/upload — `VE_EXPORT_DIR` overrides the target), while **keeping** the base cut (`<job>.mp4`), transcript, and `hf-graphics/` source so the job can be reopened. That's the finish line. Then `./prune.sh --apply` reclaims the regenerable cache. |

**Two CONDITIONAL passes hang off the line — they are not numbered steps because no job runs both.** Each has a fixed slot; run it there or say why it was skipped:

| Pass | When | Slot | What happens |
|---|---|---|---|
| **Captions** | short-form ONLY (long-form skips — YouTube serves its own CC) | after 5, before 6 (chat-only). **App lane:** no flat file exists at step 5, so the burn moves into step 8, between the app's export render and `finalize.sh` — see [`LANES.md`](LANES.md) § Captions; state the moved slot in RUN.md. | Explainer → the **LOCKED** centered preset ([`presets/instagram/explainer/captions-style.md`](presets/instagram/explainer/captions-style.md): Coolvetica white-on-black box, dead-centered on the seam, full-phrase box, words pop in on-beat). TikTok/raw → captions **low, under the face** ([`presets/tiktok/raw/tiktok-raw-style.md`](presets/tiktok/raw/tiktok-raw-style.md)). Both build from the canonical `outputs/<job>.transcript.json` — never re-transcribe. |
| **Background music** | opt-in, format-agnostic (most useful on short explainers; skip unless asked) | after 6, before 7 | `background-music` lays a **flat constant bed** by default (no ducking, no fade-in, −18 dB, short tail fade-out only). Ducking (sidechain + re-normalize to −14 LUFS) and fade-in are **opt-in**. Pure audio pass, video copied, no re-encode. Track lives in `projects/<job>/audio/`. |

**If you use a video editing app, that's the DEFAULT finish — assumed unless you explicitly choose
chat.** On an app finish, steps 4 through 7 happen on that app's timeline; on the chat-only lane
they happen in the bundled render engine (offered only when no editing app exists). After step 2,
hand the rough cut to the recorded lane's app: **Adobe Premiere Pro** via the `premiere-pro` skill,
**DaVinci Resolve** via `davinci-resolve`, or **CapCut** via `capcut` (the Premiere mechanics
follow; the other two are described right after), and do the editing there. It does
**not** import a flattened export — it **rebuilds the rough cut as separate, trimmable clips on the
timeline** by replaying the EDL (`transcript/cuts.json`) against the raw footage, so every cut is a
real edit point you can ripple/slip/slide. **On this path, run the splice as `RENDER=0 splice.sh
<job>`** — it refines + frame-snaps the cuts, persists the EDL and corrected transcript in seconds,
and never renders the flat MP4 (nothing on the Premiere path consumes it; transcription is the only
slow step allowed before the timeline). Then replay immediately:
`node lanes/premiere/premiere-bridge.mjs replay <cuts.json> <clipName>` (the headless bridge driver — no
MCP session needed). Claude can also work ON the timeline from there: graphics as alpha-ProRes
overlays and baked footage moves (the mechanics live in the `premiere-pro` skill), per-clip audio chains,
per-section label colors (set the project item's label BEFORE the replay — clips stamp it at insert),
and the final export via `exportAsMediaDirect` (renders inside Premiere — never queue Adobe Media
Encoder). One-time setup: `./setup-premiere.sh` — see SETUP.md (optional feature).

**The same, in CapCut** (macOS, needs the CapCut desktop app — no other install). CapCut has
no API, so `lanes/capcut/capcut-bridge.py` works two lanes. **File lane (build):** CapCut drafts are plain
JSON under `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/`, and
`uv run lanes/capcut/capcut-bridge.py replay <job>` writes a whole draft straight from
`transcript/cuts.json` — one trimmable timeline clip per cut, butt-joined to the EDL (run the splice
`RENDER=0`, same as the Premiere path). The rules that keep it working: **CapCut must be fully quit
while the bridge writes** (on exit it rewrites the shared draft registry and clobbers new entries);
raw footage is **hardlinked into the draft's `Resources/`** automatically, because CapCut's sandbox can
only read `~/Movies` (outside paths open as red "File not accessible" clips); to file-edit a draft
CapCut has already opened once, the bridge deletes the draft's `Timelines/` native cache so the JSON is
re-imported (otherwise edits are silently ignored); and once the user has **hand-edited a draft in the
app, only add to it** (`add-overlay` / `add-text` / `graphics <draft> <job>` / `transform`) — never
re-run `replay` over it, which would wipe those hand edits. Alpha ProRes graphics composite with true
transparency on overlay tracks; text tracks are native. **Live lane (interactive):** with the editor
open, the bridge drives the real UI through the macOS accessibility tree — `open`, `seek`, `select`,
`split`, `delete`, `undo`, markers, `save`, plus `shot` for QA screenshots — so small edits need no
quit/relaunch. **`export` finishes the job inside CapCut**: it drives CapCut's own export dialog and
verifies the file that lands (1080p mp4 into `~/Downloads` by default). Two export rules: CapCut's
post-export "share to TikTok/YouTube" screen is modal and blocks the next export (the bridge clears
it, and you should never click through it — it publishes), and a segment carrying a null
`source_timerange` wedges the encoder mid-render, so the bridge repairs those before every write.
Run `uv run lanes/capcut/capcut-bridge.py` with no args for the full command list.

**The same, in DaVinci Resolve** (macOS, Windows, or Linux; Studio recommended). One-time install:
`./setup-resolve.sh` wires the `davinci-resolve` MCP, which drives Resolve's **official scripting
API** (no bridge panel; Resolve just has to be running). The
`davinci-resolve` skill carries the whole lane: the EDL replay is **one call**
(`media_pool create_timeline_from_clips` rebuilds `transcript/cuts.json` as separate trimmable
clips, linked audio included; run the splice `RENDER=0`, same as the other app lanes), and from
there Claude can work the timeline through the API: silence-ripple auto cuts (`edit_engine`), AI
subtitles + transcript-based cut proposals, Fusion node graphs, custom DCTL color shaders, in-app
Python, vision-based clip metadata, and native in-Resolve renders. The skill also carries the
hard-won traps: never `timeline apply_cuts` (it deletes whole clips while reporting success);
match the project frame rate to the SOURCE footage by importing a template `.drp` from
`lanes/resolve/resolve-templates/` rather than `create_project` + `set_setting` (the Playback frame
rate is a separate setting the API cannot write, and a mismatch plays chopped audio — mint new
rates with `mint-template.py`, then read both fps keys back before building); and vertical 9:16
fill is one property write (`Scaling = 3`), not zoom math. Two later stages have their own
measured playbooks: delivery renders follow
[`lanes/resolve/resolve-export.md`](lanes/resolve/resolve-export.md) (`VideoQuality` is a dropdown index,
not a bitrate; `MultiPassEncode` is the only real quality lever; verify with ffprobe on the
finished file), and the final audio pass follows
[`lanes/resolve/resolve-audio-polish/`](lanes/resolve/resolve-audio-polish/README.md) (measure each source
file with `ebur128`, static gain to −16 LUFS, −1 dBFS limiter, then `ReplaceClip` the normalized
copies under the locked timeline; run it only after the edit is locked).

**Second entry path: long-form → clips (`clipper`).** The pipeline above runs raw → one video; the
`clipper` skill runs the reverse: a FINISHED long-form in, a batch of 9:16 captioned clips out.
Transcribe the published file once, select self-contained hook-and-payoff moments into a reviewed
`clips-plan.json`, then `uv run .claude/skills/clipper/scripts/make-clips.py projects/<parent>
--build` runs each approved clip through the locked engine (rough-cut splice → face-centered 9:16
reframe → TikTok/raw captions → `.final.mp4` + a `~/Downloads/` export copy). Each clip is a
standard job folder under `projects/<parent>/clips/<name>/`, so every skill here works on it.

### Format variants — only step 5 and the Captions pass change

**Format is AUTO-DETECTED from the raw footage, never asked.** Probe the clips: **vertical**
(height > width) → short-form; **horizontal** → long-form YouTube. Mixed folder → the clips carrying
the substance decide (the main dialogue/talking takes; b-roll and inserts don't vote). Explainer vs
TikTok/raw is inferred from content (teaching/system walkthroughs cut like explainers; casual
talk-to-camera stays raw). State the detected format in the report so the creator can override with
a word; ask only if the footage is genuinely undecidable. Same rule for intent: the hook + takeaway
are read out of the transcript (or sampled frames on a visual-only edit), stated for correction,
never requested up front.

| | **Short · Explainer** | **Short · TikTok/raw** | **Long-form** |
|---|---|---|---|
| **Where** | Reels · TikTok · Shorts | Reels · TikTok · Shorts | YouTube |
| **Aspect** | 9:16 · 1080×1920 | 9:16 · 1080×1920 | 16:9 · 1920×1080 (no reframe) |
| **Graphics (5)** — *full tier* | top-half graphics, face bottom — full plan | **front hook card only** (`presets/tiktok/raw/tiktok-raw-style.md`), then raw | liquid-glass panels + takeover/zoom (`presets/youtube/liquid-glass/liquid-glass-style.md`), or the print-collage look (`presets/youtube/vox-collage/vox-collage-style.md`) |
| **Graphics (5)** — *default* | *overlay cards, top half* | *unchanged — hook card only* | *overlay cards, callout zone* → each format uses its OWN preset's `default-overlay-style.md` (`presets/youtube/default/` long-form · `presets/instagram/explainer/` short explainer; TikTok/raw = hook card only) unless a bigger pass is asked for by name |
| **Captions** (conditional pass) | centered — **locked** (`presets/instagram/explainer/captions-style.md`) | low, under face — **locked** (`presets/tiktok/raw/tiktok-raw-style.md`) | none |

The 9:16 reframe (short-form) happens at the top of Graphics. Safe zones + layout live in each
preset's own style doc — read the preset you're on before building graphics. Long-form has no
platform safe bands: never cover the speaker's face or important on-screen content, keep copy off
the very edge of the frame, and leave the outro's right side + bottom clear for end-screen cards.

**Short-form safe zones (always, never break):** no key visuals in the **top 200 px** or **bottom
300 px** — the face, captions, and every key graphic stay inside y `200 → 1620`. Those two bands are
background/filler only (platform UI + device chrome sit there).

## Skills

- **`edit-video`** — **the orchestrator: the whole line, end to end.** "Edit this video" / "do the whole
  edit" routes here. It owns the ORDER, the STATE and the GATES only; each step's how-to stays in its
  own skill or preset. It keeps **`projects/<job>/RUN.md`**, rewritten at every step boundary, so a run
  survives a context compaction and can be picked up cold — its first act on any job is to read that
  file rather than assume a fresh start. It enforces that a step is finished before the next begins,
  and that a step which cannot run is **announced as skipped, never passed over in silence**.
- **Core editing:** `rough-cut`, `graphics-plan` (gated by its `validate-plan.py`), `graphics-build`
  (gated by `workflows/graphics-qa.py`; placement via `lanes/premiere/place-graphics.py`), `edit-review`
  (the step-5c polish loop: the gate, then two-dimension subagent review rounds → verified defects →
  part-by-part fixes, until the first clean round), the locked caption presets (`presets/instagram/explainer/captions-style.md`,
  `presets/tiktok/raw/tiktok-raw-style.md` + their `build.py`), `background-music`
- **Out of the pipeline (on request only):** `thumbnail-generator`. A thumbnail is a publishing
  asset, not an edit, and this system finishes at the exported file — so no step calls it and a
  job is complete without one. Ask for a thumbnail by name and it still runs.
- **`premiere-pro`** — the recommended finish if you edit in Premiere: rebuilds the cut as **individual
  trimmable timeline clips** by replaying the EDL against the raw footage, then lets Claude keep
  working on the timeline (graphics overlays, audio effect chains, section label colors, frame-grab
  QA, direct in-Premiere export). Drives the MCP Bridge panel headlessly via
  `lanes/premiere/premiere-bridge.mjs`. One-time install: `./setup-premiere.sh` — see SETUP.md.
- **`davinci-resolve`**: the same finish in DaVinci Resolve, through Resolve's official scripting
  API (no bridge panel needed): one-call EDL replay into separate trimmable clips, then
  silence-ripple cuts, Fusion graphs, DCTL shaders, in-app Python, vision metadata, and native
  renders. The skill lists what's verified AND which API calls are broken or destructive. One-time
  install: `./setup-resolve.sh` (see SETUP.md).
- **`clipper`**: the reverse entry path, a finished long-form in, short-form clips out.
  Selection-first (a reviewed `clips-plan.json` + cut sheet before anything renders), then
  `make-clips.py --build` reuses the locked engine per clip: rough-cut splice, face-centered 9:16
  reframe, TikTok/raw captions, deliverable + Downloads export copy.
- **HyperFrames suite (engine):** `hyperframes` (+ `-core`, `-cli`, `-animation`, `-creative`,
  `-registry`, `-keyframes`) and `media-use` — the HTML-based video toolkit that renders graphics & captions.
- **HyperFrames task workflows (advanced/optional):** `faceless-explainer`, `general-video`,
  `talking-head-recut`, `motion-graphics`, `pr-to-video`, `product-launch-video`,
  `remotion-to-hyperframes`, `slideshow`. These are vendored extras for one-off
  builds; the everyday pipeline above doesn't need them. (For short-form captions always use the
  locked presets in the Captions pass.)

### HyperFrames video-authoring toolkit (vendored)

A general HTML-based video toolkit from `heygen-com/hyperframes`, pinned in `skills-lock.json`. It's
the creation engine for **Graphics (step 5b)** and the **Captions** pass. The render CLI runs via
**`npx hyperframes`** (auto-downloads on a machine with `node`) — `./setup.sh` bootstraps it once
(`npx hyperframes@0.8.16 browser ensure`, which fetches the headless browser). **Update via the skills registry, not by
hand-editing** — `skills-lock.json` tracks hashes.

## Folder Structure

The project root **is** the editing workspace — job folders live directly in `projects/`.

| Path | What's In It |
|------|--------------|
| `.claude/skills/` | The editing skills + the vendored HyperFrames toolkit |
| `lanes/` | Everything app-specific, one folder per editing app (`premiere/`, `resolve/`, `capcut/`, `chat-only/`): bridge and launch scripts, project templates, lane sheets, and a `lab-notes.md` of that app's own gotchas. `workflows/` holds only the universal utilities. `LANES.md` says, per pipeline step, which app has a scripted recipe and where it lives. |
| `projects/<job>/RUN.md` | **The run's state file**, written by `edit-video` at every step boundary: format, lane, preset, per-step status, what each step produced, and everything skipped with its reason. The first thing to read on a job already in progress. |
| `projects/<job>/` | One folder per content piece: raw clips in `raw/`, audio/music in `audio/`, source assets in `assets/`, B-roll in `broll/`, thumbnails in `thumbnails/`, finals in `outputs/`. The HyperFrames graphics build lives **durably** in `hf-graphics/` (`compositions/` + `render.sh` + a `PROJECT.md` resume doc, plus `build.py`/`parts.json` only on a split-part build — never delete this; it's the real progress). Only the **regenerable** cache (`renders/`, base slices, font copies) is disposable. **Nothing lives solely in `/tmp`** — it's volatile on every platform (macOS clears it; Windows/Linux temp dirs get cleared too) and it wiped a whole build once. `prune.sh` reclaims the cache when a job ships. |
| `finalize.sh` | The **export** step (step 8). `./finalize.sh <job>` promotes the latest render to the one canonical `outputs/<job>.final.mp4`, retires drafts, and **copies the deliverable to `~/Downloads/`** (the "export"), keeping the base cut + transcript + `hf-graphics/` source for re-editing. Dry-run by default; `--apply` to act. |
| `prune.sh` | Reclaims space in `projects/` (dry-run by default; `--apply` to delete). |
| [`LANES.md`](LANES.md) | **The routing index: one row per pipeline step, one column per app (Premiere · Resolve · CapCut · chat-only), each cell saying scripted / manual / unvalidated / gap and pointing at the recipe.** Read the row for the step you are on before doing any app-specific work. The presets carry the numbers, the app skills carry the mechanics, and this file is what keeps a job in one app from running another app's recipe. |
| `assets/` | Shared generation assets — `face-refs/` (your face, for thumbnails), `fonts/`, `logos/`, YT thumbnail templates, `sfx/` (the SFX library for step 6, shipped in full — see its README), `luts/` (30 cubes plus the captured house look, Autumn-Rec709, that step 4 applies), `models/` (the face-detection model). **Personalize:** drop your own face refs + logos here (see each folder's README). |
| `brand-kit.md` | The one file you fill in — your identity, voice, colors, fonts, hook style. |
| `skills-lock.json` | Pins the vendored HyperFrames skills (source + hash). |
| `check-setup.sh` | Report-only check of the system tools the editing skills need (ffmpeg, etc.). |

**Job naming:** name `<job>` after the video's content — a short kebab-case title (e.g.
`my-first-video`, `cold-dm-teardown`), **never** the camera file (`C1840.MP4`), a date, or a stage suffix.

## Rules

- **One job: edit the best video possible.** Raw → fully edited → exported. No business/CTA logic
  lives here — captions and end screens carry no sales asks.
- **Surgical changes only.** Touch what's asked. Don't "improve" adjacent renders or refactor
  working skills.
- **Update HyperFrames via the registry,** not by hand — `skills-lock.json` tracks hashes.
- **Document, don't manufacture.** Authenticity outperforms.
- **Motion craft is the VOX craft layer, not a global one.** [`presets/youtube/vox-collage/motion-craft.md`](presets/youtube/vox-collage/motion-craft.md) belongs to the vox print-collage look — read it ONLY when that look is invoked by name, never for a default graphics pass. Default-tier craft lives inside each preset's own style doc.
- **Repeated line across takes → use the LAST take.** Don't ask.
- **Captions run the whole video by default** — never suppress them under a hook or graphic unless told.

## Lab Notes — how the locked presets work

These are engineering notes from the original build of this system — the *why* behind the locked
presets, so you can extend them without re-discovering the gotchas. Any job names that appear are
worked examples from that build.

- **Transcribe ONCE per video.** WhisperX large-v3 is the single transcription for the whole pipeline
  (most accurate, so it's the source of truth). `rough-cut` persists it to
  `projects/<job>/transcript/words.json` and reuses forever (`--force` to redo). Finishing/captions do
  NOT re-transcribe: `splice.sh` derives `outputs/<job>.transcript.json` by remapping kept words
  through `cuts.json` (pure arithmetic). **Spelling/brand fixes are applied right there** — as it
  writes the canonical transcript, `export-transcript.py` runs `transcript-corrections.json` over
  it, so the fix reaches graphics-plan AND both caption formats AND long-form (the raw `words.json`
  stays untouched). The locked caption builders read that already-corrected canonical
  `outputs/<job>.transcript.json` directly. The WhisperX venv builds once and is reused across jobs.
- **Splice quality = frame-snapped cuts + J-cut crossfades + a self-check (do not simplify these away).**
  Three audio-artifact mechanisms were found the hard way and are fixed at root in `splice.sh`:
  (1) every cut boundary **snaps to the video frame grid** — un-snapped fractional cuts give each
  segment a video duration up to ±1 frame different from its audio, and ffmpeg's `concat` pads the
  difference with digital-silence gaps at joints (audible room-tone dropouts + a progressive timeline
  stretch that desyncs captions/graphics). Snapped, the rendered timeline equals `transcript/cuts.json`
  exactly, so everything downstream anchors to EDL times directly. (2) joints are **equal-power
  crossfades over real continuing room tone** (each segment's audio runs 15 ms past its video cut),
  never butt-splices (they click on any non-zero crossing) and never fades-to-zero (those punch audible
  ambience holes). Timing stays exact by construction. A per-joint `"xfade": <seconds>` override in
  `cuts.json` widens the ramp into a segment whose cut-in clips an in-progress word attack (acoustic
  onsets often start tens of ms before the word timestamp). (3) the limiter runs with `latency=1`
  (its lookahead otherwise delays audio ~5 ms vs video). After every splice, **`audio-qa.py`** verifies
  joints, ambience continuity, timeline integrity, and limiter pressure — if it warns about limiter
  pressure, the footage is peakier than the measured gain assumes: `AMPLIFY_DB=<n>` is the manual
  override (the gain is normally measured per shoot by `workflows/voice-gain.py`). Two more mechanisms are fixed at cut time: (4) **cut boundaries are MEASURED, not
  trusted** — WhisperX word starts run ~50–100 ms late vs the real acoustic attack (and ends run
  early), so `refine-cuts.py` runs inside `splice.sh` before every cut: it measures each chosen word's
  acoustic edge on a 5 ms RMS envelope of the raw and moves the cut just outside it (onset − 40 ms /
  offset + 50 ms, clamped to never cross an adjacent word). Cut CHOICE stays Claude's; `REFINE=0` or
  `"no_refine": true` skips it. (5) **merged repeats** — WhisperX collapses an immediately repeated
  word ("However… However") into ONE entry spanning every utterance, hiding the stutter from the
  transcript. `transcribe.sh` flags long-span words (>1.0 s); the refiner burst-scans them — a segment
  STARTING on one snaps to the last utterance (prefer-last-take), one ENDING on one trims to the first,
  and a mid-segment one gets a ⚠ (author a split around it). (6) **joints are resolved PAIRWISE:
  segments may never overlap in the source.** A continuous split (one unbroken take carved into
  separate timeline clips) must share ONE boundary time; padded outward on both sides, the same
  source frames get laid down twice and play as a 1–15 frame stutter, invisible to every
  per-segment check (each segment is individually perfect, only the pair is wrong).
  `refine-cuts.py` detects continuous splits from transcript adjacency and merges each overlap to
  a single shared boundary (a `no_refine`-pinned side is never moved; the unpinned side joins it),
  and `splice.sh` hard-aborts post-snap on any overlap that survives, naming the segment numbers.
  Refinement is NOT idempotent (it measures from the authored cut), so repair an EDL that was
  already refined or shipped with `refine-cuts.py --repair-only` (joint resolution only, zero
  re-measurement), never a second full pass.
- **Premiere-path jobs never render the flat cut.** When the finish surface is Premiere, run
  `RENDER=0 splice.sh <job>` — refine + frame-snap + persist the EDL + corrected canonical transcript
  in seconds, no ffmpeg encode. `audio-qa.py` is render-dependent and skipped; level-check in Premiere
  instead (`workflows/voice-gain.py` measures the raw's kept speech and prints the Amplify dB). The metric is time-to-timeline: transcription is the only
  slow step allowed.
- **Explainer captions = LOCKED preset.** Standard burn-in for talking-head explainers lives in
  [`presets/instagram/explainer/captions-style.md`](presets/instagram/explainer/captions-style.md) + builder
  [`presets/instagram/explainer/build.py`](presets/instagram/explainer/build.py). Coolvetica Regular 49px, white on a
  solid-black box, dead-centered on the frame seam (y960), box pre-sized to the full phrase, words pop
  in per-word on their own WhisperX timestamp (on-beat karaoke). **The timing lock:** build captions
  ONLY from the canonical `outputs/<job>.transcript.json` and overlay onto the render that ships —
  same timeline → on-beat with zero manual nudging. Brand mishears are already fixed upstream by
  [`transcript-corrections.json`](transcript-corrections.json) (applied to the canonical
  transcript at splice time — see the transcribe-once note above), so captions inherit them.
- **TikTok/raw = LOCKED preset.** Hook card + line captions live in
  [`presets/tiktok/raw/tiktok-raw-style.md`](presets/tiktok/raw/tiktok-raw-style.md) + builder
  [`presets/tiktok/raw/build.py`](presets/tiktok/raw/build.py). Hook card = Inter Bold 64px
  black-on-white-box, sized to the ink extents (not font metrics), pinned top (y250), shown only over
  the spoken hook (auto-ends on a configured trigger word or `--hook-end`); captions = Inter Bold
  42px white + 4px black stroke, no box, no animation, line-by-line, low under the face (y1500).
  **Captions are ALWAYS ON** the whole video — the hook card overlays on top, never replaces them.
  Engine = PIL PNG overlays + ffmpeg `overlay` enable-timing (this ffmpeg has no freetype/libass, so
  PIL is the house pattern). Deliverable = `outputs/<job>.final.mp4` (keep `outputs/<job>.mp4` as the
  clean base the builder reads from — don't overwrite, or you'll caption an already-captioned video).
  **Gotcha:** the `-loop 1` PNG overlay inputs never EOF, so the output MUST be bounded with `-t`
  (source duration) — the builder always passes it.
- **Explainer face framing = LOCKED: hair top 50 px below the seam, measured not guessed.** Before
  building split-frame explainer graphics, run
  `uv run workflows/face-frame.py projects/<job>/outputs/<job>.mp4`. It samples ~12 frames of the base
  cut, detects the face (OpenCV YuNet — model bundled at `assets/models/`), finds the true hair top via
  median-background subtraction (works even with dark hair on a dark room), and prints the exact
  `object-position` for the `#head` cover-crop → also written to `projects/<job>/face-frame.json`. If
  the source is still 16:9 it prints the face-centered ffmpeg crop for the 9:16 reframe too. Fallback
  when hair can't be measured (hat/hood): face-box center → y1385. After the draft render,
  `uv run workflows/face-frame.py --verify <render>` must print ✓ PASS before review. First run
  auto-installs the OpenCV dependency via `uv` (one time, needs internet).
- **One comp per graphic; a `build.py` emitter is for split-part builds only.** The default card pass is hand-authored comps, one per graphic, rendered by the preset's `reference/fullscreen-render.sh` copied into the job as `render.sh`. An emitter is for a long multi-scene graphic that ships as short seamless parts from ONE shared timeline (`emit(..., t0=<offset>)`), so the seam frame is identical by construction and a tweak re-renders only its part. Recipe and the GSAP negative-offset gotcha: the `graphics-build` skill.
- **Incremental graphics = render PART-BY-PART, composite with ffmpeg.** The second-pass tweak loop
  doesn't re-render the whole video per change. Full doc:
  [`lanes/chat-only/incremental-graphics.md`](lanes/chat-only/incremental-graphics.md). A parts-oriented `build.py`
  emits one composition PER graphic + `render-part.sh <id>` + `assemble.sh`. Two part kinds: **overlay**
  (floats over footage → render standalone as a transparent `.mov` via `--format mov`) and **segment**
  (modifies the footage itself → render opaque `.mp4` carrying its own base slice). `assemble.sh` is
  ONE ffmpeg pass chaining base + each part with `-itsoffset` + `overlay=enable='between(...)'`. Loop =
  edit `build.py` → render only the changed part (~30–50s) → assemble (~5s) → review. The base rough cut
  is NEVER re-rendered. Render every part at the base fps (e.g. `--fps 24000/1001` for 23.976) or frames
  drift through ffmpeg. The win is modest on a short reel but compounds hard on long-form.
- **Render cut drift — SOLVED by the frame-snapped splice.** With snapping on, the rendered timeline
  equals `transcript/cuts.json` to the millisecond, so graphics/zooms anchor to EDL times directly.
  Only for a base rendered by an OLD un-snapped splice do you still verify cut times with ffmpeg
  `scdet` before anchoring to them.
- **`prune.sh`** reclaims space in `projects/` — deletes only regenerable dead weight (HyperFrames
  `work-*` render scratch, stray `node_modules`, intermediate renders; keeps `*final*`/`*graphics*` +
  highest `-vN`). Never touches source `raw/*.mp4` or `outputs/`. Dry-run by default; `--apply` to
  delete. The space hog is raw footage + leftover render scratch.
