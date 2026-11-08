# Install, edit, and export checks

The real acceptance is a same-footage, same-prompt comparison on a Mac, recorded in `gates/MAC-SMOKE.md`. It is not the synthetic color-bar plumbing check, and it is not a Linux unit test. Open rows in `gates/parity-blockers.json` mean the result is not parity.

Packaging tests cover exclusions, secrets, the version pin, provenance hashes, missing files, manifest checksums, and the dry-run defaults on the reviewed tools. They do not install Premiere and they do not pass the list below.

House grading, the SFX library, and Coolvetica captions are open parity blockers, not waived items. Those binaries are withheld, and a packaging smoke that never grades, scores, or sets Coolvetica does not close them. The 26.3.2 grade notes are unverified on 25.6.2. `gates/parity-blockers.json` stays the list.

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
4. The plumbing replay above is not the series edit. Audio polish, 2-frame joint fades, per-source level match, captions, the series preset, grade, SFX, and Coolvetica remain required for parity and stay blocked until the Mac gate and the asset rows say otherwise.

## Export

1. Export from Premiere itself with `exportAsMediaDirect` (the premiere skill's step 8). Do not use a queued external encoder for this check.
2. `ffprobe` the file. A video stream and a duration greater than zero only prove the plumbing export. Parity still needs the preset's frame size, frame rate, loudness, and true peak, measured on the Mac.
3. Leave the export on the machine. Do not upload it.

## Record

Fill `packaging/gates/MAC-SMOKE.md` only when install, edit, and export above have been done on the Mac. Then run the checker. `packaging/delivery/ship.sh` must still refuse. No download is recorded from this repository's tooling.
