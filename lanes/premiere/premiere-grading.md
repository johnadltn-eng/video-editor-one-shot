# Premiere grading lane — pipeline step 4 mechanics

**HOW, not WHAT.** The look, the numbers and the reason the grade runs before graphics live in the
preset ([`presets/youtube/default/README.md`](../../presets/youtube/default/README.md) § Grade). This
file is only how Premiere gets there. The Resolve counterpart is
[`resolve-grading/`](../resolve/resolve-grading/README.md); which lanes have a recipe at all is
[`LANES.md`](../../LANES.md).

Read this before any grading work on the Premiere lane. Everything below was measured on Premiere
26.3.2; several of the traps produce a file that opens fine and renders nothing, so the verification
discipline at the end is not optional.

## The lane, end to end

Four steps. Two of them are one command each.

### 1. The layer — ONE command (2026-09-02)

```bash
node lanes/premiere/premiere-bridge.mjs grade-layer
```

With the job's sequence active. No UI, no arguments, nothing to type. It mints an adjustment layer
**at the frame size it reads off the sequence**, imports it, provisions tracks up to the V1/V2/V3/V4
map, lays ONE instance on **V2** spanning V1's full extent, names the clip `GRADE`, adds Lumetri via
QE (`apply_effect` is broken on 26.3), reports any track whose output is off, and saves. Opts if a
job ever needs them: `{"track":2,"minTracks":4,"lumetri":true}`.

It is idempotent in both directions: it refuses if that track already holds a `GRADE` clip, and it
reuses a same-size layer already in the project rather than stacking duplicate bin items. **The size
is READ, never typed** — that is the entire reason the command exists. The donor template is a fixed
3840×2160, which covers any 16:9 timeline but on a VERTICAL one can be scaled to fit and leave the
top and bottom ungraded, silently.

Under it: `uv run lanes/premiere/premiere-templates/mint-adjustment-layer.py <W>x<H>` prints a sized
template plus the sequence UUID for `importSequences` (full story, and why scripting cannot simply
construct a layer: the `premiere-pro` skill Notes). Minting a size twice is byte-identical, so
re-importing is idempotent. Reach for the script directly only when building a layer outside the
active sequence.

**Retrofitting the track onto a timeline that already has graphics is one call, not a re-lay.** QE
`addTracks(1, 1, 0, 0, 0, 0, 0)` INSERTS a video track at index 1, so everything on the old V2
shifts up to V3 with every effect, keyframe and trim intact (verified 2026-09-01: 25 graphics clips
moved, none touched). Never move graphics by re-`overwriteClip`-ing them — that rebuilds from the
project item and drops their clip effects.

### 2. The Look, hands-off — three commands

```bash
./lanes/premiere/premiere-up.sh --quit                                    # saves through the bridge, graceful app.quit(), waits
uv run lanes/premiere/grade-lut.py apply projects/<job>/premiere/<job>.prproj
./lanes/premiere/premiere-up.sh projects/<job>/premiere/<job>.prproj      # relaunch, bridge back
```

Copy the `.prproj` first. That replays the default (Autumn); `--lut <Name>` replays any other
captured cube under `assets/luts`, and `grade-lut.py luts` lists what is there and what replays. No
hand step, and no dials from the pipeline: whatever was dialed when the params were captured comes
back with them.

The project must be SAVED with the fresh Lumetri before the quit, or the on-disk file has no Lumetri
to write into (`apply` then exits "Lumetri #0 not found"); `--quit` saves it. Quitting Premiere
rather than closing just the project costs nothing extra: with no project open Premiere drops the CEP
panel, so the bridge dies either way and the relaunch is what restores it. **Run end to end
2026-09-02 on a full job copy:** quit → write → relaunch → on/off frame delta 62, one command each,
no clicks.

**Write into a COPY, cold-open the copy, swap only once it is proven (the order 2026-09-02 ended
with, now the documented one).** A refused open on the job's own path is a modal on the user's screen
and a wedged bridge; on a copy it is just a file that did not open.

