# Prerequisites

Acceptance host: **macOS** with **Adobe Premiere Pro** installed. Other operating systems and other editors are outside this starter even where `setup.sh` mentions them.

Linux unit tests do not install these tools and do not certify the Mac path.

## Tools

| Tool | Why | Pin / floor |
| --- | --- | --- |
| git | `setup-premiere.sh` clones the bridge engine | any current git |
| Node.js | bridge and MCP engine | 18 or newer (`setup-premiere.sh` checks the major version) |
| ffmpeg | synthetic sample, rough cut, export check | lavfi `testsrc2` and `sine` for the sample script |
| python3 | packager, captions, grade tool | 3.9+ is enough for the packager |
| uv | transcription environment on first speech rough cut | current uv |
| Homebrew | fresh-Mac installs inside `./setup.sh` | the Mac one-liner in `SETUP.md` |

`./check-setup.sh` is report-only. It does not prove Premiere is connected.

## Pins the setup scripts already contain

- Render engine: `npx hyperframes@0.8.16` (`HF_PIN` in `setup.sh`). Do not run `hyperframes upgrade`.
- Premiere MCP engine: git commit `12684e37297a702265985dffa7d33629d28074f4` (v1.2.3) in `setup-premiere.sh`. The comment on that pin says it was verified on Premiere 26.3.2. This starter does not extend that claim to other builds.
- Editor content pin: `7557eeeedab3dd444effa27474cbaad23ace997e`.

The MCP clone and its `node_modules` are created on the Mac by setup. They are not in the starter archive (`vendor/` is denied).

## Premiere version

Grading and several bridge notes in the editor were measured on **26.3.2**. If `premiere-bridge.mjs ping` reports a different version, including **25.6.2**, record the string and leave grading unverified. Do not treat the ping as an export or grade certification.

## Not required for the minimal path

- The personal day-number preset
- Face photos, logos, or a filled brand kit
- A Hugging Face token (`.env.example` is optional diarization only)
- A thumbnail account
- The withheld LUT, SFX, Coolvetica, and face-model files

A speech rough cut downloads the WhisperX large-v3 model on first use. The synthetic test pattern has no speech, so that download is not part of the plumbing check.
