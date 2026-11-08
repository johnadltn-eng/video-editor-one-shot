# Clean sample strategy

The starter does not contain filmed footage, client projects, face photos, or renders.

## Generate a test pattern

```bash
./packaging/sample/make-synthetic-sample.sh
```

That writes a 2-second color-bar clip with a tone under `packaging/sample/out/`. The script refuses job folders (`projects/`), paths that contain `..`, and destinations outside `packaging/sample/out/` or `/tmp`. The clip is gitignored. Do not commit it.

`packaging/sample/synthetic-cuts.json` points at `synthetic-sample.mp4` from 0 to 2 seconds. The transcript is empty because the pattern has no speech. Use it to prove file layout and a Premiere replay, not a dialogue cut.

## What not to use

- Do not zip or copy an existing `projects/` directory.
- Do not point the sample generator at a downloads folder of real footage.
- Do not reuse an old client archive as the clean source. The packager reads the git tree and an allowlist, not a previous zip.
- A speech acceptance clip, if you need one, is recorded for the smoke test and kept out of git. It is not a client file.

## After unpack

Copy the generated clip into a new local job only when a Mac smoke test needs a timeline. Delete that job when the check is done. `projects/` stays untracked.