```bash
cp projects/<job>/premiere/<job>.prproj projects/<job>/premiere/archive/<job>.pre-lut.prproj   # the backup, always
cp projects/<job>/premiere/<job>.prproj projects/<job>/premiere/<job>.graded.prproj             # the working copy
uv run lanes/premiere/grade-lut.py apply projects/<job>/premiere/<job>.graded.prproj               # selfcheck runs first
./lanes/premiere/premiere-up.sh projects/<job>/premiere/<job>.graded.prproj                         # cold-open THE COPY
node lanes/premiere/premiere-bridge.mjs frame ...   # on/off frame delta with the GRADE layer toggled: must move
./lanes/premiere/premiere-up.sh --quit
mv projects/<job>/premiere/<job>.graded.prproj projects/<job>/premiere/<job>.prproj              # swap only now
./lanes/premiere/premiere-up.sh projects/<job>/premiere/<job>.prproj
```

☠️ **The hard gate after a refused open: no second open of anything until the modal is provably
gone.** Premiere queues every open behind the alert; on 2026-09-02 five more opens were issued after
the first refusal, and by the fifth Premiere would not quit by any means (Cmd+Q, AppleEvent, the
bridge). One failed open is data, five is a wedge. The check and the fix are one script:
`./lanes/premiere/premiere-dismiss.sh --check` (exit 2 = a `UI_MessageBox::RunModal` frame is on the
stack, which is the only signal that survives a locked screen) and `./lanes/premiere/premiere-dismiss.sh`
(posts Return straight to the pid until the frame is gone). Only when it reports zero, and
`./workflows/window-grab.sh --list Adobe` shows no alert-sized window, may the next open be issued.
A native alert does not wait for a human to click OK; it waits for that Return.

`strip --slot look` removes it; `capture --slot look` re-mints the params file from a project where
the LUT was applied by hand. Verified **pixel-identical** to a hand-applied grade (max channel delta
0), and the numeric Lumetri dials still work live on top of it afterwards.

**Trying a different cube is one hand step, then scripted forever.** Apply it by hand on a scratch
project's GRADE Lumetri (Creative > Look > Browse > the cube under `assets/luts/`, set the dials),
save, then `grade-lut.py capture <scratch>.prproj --slot look` writes `<Name>.lookparams` next to the
cube, and `apply --lut <Name>` replays it on any job forever. The default never moves unless
`DEFAULT_LUT` does. ⚠️ The browsed path is baked into the hashed payloads, so browse from
`assets/luts`, never from a Downloads copy (the first Autumn capture carried the Downloads path and
had to be re-applied from the repo path; only the two path payloads changed). `capture` also writes
the verified fresh-instance component struct rather than the donor's, and warns when they differ —
see THE FIFTH PIECE below for why that matters.

**A params file is proven before it is trusted: `grade-lut.py selfcheck` (2026-09-02).** It checks
every shipped `.lookparams`/`.lutparams` offline, with no Premiere: each arb pid is an open/close
`<StartKeyframeValue>` (never self-closing, the damaged-project signature), each BinaryHash length
word equals payload + 12, pid 4 decodes to the empty sentinel in the look slot, pid 98 is an `ITX3`
block whose float32 data matches the `.cube` beside it to 1e-5 (so the params provably belong to
that LUT), the dials are numeric, the component struct is the 128-byte `tmul`, and the file's sha256
matches `assets/luts/README.md` § Checksums (drift warns; an unnoticed re-mint is the failure it
exists for). `capture` runs it on what it just wrote and `apply` runs it before writing and REFUSES a
failing file, so "apply printed success and Premiere said damaged" cannot recur from a bad params
file. `selfcheck --lut <Name>` or `selfcheck <file>` checks one.

### 3. Check track output BEFORE measuring anything

☠️ **A muted track makes every grade test read ZERO and looks exactly like a dead effect
(2026-09-02).** Premiere's **Toggle Track Output** (the eyeball on the track header) removes the
whole track from the composite, so with V2 output off the adjustment layer contributes nothing:
disabling the GRADE clip, pushing `Exposure` +2 and pulling Creative `Saturation` to 0 all returned
**max channel delta 0** on a real job — the exact signature of a poisoned Lumetri, with nothing wrong
at all.

