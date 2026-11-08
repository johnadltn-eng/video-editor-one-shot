# Premiere on Mac — starter

Read this before `SETUP.md` or `CLAUDE.md`. Those files describe the full editor. This archive is a smaller, review-only starter.

## What this is

A local package for a first edit that finishes in **Adobe Premiere Pro on macOS**. The editor source matches commit `7557eeeedab3dd444effa27474cbaad23ace997e`. Packaging docs may be newer. `VERSION` inside the zip says `distribution=not-released`.

Linux tests of the packager do **not** certify this Mac path. Do not treat a green test run as a finished install.

## What this is not

- Not a published download and not a release.
- Not a certification of Premiere grading. The grading notes were measured on **Premiere 26.3.2**. A bridge ping that reports another build, including **25.6.2**, does not prove adjustment-layer grading or LUT replay. The CinePacks LUT library is not in this starter. Leave `grade_lut_replay_verified` false.
- Not parity with Resolve, CapCut, Windows, Linux, or the chat-only finish. `setup.sh` and `setup-premiere.sh` still contain branches for other hosts. Ignore those branches for this starter.
- Not the personal day-number series. `presets/road-to-20k/` is omitted on purpose. A first edit does not need it.
- Not a bundle of client footage, face photos, logos, or old job folders. `projects/` is not in the archive.

## First edit, minimal path

1. Read `packaging/PREREQUISITES.md` and install the listed tools. On a fresh Mac, Homebrew is the one step that needs a password; `./setup.sh` can install the rest.
2. Run `./setup.sh`, then `./setup-premiere.sh`. Restart the coding agent when the scripts say to, and accept the project MCP prompt if it appears.
3. Confirm the bridge with `node lanes/premiere/premiere-bridge.mjs ping`. Write down the Premiere version it reports.
4. Create footage with `packaging/sample/make-synthetic-sample.sh`, or record a new non-client clip. See `packaging/SAMPLE.md`.
5. Replay that clip onto a Premiere timeline and export it. The checks are `packaging/ACCEPTANCE.md`.
6. Fill the Mac smoke record in `packaging/gates/MAC-SMOKE.md` only after those steps succeed on the Mac. `packaging/delivery/ship.sh` still refuses to publish.

`brand-kit.md` is optional and ships with placeholders. `.mcp.json.example` in this archive is a portable placeholder. The real `.mcp.json` is written on the Mac by setup and must stay uncommitted.

## Assets you will not find

Inter and TikTok Sans are included with their SIL Open Font License files. Coolvetica, Playfair Display, DM Serif Display, Instrument Serif, the LUT cubes, the SFX library, and the face-detection model are not included. Steps in `CLAUDE.md` that depend on them cannot be completed from this starter. That is a license hold, not a missing download.

## Manual gate before any download or setup record

Do not record this starter as installed or downloadable until `packaging/gates/MAC-SMOKE.md` passes on a Mac. A record that claims multi-editor parity, a published download, or a verified LUT grade is invalid.
