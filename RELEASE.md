# Release notes — Claude Video Editor client package

The top section is the current build. `packaging/package-for-client.sh` stamps its version into
the zip as `VERSION` and copies this file in; `packaging/delivery/ship.sh` publishes it to the
download page. Add a new `## <version>` section at the top for every ship; version = the ship
date, `.2`, `.3` suffix for a second ship the same day. Bullets are client-facing: what changed
for them, in their words, no internal job names.

## 2026.09.03.2

- THE ONE-SHOT EDIT: say "edit this video" once and the first draft that comes back is finished, every step run, every objective defect already caught and fixed. Everything below is what makes that hold
- One command runs the whole line: intake, rough cut, audio polish, colour grade, graphics, sound design, review, export. The run keeps a RUN.md per job, so it survives a long session and picks up cold exactly where it stopped, and a step that cannot run on your editing app is announced, never skipped in silence
- Rough cut: every cut boundary is measured on the audio instead of trusted from the transcript (peak-relative word edges, uniform tails, no clipped word starts, no roomy ends), then a fresh-eyes second pass by two independent reviewers checks script flow and slice accuracy before the cut ships
- Audio polish: the gain is measured per shoot (your kept speech to −17 LUFS before the limiter, a quiet shoot gets more, a hot shoot less), then the −6 dB limiter. One command on the Premiere timeline, read back to verify
- Colour grade, step 4: automatic. One command puts the house look on an adjustment layer under the graphics before a single graphic is placed, so the graphics keep their exact colours. The LUT library ships in the package
- Graphics, the default long-form pass now carries the full creative-moves vocabulary without being asked: word-synced text animations, short punch cut-to-graphic beats, scene slides, vector props, emphasis push-ins, at a locked cadence of 11 to 13 graphic events per minute with no bare stretch over 6 seconds
- Graphics, the rules that make it look right every time: every entrance and exit comes from one animation registry (shipped as code, not prose), overlays sit in the measured low band under your chin, accent props glow, anything meant to be read holds still for 2 to 3 seconds, reveals come in bursts instead of a linear wipe, arrowheads are computed from their path, cards name things and scenes enact them
- Graphics plan gate: the storyboard is validated before anything renders (word anchors, cut edges, readable holds, density), so a bad plan never costs a render
- Graphics QA gate: a deterministic sweep of every frame of every render (face and band breaks, exits, cut alignment, holes, copy versus plan, registry conformance, grain, density) must be green before review starts; then two-dimension review rounds (copy and depiction, motion and rhythm) converge to zero objective defects. You only ever watch for taste
- Sound design, step 6: every graphic beat gets a sound from the preset map, placed on three SFX tracks and verified on the Premiere timeline in one command; hand edits on the timeline are detected and kept on a re-place. The full SFX library (151 clips) ships in the package
- The two locked full-screen background fields ship pre-rendered, so the first job skips two 90-second renders

- SETUP AND MISC, starting here. Setup is one sentence: open the folder in Claude Code and say "run the setup". It installs the tools, fetches the render engine's browser, detects your editing app and records your lane; at most one question (which app, only if several are installed) and at most two restarts
- Fresh Mac: after you install Homebrew, setup finds it and puts it on your PATH itself. Fresh Linux: setup prints the apt commands for the missing tools instead of asking for a restart in a loop
- CapCut counts as an editing app in the which-app question, and the lane you picked is remembered for every edit
- After an editing-app lane is wired, the docs tell you to answer yes to the Claude Code prompt that enables the project's MCP servers, and Claude knows the fix if it was declined
- Premiere lane ships the engine build the system was validated on (v1.2.3), with its usage telemetry switched off
- Native Windows: every tool runs through `uv run`, status output is UTF-8 safe, and Mac-only helpers say so instead of failing silently
- Package is 84 MB smaller (a duplicate background render no longer ships)