The Exposure control does NOT distinguish the two cases, because a muted track kills it too. It is
`videoTracks[i].isMuted()` / `setMute(0|1)` in ExtendScript, so read every track's mute state before
measuring anything and restore whatever the creator had set afterwards (they mute the grade and
graphics tracks to look at raw footage). The tell that the harness itself is fine: change something
on **V1** (Motion `Scale` to 50) — if that moves the frame, grabs are live and the silence is
upstream.

### 4. Verify from a program render, never from a readback

Grab one frame with the layer disabled and one enabled (the bridge `frame` command) and confirm the
footage moved and the graphics track did not. On the Autumn Look a bare-footage frame moves mean RGB
`105.86/87.59/90.69` → `99.2/83.5/85.2` (max channel delta 59), and on another job at 2.0s
`105.1/86.4/89.4` → `102.1/83.0/84.8` (delta 61). The absolutes differ per frame; the tell is a
channel delta in the tens. If it reads 0, either the LUT silently did not land or the track's output
is off (step 3). On a fresh project step 4 runs before any graphic exists, so the graphics half of
that check happens at the first placement instead.

⚠️ The **opposite** stack exists — V4 adjustment layers over everything, per-section Lumetri,
film-feel effects — and it is the vox-era architecture. As of 2026-08-31 it lives only inside its own
preset ([`presets/youtube/vox-collage/premiere-lane.md`](../../presets/youtube/vox-collage/premiere-lane.md)),
opt-in by name, so no shared lane doc can teach a default job the wrong stack any more. Do not read
it on a `youtube/default` job.

## Why the LUT needs a file write at all

**The LUT is NOT reachable through the scripting API.** Lumetri exposes 130 ExtendScript properties
and **six of them look like the LUT** — `Input LUT` twice as an enum, two unnamed string slots ahead
of it, plus `LUTAsset` and `LookAsset`. Every one **accepts a write and reads the value straight
back** (the enum stores whatever index you hand it; the string slots store the full `.cube` path) and
**the render never changes by a single pixel** — swept indices 0-10 against program-monitor grabs,
before AND after installing the LUT into `~/Library/Application Support/Adobe/Common/LUTs/Input/` and
restarting Premiere: all eleven frames byte-identical.

☠️ **The MCP's own `apply_lut` tool is a MEASURED no-op that reports success** (tested 2026-09-02,
not inferred). Its source adds a Lumetri then does `setValue(<path string>)` on the property named
`Input LUT` — an ENUM, so the string is silently coerced. After a `success: true, "LUT applied"`
response the readback shows `p6 Input LUT = 0`, `p7 Input LUT = 0` and every LUT/Look param empty,
and the rendered frame is unchanged (max channel delta 1 against the before frame, which is just a
second default Lumetri in the chain; a real Autumn application moves the mean ~9 points). The handler
also swallows every exception, so it can never report failure.

☠️ **And it is not merely inert on a grade layer, it is UNSAFE there:** it writes into
`clip.components[numItems - 1]`, assuming the Lumetri it just added is the last component. Upstream
issue #63 (*"Multiple Lumetri instances cannot be safely targeted; apply_effect can destroy masks"*)
proves Premiere inserts a second Lumetri in the MIDDLE, so on a clip that ALREADY carries one — which
every GRADE layer does — the write lands in the existing instance and resets it. That issue is closed,
but the `lastComp` pattern is still in the source in three places and has not been touched since July.
The clean-clip test above only passed that axis by accident (a fresh layer's components really are
Opacity/Motion/Lumetri). **Treat `apply_lut` as a trap, never a route.**

Also dead: project-file surgery through the ES host (Premiere regenerates the mirror params on load;
a heavier patch hung the host), and master-clip colour management (`projectItem.setOverrideColorSpace`
is real, and its list is a PROPERTY not a method, but it holds only 32 camera/display colour spaces,
never a `.cube`).

**The numeric dials ARE scriptable** — `Exposure` (param 19) at +2.0 moved a frame from mean RGB
105.9/87.6/90.7 to 151.6/131.8/135.0 — so the split is exactly: dials scripted, LUT by file write.

### Look slot, never Input LUT

