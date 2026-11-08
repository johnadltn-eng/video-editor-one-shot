# Full editor archive — read this first

This zip is a review archive of the full source editor plus reviewed local tools. It is not a reduced starter, and it is not proof that a clean machine matches an existing install.

`VERSION` says `distribution=not-released`. Linux tests of the packager do not certify macOS or Premiere.

## What is in the archive

The pinned editor at `7557eeeedab3dd444effa27474cbaad23ace997e`: setup, Premiere and Resolve installers, bridges, presets, skills, and workflows. Series tools that were reviewed separately are included under `presets/road-to-20k/`. Read `packaging/PARITY.md` for the ledger.

Other modes (Resolve, CapCut, chat-only, music, clipper) are present as source. Only say a mode works where that mode's own notes and a Mac or app test say so. The working-install bridge report used for planning was Premiere 25.6.2. Grading docs were measured on 26.3.2. This archive does not re-prove either.

## What will refuse to run

- `grade.py`, `place.py`, `level_match.py`, `punch_ins.py`, `fx_segments.py`, and `media_fix.py` do not change a project or move an original unless you pass `--apply`. Moving a job-local raw file also needs `--move-original`.
- `packaging/assets/check_required_assets.py` exits 2 because the LUT library, SFX clips, and Coolvetica are not cleared to ship.
- `packaging/delivery/ship.sh` always refuses to publish.

## Before anyone records a download or a finished setup

Run `packaging/gates/MAC-SMOKE.md` on a Mac, on new footage, with the same prompt as the comparison install. Open blockers in `packaging/gates/parity-blockers.json` mean the result is not parity, even if the bridge ping succeeds.
