# Install, edit, and export checks

These checks are the definition of a first edit for this starter. They are **manual on a Mac with Premiere**. The unit tests in `packaging/tests/` cover the packager (exclusions, secrets, the version pin, missing files, manifest checksums). They do not install Premiere and they do not pass this list.

Grading, SFX, and Coolvetica captions are **not** acceptance items. The assets are withheld, and the 26.3.2 grade recipe is unverified on any other build.

## Install

1. Unpack the local zip. Read `START-HERE.md`.
2. Confirm `VERSION` contains `distribution=not-released` and `pinned_commit=7557eeeedab3dd444effa27474cbaad23ace997e`.
3. Confirm `SHA256SUMS` matches the files (the packager tests this; repeat it if you want a second check).
4. Install tools from `PREREQUISITES.md`.
5. `./check-setup.sh` shows the core tools present.
6. `./setup.sh` then `./setup-premiere.sh` on macOS.
7. `node lanes/premiere/premiere-bridge.mjs ping` connects. Record the Premiere version.
8. If that version is not 26.3.2, write that the grade is unverified. Do not run LUT apply and call it accepted. The cubes are not in the archive.

## Edit

1. Generate the synthetic sample (`SAMPLE.md`) or use a newly recorded non-client clip.
2. Create a local job folder and copy the clip into `raw/`. Do not import someone else's project.
3. Replay `packaging/sample/synthetic-cuts.json` (or an EDL for the self-recorded clip) with the Premiere bridge replay command so the timeline has separate source clips, not one flattened file.
4. Optional and not required: `uv run lanes/premiere/audio-polish.py` and `joint-fades.py` on that local job. A failure here blocks the smoke record; it does not justify swapping in another editor.

The personal day-number preset is not part of this edit.

## Export

1. Export from Premiere itself with `exportAsMediaDirect` (the premiere skill's step 8). Do not use a queued external encoder for this check.
2. `ffprobe` the file. It needs a video stream and a duration greater than zero.
3. Leave the export on the machine. Do not upload it as a sample of this starter.

## Record

Fill `packaging/gates/MAC-SMOKE.md` only when install, edit, and export above have been done on the Mac. Then run the checker. `packaging/delivery/ship.sh` must still refuse. No download is recorded from this repository's tooling.
