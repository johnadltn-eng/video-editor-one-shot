# SFX — the youtube/default sound design (pipeline step 6)

**WHAT only.** Which sound lands on which motion event, how it is sliced, how loud, and how the
layers stack. Every number here is app-independent. Placing a clip on a timeline is a lane
mechanic: [`LANES.md`](../../../LANES.md) § step 6 (Premiere: `lanes/premiere/place-sfx.py`).

Measured off the one shipped sound design, a hand-placed reference intro: 65 clips, 51
onsets, every one frame-grabbed and level-measured. The machine-readable copy is
[`sfx.json`](sfx.json); [`workflows/sfx-plan.py`](../../../workflows/sfx-plan.py) reads it and
turns the placed graphics into `projects/<job>/hf-graphics/sfx-plan.{json,md}`.

## The law

1. **Events come from the graphics, not from the transcript.** Every registry call a comp makes
   (`pop`, `slam`, `riseIn`, `slideIn`, `slideOut`, `drawOn`, `countUp`, `reveal`), every word of a
   text animation rising in, and every hard cut INTO a full-screen is an event. Cuts back to the
   face are not. Exits (`riseOut`, `exit`) are not. Talking-head stretches with no graphic get
   nothing.
2. **One sound per motion class, the same one every time.** Variation comes from slicing the file
   differently on a run, never from swapping sounds. Stings (WOW, bell, impact) are singletons and
   are not in the default map: they are a plan-time call, one per piece at most.
3. **One-shots are sub-slices of the library file.** Each event class carries its slices in
   `sfx.json`; a run rotates through them so no two adjacent hits play the identical sample.
   Sustained classes (`countUp`, `reveal`) are cut to the event's duration.
4. **Timing is on the element's own onset**, snapped to the frame grid. A slide whoosh starts ON
   the slide start. A cut-in whoosh leads the cut by 2 frames; a riser ends 0.45s before it.
   Layers on one hit land on the same frame.
5. **Levels are class bands on the on-timeline peak**, so the clip level is target minus the
   measured slice peak, whole dB, never above +6:

   | class | target peak | used for |
   |---|---|---|
   | whoosh | −4 dBFS | slides, cut-ins |
   | transient | −6 (the voice ceiling) | pops, slams |
   | tick | −6 | stepping / ticking events (Texting On Phone, held in reserve) |
   | marker | −9 | draw-ons, strikes |
   | character | −10 | title-card whoosh, any sting |
   | soft | −12 | rise-ins |
   | bed | −18 | count-ups, type-ons, risers |

