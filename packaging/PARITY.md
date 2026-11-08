# Full-editor parity ledger

This archive's target is the full source editor plus the reviewed local tools, not a reduced starter. It is not a certification that a clean Mac matches any existing install. Linux tests do not prove Premiere.

Baseline the docs can state: bridge notes from the working install reported Premiere 25.6.2. Grading measurements in the editor docs were taken on 26.3.2. Neither number has been re-proven by this branch.

## Included from the pinned commit

Setup, check, Premiere and Resolve installers, finalize, the Premiere bridge and launch scripts, audio polish, joint fades, grade-lut, all tracked lanes, all tracked skills, and the tracked series preset. Those bytes match `7557eeeedab3dd444effa27474cbaad23ace997e` unless `packaging/provenance.json` names the file.

Other editing modes stay in the archive and stay unverified here: Resolve, CapCut, chat-only, captions, background music, clipper, and the HyperFrames skills. Platform support is whatever each skill already says. This ledger does not add a new certification.

## Included from the reviewed local copies

These were not in the pinned tree, except `place.py`, which gains one linked-audio check for `/fx/outputs/` plus a dry-run default:

| Tool | What it keeps | Default |
| --- | --- | --- |
| `tools/grade.py` | V1/V2 Lumetri, one backup, close, captured-look write, dangling-pointer check, reopen | Refuses without `--apply`. closeDocument can drop the bridge. Not certified on 25.6.2. |
| `tools/level_match.py` | Kept-speech target −15 LUFS, clamp −12..+15 dB, half-dB steps, after audio-polish | Refuses to write unless `--apply`. |
| `tools/media_fix.py` | Blur feather 140 px from y1480, CFR at 30 fps, CRF 14 | `--apply` writes a derived file inside the job. The original moves only with `--move-original`, and only inside that job. |
| `tools/tracks.py` | Read-only track dump | `--save` is optional. Activation can still change the active project. |
| `tools/place.py` | Clears V2–V5, strips linked audio for raw, b-roll, and effect renders, leaves other A2+ audio | Refuses without `--apply`. |
| `tools/punch_ins.py` | Static scale, push, and five-frame punch math; YuNet samples at 0.2/0.5/0.8 | Refuses without `--apply`. The model license is separate. |
| `tools/fx_segments.py` | 1080×1920, exact 30 fps, hyperframes 0.8.16 mattes | Refuses without `--apply`. Does not move raw files. |
| `templates/build_daycard.py` | Cleaned static-median matte, frame-0 title opacity 0, 30 fps ProRes 4444 | Will not render from `presets/`. Copy it into the job first. |
| `templates/fx/*.py` | Seventeen effect recipes and the two orchestration examples. `scale_at` still returns before an unreachable second return. | Will not render unless the working directory already has `src/`. |

`presets/road-to-20k/BEHAVIOR.md` is the portable write-up of pacing, caption sizes, audio order, and effect rules. The tracked README and `/20k` skill in git are still the older pinned text. Later local rewrites of those docs were not byte-copied.

## Assets

| Item | Archive | Why |
| --- | --- | --- |
| Inter, TikTok Sans | Included with existing OFL files | OFL text already in tree. Name tables also declare OFL 1.1. |
| Instrument Serif, DM Serif Display Italic, Playfair Display Italic VF | Included with upstream OFL files | Name ID 13 declares OFL 1.1. Bytes match the Google Fonts files named in `license-audit.json`. |
| YuNet `face_detection_yunet_2023mar.onnx` | Included with MIT notice | SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` matches the OpenCV Zoo LFS object. That directory's license is MIT, Copyright 2020 Shiqi Yu. |
| Coolvetica | Not included | Typodermic copyright, no license grant in the name table or beside the files. |
| CinePacks cubes and captured look params | Not included | Copyright headers, no grant. Params are not converted or re-wrapped. |
| SFX clips | Not included | No license record. Clip metadata is not redistributed. |
| Adjustment-layer donor | Path-cleaned copy only | Last-known path fields cleared. Premiere import untested. |
| CapCut text templates with cache paths | Not included | Absolute home paths. The bridge script still ships. |

`python3 packaging/assets/check_required_assets.py` exits 2 while those blocked rows remain. That is intentional.

## Not claimed

Same-footage prompt comparison, fresh install, export loudness, caption metrics, grade save/reopen, and multi-editor parity. See `gates/MAC-SMOKE.md` and `gates/parity-blockers.json`. `delivery/ship.sh` still refuses to publish.