Lumetri's chain inside one instance is `Input LUT -> Basic Correction dials -> Creative Look`. A LUT
applied as **Creative > Look** renders AFTER the correction dials, which means correction and LUT fit
in ONE Lumetri and the panel shows both. Applied as **Basic Correction > Input LUT** it renders
BEFORE the dials, which forces a second Lumetri instance in front of it for any balance pass, and
that layout hides the LUT from the panel (a layer was reset once and the LUT survived on the instance
nobody could see). Both slots capture and replay the same way; only the param ids differ (`SLOTS` in
the tool). Byte-identical strip+apply regression passes on both.

Params files sit beside their cubes under `assets/luts/rec709/`: `Autumn-Rec709.lookparams` (look
slot, THE house look) and `London-Rec709.lutparams` (input slot, retired example). The `.lookparams`
also holds a numeric snapshot of every Lumetri dial (105 of them), which is how Intensity 70 and
Saturation 115 come back on a fresh job. ⚠️ **The Blob does NOT carry dials:** it read Intensity 100
while the panel rendered 70, and Premiere trusts the mirror params on load, so a blob-only capture
silently replays the LUT at defaults. Verified by resetting a copy to factory values (renders
identical to raw) and replaying (identical to the dialed frame, delta 0). Re-run `capture --slot look`
on a saved project if the preset ever changes.

## The five pieces a LUT is made of

The LUT is spread across four serialized Lumetri params plus one struct on the component itself, all
of which must be present:

| pid | ES prop | What |
|---|---|---|
| 1 | 0 | `Blob` — a plain-text `<Lumetri>` XML shader stack, **UTF-8**, whose `LUT` shader holds `<__Embed>"1"</__Embed>` + `<LUT>"<full path>"</LUT>` |
| 4 | 4 | the `.cube` path, **UTF-16LE**, NUL-terminated |
| 5 | 6 | the `Input LUT` enum — **0** for a browsed custom LUT (Adobe's bundled LUT presets use 1) |
| **98** | **122** | **`Embedded LUTs` — the whole cube, parsed into binary.** This is the one that matters and the one that is easy to miss. |

For the **look slot** the path is pid 24 (ES 32) and the enum pid 25 (ES 34); Blob and `Embedded
LUTs` are the same. Found by diffing a Look-applied save against a fresh Lumetri: exactly pids 1, 24,
98 changed, enum 25 stayed 0. The blob carries it as a `__Preset` entry in the Creative group instead
of the `LUT` shader.

`Embedded LUTs` is an `ITX3` blob: 16-byte hash · `uint32` length · `'ITX3'` · `uint32` size (33) ·
`uint32` channels (3) · 4×`float32` domain-min · 3×`float32` domain-max · then `size³ × 3` `float32`
RGB triplets in `.cube` order. That structure was confirmed by regenerating it from the `.cube` and
diffing against Premiere's own output: **byte-for-byte identical except the leading 16-byte hash**. So
the payload is fully derivable — only the hash is not, which is exactly what forces capture-and-replay.

### ☠️ THE FIFTH PIECE — the component's own `PremiereFilterPrivateData`

**The cause of every "project appears to be damaged" on 2026-09-01.** Besides its 130 params, the
`VideoFilterComponent` carries a 128-byte `tmul` struct of its own. Applying a LUT by hand flips word
24 in it from 0 to 257 ("LUT present"), and Premiere also rewrites the Input-LUT path param (pid 4) as
an explicit sentinel instead of a self-closing tag. A write that sets the params but leaves that
struct in its fresh state produces a file that parses as valid XML, passes every element-level
comparison, and Premiere refuses on open.

Five corruptions in one afternoon, each "explained" by a theory (duplicate ObjectIDs, internal flags,
an Auto press on the target, a project-bound guid, a warm cache) that fit the data by coincidence,
because every write that opened had inherited an already-flipped struct from an earlier hand apply on
that same instance, and every write into a truly fresh Lumetri failed. Found by having the same Look
hand-applied on the exact fresh base and diffing Premiere's save against the tool's byte for byte:
the struct and pid 4 were the only substantive differences.

`grade-lut.py` now captures `component_pfpd` and writes it (and refuses a params file that lacks it).
Verified: the tool's write on the fresh base differs from Premiere's own only in panel-expansion UI
state, change counters and timestamps, and it cold-opens with nothing else loaded.

> **Method lock: when a surgically written project is refused, the diff to run is Premiere's own save
> of the same edit on the same base, not another theory.** Do not open more test copies on the
> creator's screen.

The struct is LUT- and slot-independent (byte-identical across the Autumn Look and the London
Input-LUT captures) but it DOES carry instance history: re-capturing Autumn from a scratch Lumetri
that had LUTs removed and re-applied a few times came back with word 10 = 1 on top of word 24 = 257.
The pipeline replays into a fresh instance, so `capture` always writes the verified fresh-instance
struct (`PFPD_FRESH_LUT` in the tool, the one `proof.prproj` cold-opened with) and warns when the
donor's differed; a donor struct with history on a fresh target is an unverified combination, which
is exactly the class of write that produced the damaged files.

⚠️ **VERSION-BOUND.** The captured params were minted on Premiere 26.3.2 and nothing checks the
running version. If an update changes the component struct's layout, `apply` still reports success and
the project still opens while the grade renders NOTHING — the same silent signature as a poisoned
Lumetri or a muted track. On a new Premiere build, if a frame grab with the layer toggled does not
move, suspect `PFPD_FRESH_LUT` first and re-mint by hand-applying + `capture` on that build.

## The traps that make a write look like it worked

☠️ **OBJECT IDs ARE NOT UNIQUE IN A `.prproj`, AND THAT WILL CORRUPT A PROJECT SILENTLY.** One real
project has **60 duplicated ObjectIDs** across different ClassIDs, so `ObjectID="3320"` can match two
completely unrelated elements. The first cut of this tool looked params up by ID alone and spliced
whole `<…ComponentParam>` containers in — it wrote into the wrong element, produced a file that
**parsed as perfectly valid XML with zero dangling ObjectRefs**, and Premiere refused it with *"The
project appears to be damaged, it cannot be opened"* (which also wedges the scripting bridge behind a
modal until a human clicks OK). Two rules came out of it, both now enforced: `obj_body()`
**disambiguates every lookup by `ParameterID`**, and `put_payload()` transplants **only the
`<StartKeyframeValue>`**, never the container (which carries ClassID/Version/KeyframeSetSize belonging
to that project). `integrity()` refuses to write if the ObjectID/ObjectRef sets or the component count
change. **The regression test is a byte-compare:** `strip` then `apply` on a copy must reproduce the
file exactly — it does, on both Lumetri instances. **Never run this on a job project without a copy of
the `.prproj` beside it**; it cost one real corruption, recovered only because a backup existed.