6. **Three SFX tracks by layer depth:** A2 carries the primary sound of every event; a sound
   that would OVERLAP a different sound still ringing on a track goes a layer down (A3, then A4) so
   both play out, while the same sound repeating on top of itself stays on one track and truncates
   (the reference's machine-gun pops). An identical sound within 2 frames is a doubling and is
   dropped. Music is A5 (opt-in). No fades on any SFX clip, every clip hard-trimmed to its slice.
7. **Density follows the graphics.** The reference intro ran 1.25 events/s inside the graphics
   span. A plan that sounds every registry event lands near that on its own; it never needs
   padding, and it never needs thinning unless you say so at step 7.

## The map

| event | sound | level | slice / timing |
|---|---|---|---|
| `pop` (a free-standing object appears) | Pop 1 | transient band | five slices, rotated |
| `slam` (an object stamps) | Metal Pop | transient band | 0.43–0.67 (your slice) |
| `riseIn` (a card, panel, row or label rises) | **Simple Whoosh 1, the SECONDARY whoosh** | soft band; a HERO rise at 0 dB (hand `level_db`) | whole file |
| `slideIn` / `slideOut` and any scene move | **Simple Whoosh 2, THE PRIMARY whoosh** | whoosh band | whole file |
| `drawOn` (a strike, an arrow, an underline) | Pencils & Markers | marker band | four slices, rotated |
| `countUp` (a number stepping) | UI Data Loading | bed band | cut to the count |
| `reveal` (text typing on) | Keyboard Typing.aiff | **fixed +2 dB** | 3.84–5.74, cut to the reveal |
| `flash` / a FLICKER text animation | **Neon Flicker** (paired) | fixed 0 dB | whole file, ONE per strobe at its START, nothing on the landing |
| word on a RISE text animation | Scissors | **fixed −7 dB** | five snips, rotated; a snip is cut short by the next word |
| a RED word (negation) | **Error Buzz** (paired) | fixed −7 dB | whole file, instead of the scissors |
| word on a POP text animation | Pop 1 | transient band | the pop's slices |
| word on a SLAM text animation | **Impact** | fixed −10 dB | 0.93–2.50, **2 frames after** the word onset (on the settle); the run truncates itself, the last word rings |
| `emphasis` (HAND ONLY: a script-critical word) | Impact | fixed −5 dB | 0.90–2.14, 2 frames after the onset; that word loses its scissors |
| `row-tick` (a `pop` inside a list/card graphic) | Lighter | fixed −5 dB | 0.33–0.57: a switch clicking on, not an object |
| `payoff` (HAND ONLY: 100%, the finished node, a check) | Bell Ding | fixed −10 dB | 0–1.5s, **4 frames BEFORE** the visual lands; drops the pop it replaces |
| `gunshot` (HAND ONLY: a literal shot, bullet holes) | Gunshot | fixed −15 dB | 0–0.6s, 2 frames early (the attack sits 70 ms in) |
| `processing` (HAND ONLY: software working) | UI Data Loading | fixed −17 dB | 0.57–2.40, cut to the working span |
| `click` (HAND ONLY: a cursor action in a software scene) | Mouse Click | fixed −10 dB | two slices, rotated |
| cut INTO a full-screen | Whoosh Short 2 | whoosh band | whole, 2 frames early; **dropped when a flicker opens the full-screen** |
| the FIRST full-screen of the job | + Riser 2 | bed band | the file's last 1.17s, ending 0.45s before the cut, whoosh or not |
| title card (section boundary) | Genius Intro Sound | character band | first 3.5s |
| `riseOut`, `exit`, cut back to face, push-in, an annotation's arrow | silent | | |

**The whoosh roles (2026-09-03):** Simple Whoosh 2 is the primary, on anything that MOVES
across the frame (slides, scene changes, a panel carrying off). Simple Whoosh 1 is the secondary,
on anything that RISES into place. Whoosh Short 2 is the cut-in only. Other whooshes in the
library are for other animation types as they come up, one whoosh per type.

**Paired sounds (a sound that IS an animation's sound, never swapped):** flicker ↔ Neon Flicker,
red word ↔ Error Buzz, list row ↔ Lighter, slam text ↔ Impact. `assets/sfx/Mac SFX 01–24.wav` are
the individual pieces of the old "Mac & Computer Sound Effects" file (index beside them); Neon
Flicker was 10, Error Buzz was 02; the rest are unassigned until they get used.

**Script calls (never automatic, always a hand entry):** an emphasis Impact on an especially
important word (styling alone, serif or italic, does NOT trigger it: scissors is fine on most
emphasis words), a payoff bell, a gunshot, a software scene's processing bed and clicks. They go
in `projects/<job>/hf-graphics/sfx-hand.json` as `{gid, event, at | word, dur?, level_db?, drop?}`;
`drop` removes the automatic events the hand entry replaces (the pops under a gunshot or a bell).

**Read off the timeline, not guessed (your-job, 2026-09-03):** every row above that names a
fixed level or a frame offset is the value placed by hand on the reference job. Reading the shipped
timeline back against the plan is how the next batch of hand edits becomes the next batch of rules
(the readback is per lane: [`LANES.md`](../../../LANES.md) § step 6).

Sounds still unmapped and when to reach for them by hand: `Japanese WOW` on the one reveal of a
piece; `Slap` on a physical bump; `Deep Whoosh 4` + `Deep Whoosh 3` a second later on a big
drop-out-and-launch; `Analogue Camera Snap` when the prop IS a camera; `Paper Turn` when the surface
IS paper (the vox look, not this one).

## Definition of done

`sfx-plan.json` written and reviewed as a cut sheet (`sfx-plan.md`), every row placed on the
lane's SFX tracks at its planned frame with its planned level, **read back**, and a frame grab at
a sample of onsets showing the event the sound sits on. Runs AFTER the step-5c defect loop dries
(a graphic retimed later orphans its sound); re-run the plan and re-place after any graphic moves.
