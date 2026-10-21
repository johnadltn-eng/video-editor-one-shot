#!/usr/bin/env python3
"""Author the Day N EDL from word anchors (Road to 20K preset). Copy to projects/<job>/transcript/author_edl.py.

seg(clip, a, b, section): a / b = the WhisperX START time of the first / last kept word (from transcript/words.json);
the segment runs from the first word's start to the last word's end. refine-cuts.py (inside splice.sh) then
measures the real acoustic edges. Pin a hand-measured edge with dict(seg(...), start=/end=..., no_refine=True).

Order = the order on the timeline. One line per kept phrase; say in the comment what was cut and why.
Writes transcript/cuts.authored.json + /tmp/video-editor/<job>/cuts.json (what splice.sh reads), then:
  AMPLIFY_DB=0 RENDER=0 bash .claude/skills/rough-cut/scripts/splice.sh projects/<job>
"""
import json
from pathlib import Path
J = Path(__file__).resolve().parent.parent
W = {c['clip']: c['words'] for c in json.load(open(J / 'transcript/words.json'))['clips']}


def seg(clip, a, b, section, **kw):
    ws = [w for w in W[clip] if 'start' in w]
    first = min(ws, key=lambda x: abs(x['start'] - a)); last = min(ws, key=lambda x: abs(x['start'] - b))
    i0, i1 = ws.index(first), ws.index(last)
    d = dict(clip=clip, start=first['start'], end=last['end'], section=section,
             transcript=' '.join(x['w'] for x in ws[i0:i1 + 1]))
    d.update(kw)
    return d


S = [
    # HOOK (in sync), "DAY N" on from its first frame
    # seg('IMG_0000.MOV', 55.86, 57.72, 'hook'),        # Look, if you're someone that thinks ...
    # ...
    # CLOSE: the reel ends on the live close (it loops); NO end card
]

out = {'segments': S}
(J / 'transcript/cuts.authored.json').write_text(json.dumps(out, indent=1))
work = Path('/tmp/video-editor') / J.name
work.mkdir(parents=True, exist_ok=True)
(work / 'cuts.json').write_text(json.dumps(out, indent=1))
for s in S:
    print(f"{s['section']:8s} {s['clip']:16s} {s['start']:6.2f}-{s['end']:6.2f}  {s['transcript']}")
print(f"{len(S)} segments, {sum(s['end'] - s['start'] for s in S):.1f}s of talk")
