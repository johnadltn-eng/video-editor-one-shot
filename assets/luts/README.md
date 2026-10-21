# LUT library

The bundled LUT library: 15 Rec709 cubes in `rec709/`, 15 LOG cubes in `log/`. The Rec709 set is for camera
footage that is already Rec709; the LOG set expects a log-profile source.

- **House look: `rec709/Autumn-Rec709.cube`** as Lumetri Creative > Look, Intensity 70,
  Creative Saturation 115. `uv run lanes/premiere/grade-lut.py apply <job>.prproj` replays it.
- `uv run lanes/premiere/grade-lut.py luts` lists everything and says which cubes replay. It walks
  `assets/luts/` recursively, so subfolder layout is free to change.

The LOOK (which cube, which dials, why): `presets/youtube/default/README.md` § Grade.
The MECHANISM (how it gets written into a project, and every trap): `lanes/premiere/premiere-grading.md`.

A cube with no `.lookparams` needs one hand-application in Premiere before it can replay; the
capture procedure, why the params travel without the cube, and the pid-98 embed trap are all in
`lanes/premiere/premiere-grading.md`.

Autumn's params were captured from `/Users/Shared/video-editor-luts/`, so they carry no username
and pass the leak-check.

## Checksums

`uv run lanes/premiere/grade-lut.py selfcheck` proves every params file offline (element shapes, the
BinaryHash length words, the embedded cube against the `.cube` beside it, the dials, the component
struct) and warns when a file's sha256 no longer matches this list. A re-mint is allowed; an
UNNOTICED one is not (the 2026-09-02 damaged Autumn file was a same-afternoon re-capture nobody had
validated from a render). After a deliberate re-capture that was verified from a program render,
update the line here.

- `rec709/Autumn-Rec709.lookparams` sha256 `7c3f5851b87a5157bada081e3eb275d16221f4003b82ec2642aee140db04ad84` (2026-09-02, pid-4 sentinel fix, verified on your-job: on/off frame delta 63)
- `rec709/London-Rec709.lutparams` sha256 `5af555e7a55ad5812b2370946e2aee69201025584ddb67e00b7f222cd40b2b00` (retired input-slot example; carries a home-directory path, never ships as the default)