⚠️ **An EMPTY arb param is written self-closing** (`<StartKeyframeValue …/>`), a populated one as an
open/close pair. A regex that only matches the pair fails on a freshly-added Lumetri — which is
exactly the state you apply a LUT into. Match both forms.

☠️ **`BinaryHash` is VALIDATED, and a wrong one is discarded SILENTLY.** Every
`<StartKeyframeValue>` carries `BinaryHash="<96-bit digest>-<uint32 len+12>"`. The low 32 bits are the
payload length + 12 (confirmed on 8 of 8 samples). The **96-bit half is a proprietary digest** — not
MD5/SHA1/SHA256 in any truncation or byte order (tested against 14 real pairs), and a second sweep the
same day found nothing either: 20 pairs × 14 input framings (raw, the base64 text with and without
whitespace, UTF-16, length-prefixed and length-suffixed variants) against MD5, SHA-1/2/3, SHAKE,
BLAKE2, RIPEMD, MD4, xxHash 32/64/3/128, MurmurHash3 32/128, CityHash, FarmHash, SpookyHash,
MetroHash, SipHash and the CRC32/Adler/FNV/djb2 words, in straight, reversed and GUID-mixed byte
order, plus a constant-XOR salt test; the ITX3 blob's own 16-byte lead is none of those over the cube
file or the blob body either. **Do not spend another session on it.** Write a payload with a stale,
zeroed, or absent hash and Premiere throws the value away without a word: the effect loads, the UI
even shows `[Custom]`, and nothing renders. That is why the params are **captured and replayed
verbatim** rather than synthesized, and why a new LUT needs one hand-application to mint its
`.lookparams`.

