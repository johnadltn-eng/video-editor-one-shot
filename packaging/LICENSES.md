# License and asset prerequisites

Tracked files were not treated as safe to redistribute just because they are in the tree. The packager includes a media or font file only when `license-audit.json` allows that path and the named license file is in the archive and contains its marker.

## Allowed

| Files | Grant in this tree |
| --- | --- |
| `assets/fonts/Inter-Regular.otf`, `Inter-Bold.otf`, `Inter-Black.otf` | `assets/fonts/OFL-Inter.txt` (SIL OFL 1.1). The license must travel with the fonts. |
| `assets/fonts/TikTokSans36pt-*.ttf` (Black, Bold, ExtraBold, SemiBold) | `assets/fonts/OFL-TikTokSans.txt` (SIL OFL 1.1). |

Editor source that matches the pinned commit is included by the allowlist (scripts, presets, the Premiere lane, and the minimal skill set). That is the starter's own code and docs, not a third-party media license.

## Withheld

| Asset | Why |
| --- | --- |
| All 30 files under `assets/luts/**/*.cube` | Each header says Created by CinePacks, Copyright 2019, cinepacks.store. No redistribution license is in the tree. |
| `assets/luts/rec709/Autumn-Rec709.lookparams` | Captured grade payload for that LUT. Withheld with the cubes. Grading stays unverified. |
| `assets/sfx/` | No license or credit file. Clips are not cleared by their filenames. |
| `Coolvetica-Rg.otf`, `Coolvetica-Hv-Comp.otf` | No license file. Explainer captions that require Coolvetica cannot be rendered from this starter. |
| `PlayfairDisplay-Italic-VF.ttf`, `DMSerifDisplay-Italic.ttf`, `InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf` | No license file next to the binaries. |
| `assets/models/face_detection_yunet_2023mar.onnx` | No license file for the model binary. |
| `lanes/premiere/premiere-templates/adjustment-layer.prproj` | Embeds an absolute home-directory path. The path scan rejects it, so the template is withheld. |
| Skill-bundled woff2 fonts and Pixabay-credited clips under other skills | Those skills are outside the minimal allowlist, and the engine suffix rules would drop the binaries anyway. |
| Face photos and logos | The folders are placeholders for a local creator. They are not part of the starter. |

## Personal paths

`/Users/Shared` and `/Users/Public` appear in setup comments as machine-wide locations and are allowed. Any other `/Users/<name>/` or `/home/<name>/` path inside a file the allowlist selected fails the build. `.env`, `.mcp.json`, and setup marker files are excluded even if a profile tries to allow them.

## Adding an asset later

Put the license text in the tree, point `license-audit.json` at that file and a marker that the text contains, and add a test that the archive includes both. Do not flip an entry to allow because the file was already committed.
