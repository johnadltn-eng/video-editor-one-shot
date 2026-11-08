# Starter packaging

This directory builds a **local review archive** of a Premiere-on-macOS starter. It does not publish a download, open a release, or update an external page.

The pinned editor commit is `7557eeeedab3dd444effa27474cbaad23ace997e`. Files that the starter ships from that commit must match it byte for byte. Files under `packaging/` are the review tooling and may be newer. `.gitignore` and `RELEASE.md` are the only other source files this review changes, and the packager exempts only those paths from the byte check.

## What was missing

`RELEASE.md` and a comment in `setup.sh` refer to `packaging/package-for-client.sh` and `packaging/delivery/ship.sh`. Neither file existed in the pinned tree. An older archive label (`2026.09.03.2`) is not a git commit and is not reused here.

`package-for-client.sh` now builds the allowlisted starter. `delivery/ship.sh` always exits 3 and does not upload.

## Build a local zip

```bash
./packaging/package-for-client.sh pack --output /tmp/premiere-mac-starter.zip
```

`plan` prints the member list and writes nothing. `--publish`, `--upload`, and `--release` are refused. `--lane` accepts `premiere` only.

The zip contains `VERSION`, `MANIFEST.json`, and `SHA256SUMS`. `distribution=not-released`. Two packs of the same tree produce the same bytes.

## What the allowlist will not do

The packager never copies the repository wholesale. Engine rules drop, even if a profile allow prefix is broad:

- `projects/`, job media, outputs, logs, caches, `node_modules/`, `vendor/`
- `.git/`, `.env`, `.mcp.json`, `.setup-complete`, `.setup-hyperframes-ok`
- personal series presets under `presets/road-to-20k/`
- home-directory paths and secret markers inside a file that would otherwise ship (the build fails; the value is not printed)
- symlinks
- fonts, LUTs, sounds, models, and project templates unless `license-audit.json` allows that exact path

Read `LICENSES.md` before expecting a house grade, SFX, or Coolvetica captions. Those assets are withheld.

## Read next

- `STARTER.md` — onboarding for this archive (`START-HERE.md` inside the zip)
- `PREREQUISITES.md` — tools and pins
- `SAMPLE.md` — synthetic footage only
- `ACCEPTANCE.md` — install, edit, and export checks
- `gates/MAC-SMOKE.md` — manual Mac gates required before any download or setup record
