# Manual Mac gates

These gates are run by a person on a Mac with Premiere Pro. Linux unit tests do not pass them. A filled record does not publish an archive.

The bridge ping is only the packaging smoke. Parity needs the same new speech clip and the same prompt on an isolated project, then a comparison of coverage and specs. `parity_certified` stays false while `parity-blockers.json` has open rows. Do not use an existing private project.

Write the record only under `packaging/gates/records/` (gitignored, and the packager excludes that directory). Start from `smoke-record.example.json`. Do not put a home-directory path in `runner`.

Check it with:

```bash
python3 packaging/gates/check_mac_smoke.py packaging/gates/records/mac-smoke-record.json
```

`packaging/delivery/ship.sh` still exits with a refusal after this check. Do not record a download, and do not record setup as certified for other people, until every gate below is actually true on that Mac.

## Before any download or setup record

1. `clean_unpack_exclusions` — unpack a locally built archive on a machine that does not already contain this editor. Confirm it has no `projects/`, filmed media, `.git/`, `.env`, `.mcp.json`, `.setup-complete`, or `node_modules/`. The series preset source is supposed to be present. Client projects are not.
2. `dependencies_present` — install from `packaging/PREREQUISITES.md`. `./check-setup.sh` reports the core tools.
3. `setup_sh_completed` — `./setup.sh` finishes far enough to verify tools. A restart it asks for is part of the gate, not a skip.
4. `premiere_lane_setup_completed` — `./setup-premiere.sh` on macOS. Other lanes ship as source and are not certified by this gate.
5. `bridge_ping_recorded` — `node lanes/premiere/premiere-bridge.mjs ping` returns a connection. Save the Premiere version string it reports.
6. `premiere_version_recorded` — the record names that version. Grading docs were measured on **26.3.2**. A report of **25.6.2** does not verify grade or LUT replay. `grading_note` must say the grade is unverified. `grade_lut_replay_verified` stays false until a Mac test uses a cleared LUT. Missing LUTs, SFX, and Coolvetica stay open blockers, not skipped acceptance items.
7. `synthetic_or_self_recorded_only` — footage is the generated test pattern or a clip recorded for this smoke test. No client media, no existing job folder copied in.
8. `timeline_replay` — the synthetic cuts file or that self-recorded clip is replayed onto a Premiere timeline as separate clips.
9. `export_ffprobe` — an in-Premiere export (not a queued external encoder) produces a file, and `ffprobe` shows a video stream.

Also keep:

- `linux_ci_certifies_mac`: false
- `multi_editor_parity_claimed`: false
- `download_published`: false

Resolve, CapCut, Windows, and chat-only are not part of this gate.