☠️ **Do NOT write the Blob param through ExtendScript. It POISONS the Lumetri instance.** The write
succeeds and reads back byte-perfect, and from that moment the effect renders **nothing at all — not
even `Exposure`**. It reads exactly like "the LUT didn't take" when the whole effect is dead, so every
later test on that clip is a false negative. (ES also writes strings as UTF-16, where the blob must be
UTF-8.) Recovery is to delete the clip and re-place it with a fresh Lumetri.

⚠️ The Exposure control is necessary but NOT sufficient: a muted track silences `Exposure` too, so a
dead control means "poisoned effect OR muted track" — read the mute state first (lane step 3).
**Always re-run a control — `Exposure` +2 must move mean RGB ~46 points — before trusting any negative
result in this area.** That single check is what separates a real finding from an hour of chasing a
corpse.

⚠️ **On a project holding more than one Lumetri, `grade-lut.py` needs the right `--which N`.**
Instances are indexed across the WHOLE file, so resolve the index by walking the component to its
MasterClip name rather than guessing.

## Portability — the params travel, the path is a label

**A `.lookparams` captured on one machine replays on any other, and `apply` never reads the cube**
(measured 2026-09-02). pid 98 `Embedded LUTs` carries the entire cube (575 KB of base64 for a 33³) and
the Blob's `__Preset` path sits next to `__Embed "1"`: Premiere renders from the EMBEDDED copy and
never opens the file. Proof: `assets/luts/` renamed away, no other copy of the cube anywhere on the
machine (`mdfind` clean), Premiere fully quit and cold-opened — the graded frame came back
**pixel-identical, max channel delta 0**. So a client can be shipped a turnkey grade with NO
hand-application step.

☠️ **But Premiere RE-RESOLVES the LUT on save and DROPS the embed.** A project written by `apply`
carries the cube embedded and renders from it with no file on disk; the NEXT Premiere save rewrites
that instance as a LINK to the baked path and empties pid 98 (measured: the same project shrank by
exactly one payload, 575 KB, across one save). On the capture machine the path resolves so nothing
breaks and the swap is invisible; anywhere else it is a dangling reference as soon as the user saves.
The params are hash-sealed so the path cannot be rewritten — the fix is to make the path TRUE, which
is why captures are taken from `/Users/Shared/` (no username, present on every Mac) and why
`setup-premiere.sh` mirrors the cube library there on a client's first run. ⚠️ NOT YET MEASURED:
whether Premiere keeps the embed when the path does NOT resolve. It probably does, since that is what
embedding is for, but assume nothing — the mirror makes it moot.

☠️ **A hand-apply does not always EMBED the cube.** Browsed from `/Users/Shared/` Premiere LINKED it
(pid 98 empty) while the same cube browsed from inside the repo embedded normally, and the Blob says
`__Embed "1"` in BOTH cases, so the blob cannot tell you which happened — check pid 98, or let
`capture` fail on its own guard ("donor has no embedded LUT in the look slot"). **A link is not a dead
end and needs no second hand-apply: pid 98 is a property of the CUBE, not of where it was browsed
from**, so a valid Premiere-authored pid 98 for the same cube grafts in from any earlier capture.
Autumn's shipping params are that graft (clean path params from a fresh apply + pid 98 from the
previous one) and replay byte-perfect.

☠️ **The path CANNOT be removed, redirected, or looked up dynamically, and stripping it was
measured.** It lives inside pid 1 the Blob (as `__Preset`, beside `__Embed "1"`) and again in pid 24,
both hash-sealed, and **the Blob is STRUCTURALLY REQUIRED** — it is the shader stack that tells
Lumetri to run a LUT shader at all. Applying pids 4 + 98 + enum + dials while omitting the Blob and
the path param renders the frame at `51.99/58.82/64.98` against `52.91/58.88/64.68` ungraded (delta
30, which is the dials alone) versus `44.22/54.56/59.39` with the Blob: the embedded cube in pid 98 is
inert without the Blob to invoke it. So the capture-time path rides along forever, whatever it says.
The ONLY lever is WHERE the cube is browsed from when the params are minted.

## Adjacent traps found in the same sessions

- **The Blob's format is documented by Adobe, in Adobe's own file.** `Lumetri Presets.prfpset` is
  plain text and its six bundled input-LUT presets give the exact recipe (blob carrying a BARE
  FILENAME + param 4 path + enum 1; all six use enum 1 with different LUTs, so the enum only means
  "a LUT is selected"). Read it before theorising about the format.
- **The preset-application path has no scripting entry point.** `applyPreset` / `attachPreset` /
  `importPresets` exist on nothing — probed `app`, `app.project`, `qe.project`, `TrackItem`, the QE
  clip and the component. The Blob is an OUTPUT of Lumetri's serializer, consumed only by that path.
- **`remove_effect_by_name` addresses the wrong clip.** It reported `removed:true, changed:false,
  "already absent"` on a clip that visibly still had Lumetri. Strip effects by deleting and
  re-placing the clip instead.
- **Premiere refuses AppleEvents on this machine** (`osascript … to quit` returns `-600 Application
  isn't running` while the process is up), which is why `premiere-up.sh --restart` never actually
  quits. The working graceful quit is ES `app.quit()` through the bridge: ~60-90s, and it drops the
  windows well before the process exits. ⚠️ Its pid wait had its own bug (2026-09-02): `pgrep -f
  <app path>` also matches `crashpad_handler` and `AdobeIPCBroker`, which OUTLIVE the quit, so a
  quit that had worked was reported as "did NOT take". The check is `pgrep -x` on the exact process
  name now.
- **`Auto` cannot be pressed by script, but its result can be READ.** There is no auto-tone method on
  any object and no `executeCommand`/`executeMenuCommand` surface in Premiere's ExtendScript (unlike
  After Effects), and writing `SemanticAutoTone Progress` or `Auto Tone Analytics Data` triggers no
  recompute. But `Auto Tone Analytics Data` (ES prop 126) is a live JSON RECORD of what Auto last
  computed, and every dial it drives is a normal scriptable param — so a press can be read back and
  re-applied at any intensity (applied dials = recorded values scaled by the Auto **Intensity**
  slider; at 50 exactly half, Saturation scaling toward its 100 neutral). ⚠️ That record is only
  meaningful when Auto was pressed on a footage CLIP. On an adjustment layer it records a blank-media
  constant — see the preset's § There is no colour-correction step.

## Verification discipline, in one list

Three different failures in this area all present as "the grade does nothing", and none of them is
distinguishable from a readback:

1. **Muted track** — read `videoTracks[i].isMuted()` FIRST. Confirm grabs are live by moving
   something on V1.
2. **Poisoned Lumetri** (a Blob written through ES) — `Exposure` +2 fails to move the frame on an
   unmuted track. Recovery is delete and re-place the clip.
3. **Discarded payload** (stale `BinaryHash`, missing pid 98, missing PFPD struct) — the project opens,
   the UI may show `[Custom]`, the frame does not move.

So: never trust a readback, never trust the effect panel, and never trust a negative result until the
Exposure control has been re-run on a track you have confirmed is unmuted. Verify only from a program
render with the layer toggled.

## There is no correction step, and Auto on the layer is noise (2026-09-01)

The preset's rule is that the grade is the layer plus the Look and nothing measures or corrects
the footage first; this is where the evidence behind it lives. A measured "auto-correct" solver was
built and deleted the same day. It was calibrated against reference frames that were each the wrong
thing: a finished timeline with a LUT baked in (so the "correction" was a look in disguise), a
textbook skin target (shipped a frame the user called "orange as fuck"), and finally Premiere's Auto
pressed on the ADJUSTMENT LAYER. **Auto on an adjustment layer does not look at the footage.**
Pressed on two different clips, different lighting and colour, it returned byte-identical values to
four decimals (Temperature −29.199, Tint 15.43, Highlights −50.73). The layer has no pixels of its
own, so it analyses its own blank synthetic media (a cached analysis is the only other reading that
fits). Press Auto on a footage clip if you ever want its opinion (on real footage it moved nothing
worth keeping); on the layer it is noise.

Two measurement lessons worth keeping if this is ever revisited: never gray-world a lit set (the
full-frame average is skin and set dressing, and on a two-source room "neutral" is a judgement
call, not math), and choose the measurement pixel mask ONCE on the uncorrected frame, or the
selection drifts under the correction and the response reads as non-physical.
