# /// script
# dependencies = ["pillow"]
# ///
"""Road to 20K Day N overlays (preset: presets/road-to-20k, the Day 6/7 look).

Copy into projects/<job>/hf-graphics/ and edit ONLY the JOB CONFIG block. Renders straight-alpha ProRes 4444
movs at 30 fps into hf-graphics/renders/ for the Premiere graphics tracks.

  uv run hf-graphics/build_overlays.py all            # daymark + pops + timestamps + captions (+ slates)
  uv run hf-graphics/build_overlays.py captions       # just one family: title | pops | ts [name] | captions | slate

Layout (1080x1920, HiveMind reel-layout-safe-zones.md): hook band y182-447, chest caption band y895-1087,
safe zone x92-988 / y163-1670. Look: TikTok Sans from assets/fonts ONLY (the font loader asserts the family),
white fill + black outline, no boxes, no shadows.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

JOB = Path(__file__).resolve().parent.parent
FONTS = JOB.parent.parent / "assets" / "fonts"
OUT = JOB / "hf-graphics" / "renders"
W, H, FPS = 1080, 1920, 30
SAFE_X0, SAFE_X1 = 92, 988
F = lambda f: f / 30          # frames -> seconds (all layout below is in timeline frames @30)

# ============================== JOB CONFIG (edit per job) ==============================
VER = "v1"                    # bump on every re-render so Premiere never shows a cached file
DAY = 8                       # -> "DAY 8" in the hook band
END_F = 0                     # last frame of the timeline (V1 end); the reel ends on the live close, NO end card
HOOK_F = 0                    # frames the "DAY N" mark holds = the length of the Day N hook (on from its first frame)
BROLL_F = []                  # [(f0, f1), ...] V2 picture-only spans: captions break at their edges
# caption height per shot, from a program-frame band check (first match wins; anything unlisted = chest band 998):
#   998 face sits high (balcony / wide)  ·  1340 just under the chin, or over b-roll / a fitted 16:9 frame  ·  1500 selfie, chin ~y1320
CAP_Y_F = []                  # [(f0, f1, y), ...]
TIMESTAMPS = []               # [("ts-1152", "11:52 AM", f0, 60), ...]  clip creation time, on b-roll only
POPS = []                     # [("pop-setup", [("First AI video editor setup", 60)], 300, f0, 105), ...]  rows = (text, px); top y; start frame; frames
SLATES = []                   # [("slate-close", "CLOSE GOES HERE", 90), ...]  black placeholder for footage not filmed yet
# caption word fixes, keyed by (canonical transcript start time rounded to 0.01, exact word text) from outputs/<job>.transcript.json:
RETEXT = {}                   # {(6.01, 'down'): 'DOWN', (24.82, 'cloud'): 'Claude', ...}   CAPS on the key words, casing, punctuation, mishears
DROP = set()                  # {(12.51, 'Like,'), ...}   slivers of cut words, words merged into a neighbour
RETIME = {}                   # {(22.24, 'and'): (22.241, 22.692), ...}   canonical times
INSERT = []                   # [("to", 21.407, 21.527), ...]   words WhisperX lost (canonical times)
# ======================================================================================

DAYMARK = dict(text=f"DAY {DAY}", weight="Bold", size=118, track=20, stroke=3, band=(182, 447))
CAP = dict(size=58, stroke=4, center_y=998, max_words=4, max_chars=24, band=(895, 1087))
TS = dict(size=44, stroke=4, x=100, bottom=1600)
TIMELINE_END = F(END_F)

_segs = json.loads((JOB / "transcript" / "cuts.json").read_text())["segments"]
_tlp = JOB / "premiere" / "timeline-clips.json"
if _tlp.exists():             # V1 as it sits now (presets/road-to-20k/tools/dump_timeline.py): survives hand edits of any kind
    CLIPS = json.loads(_tlp.read_text())
else:                         # before the replay: EDL arithmetic
    CLIPS, _f = [], 0.0
    for s in _segs:
        CLIPS.append(dict(clip=s["clip"], f0=round(_f * FPS), f1=round((_f + s["end"] - s["start"]) * FPS), **{"in": s["start"]})); _f += s["end"] - s["start"]
_ON = sorted(CLIPS, key=lambda c: c["f0"])
PICTURE_CUTS = sorted(set([F(c["f0"]) for p, c in zip(_ON, _ON[1:]) if c["clip"] != p["clip"]] + [F(f) for ab in BROLL_F for f in ab]))
CAP_Y_OVERRIDE = [(F(a) - 0.01, F(b) - 0.01, y) for a, b, y in CAP_Y_F]


def font(weight, size):
    f = ImageFont.truetype(str(FONTS / f"TikTokSans36pt-{weight}.ttf"), size)   # assets/fonts only
    assert f.getname() == ("TikTok Sans", weight), f"font load failed: {f.getname()} for {weight}"   # never a system fallback
    return f


def text_layer(draw, xy, s, f, stroke):
    draw.text(xy, s, font=f, fill=(255, 255, 255, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))


def ink(f, s, stroke):
    return f.getbbox(s, stroke_width=stroke)


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def encode(frames, name):
    """frames: [(PIL image, n_frames)] -> OUT/<name>-<VER>.mov (ProRes 4444, straight alpha, 30 fps)."""
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{name}-{VER}.mov"
    with tempfile.TemporaryDirectory() as td:
        lines = []
        for i, (img, n) in enumerate(frames):
            p = Path(td) / f"{i:05d}.png"; img.save(p)
            lines += [f"file '{p}'", f"duration {n / FPS:.6f}"]
        lines.append(f"file '{Path(td) / f'{len(frames) - 1:05d}.png'}'")
        (Path(td) / "list.txt").write_text("\n".join(lines) + "\n")
        total = sum(n for _, n in frames)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(Path(td) / "list.txt"),
                        "-vf", f"fps={FPS}", "-frames:v", str(total), "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", "-vendor", "apl0", str(dst)], check=True)
    print(f"wrote {dst.relative_to(JOB)}  ({total} frames, {total / FPS:.3f}s)")
    return dst


# ---------------------------------------------------------------- the "DAY N" mark (from Day 6)
def build_daymark():
    """TikTok Sans Bold 118, +20 px tracking, 3 px outline, centred in the hook band, static over the Day N hook."""
    m = DAYMARK; f = font(m["weight"], m["size"]); img = blank(); d = ImageDraw.Draw(img)
    chars = list(m["text"]); adv = [f.getlength(c) for c in chars]
    total = sum(adv) + m["track"] * (len(chars) - 1)
    b = ink(f, m["text"], m["stroke"]); h = b[3] - b[1]
    x = W / 2 - total / 2; y = (m["band"][0] + m["band"][1]) / 2 - h / 2 - b[1]
    assert SAFE_X0 <= x - m["stroke"] and x + total + m["stroke"] <= SAFE_X1
    for c, a in zip(chars, adv):
        text_layer(d, (x, y), c, f, m["stroke"]); x += a + m["track"]
    return encode([(img, HOOK_F)], "daymark")


# ---------------------------------------------------------------- text pops
def build_pops():
    """TikTok Sans Bold, white + black outline, centred, top at `top`: 5-frame scale pop (0.70 > 0.88 > 1.06 > 1.02 > 1.00), hold, hard out."""
    for name, rows, top, _, nfr in POPS:
        lines = [(t, font("Bold", sz), max(3, sz // 16)) for t, sz in rows]
        base = blank(); d = ImageDraw.Draw(base); y = top
        for t, f, st in lines:
            b_ = f.getbbox(t, stroke_width=st); x = W / 2 - (b_[2] - b_[0]) / 2 - b_[0]
            d.text((x, y - b_[1]), t, font=f, fill=(255, 255, 255, 255), stroke_width=st, stroke_fill=(0, 0, 0, 255))
            assert SAFE_X0 <= x + b_[0] and x + b_[2] <= SAFE_X1, t
            y += (b_[3] - b_[1]) + 14
        assert 163 <= top and y <= 1670
        cx, cy = W / 2, (top + y) / 2; frames = []
        for sc in (0.70, 0.88, 1.06, 1.02, 1.00):
            im = base.resize((round(W * sc), round(H * sc)), Image.LANCZOS); f_ = blank()
            if sc <= 1: f_.alpha_composite(im, (round(cx - cx * sc), round(cy - cy * sc)))
            else: f_.paste(im.crop((round(cx * sc - cx), round(cy * sc - cy), round(cx * sc - cx) + W, round(cy * sc - cy) + H)), (0, 0))
            frames.append((f_, 1))
        frames.append((base, nfr - 5))
        print(f"{name}: ink y{top}-{y}"); encode(frames, name)


# ---------------------------------------------------------------- timestamps
def build_ts(only=None):
    f = font("Bold", TS["size"])
    for name, s, _, nfr in TIMESTAMPS:
        if only and name != only: continue
        img = blank(); d = ImageDraw.Draw(img); b = ink(f, s, TS["stroke"])
        text_layer(d, (TS["x"] - b[0], TS["bottom"] - b[3]), s, f, TS["stroke"])
        encode([(img, nfr)], name)


# ---------------------------------------------------------------- placeholder slates
def build_slate():
    for name, text, nfr in SLATES:
        f = font("Bold", 72); lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if f.getlength(t) <= SAFE_X1 - SAFE_X0: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(img)
        lh = 90; y0 = H / 2 - lh * len(lines) / 2
        for i, l in enumerate(lines):
            d.text((W / 2 - f.getlength(l) / 2, y0 + i * lh), l, font=f, fill=(255, 255, 255, 255))
        encode([(img, nfr)], name)


# ---------------------------------------------------------------- word captions
def _key(t, text):
    """(time, text) key for DROP/RETEXT/RETIME, matched within 15 ms (2-decimal keys vs re-spliced times)."""
    for k in list(DROP) + list(RETEXT) + list(RETIME):
        if k[1] == text and abs(k[0] - t) < 0.015:
            return k
    return (round(t, 2), text)


_OFF = [0.0]
for _s in _segs: _OFF.append(_OFF[-1] + _s["end"] - _s["start"])


def _seg(t):
    return max(0, min(len(_segs) - 1, next((k for k in range(len(_segs)) if t < _OFF[k + 1] - 1e-6), len(_segs) - 1)))


def _src(t, i=None):
    """canonical (EDL) time -> (clip, source seconds), through EDL segment i (default: the one t falls in)."""
    i = _seg(t) if i is None else i
    return _segs[i]["clip"], _segs[i]["start"] + (t - _OFF[i])


def _tl(t, i=None, end=False):
    """canonical time -> timeline seconds: find the V1 clip that shows that source moment now; None if it was cut out.
    For a word's end (end=True) the clip that holds the word's start is used and the time is clamped to its out-point."""
    clip, src = _src(t, i)
    for c in CLIPS:
        dur = (c["f1"] - c["f0"]) / FPS
        if c["clip"] == clip and c["in"] - 0.02 <= src < c["in"] + dur + (0.25 if end else 0):
            return c["f0"] / FPS + min(max(src - c["in"], 0.0), dur)
    return None


def caption_words():
    tr = json.loads((JOB / "outputs" / f"{JOB.name}.transcript.json").read_text())
    out = []
    for w in tr["words"]:
        if w.get("type") != "word": continue
        key = _key(w["start"], w["text"])
        if key in DROP: continue
        t = RETEXT.get(key, w["text"])
        if t == "i": t = "I"
        a, b = RETIME.get(key, (w["start"], w["end"]))
        a, b = _tl(a), _tl(b, _seg(a), end=True)
        if a is None or b is None: continue
        out.append(dict(text=t, start=a, end=b))
    out += [dict(text=t, start=_tl(a), end=_tl(b, _seg(a), end=True)) for t, a, b in INSERT if _tl(a) is not None]
    return sorted(out, key=lambda w: w["start"])


def show(t):  # display form: drop trailing . and , (keep ?)
    return t.rstrip(".,")


def phrases(words, cuts):
    """Clauses break on punctuation, a pause > 0.35 s or a picture change; each clause splits into the fewest EVEN chunks
    that fit max_words/max_chars; a one-word line joins its neighbour when they are back to back and still fit."""
    clauses, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
        nxt = words[i + 1]["start"] if i + 1 < len(words) else 9e9
        if w["text"][-1] in ".?!," or gap > 0.35 or any(w["start"] < c <= nxt for c in cuts):
            clauses.append(cur); cur = []
    if cur: clauses.append(cur)
    groups = []
    for c in clauses:
        n = -(-len(c) // (CAP["max_words"] + 1))
        while True:
            size = -(-len(c) // n); chunks = [c[i:i + size] for i in range(0, len(c), size)]
            if all(len(" ".join(show(w["text"]) for w in ch)) <= CAP["max_chars"] for ch in chunks) or n >= len(c): break
            n += 1
        groups += chunks
    merged = []
    txt = lambda ws: " ".join(show(w["text"]) for w in ws)
    for g in groups:
        if merged and (len(g) == 1 or len(merged[-1]) == 1) and len(merged[-1]) + len(g) <= 5 \
                and len(txt(merged[-1] + g)) <= CAP["max_chars"] and g[0]["start"] - merged[-1][-1]["end"] < 0.35 \
                and merged[-1][-1]["text"][-1] not in ".?!" and not any(merged[-1][-1]["start"] < c <= g[0]["start"] for c in cuts):
            merged[-1] = merged[-1] + g
        else:
            merged.append(g)
    return merged


def build_captions():
    """Word-by-word: each phrase is pre-laid at full width and its words appear on their own WhisperX beat.
    TikTok Sans Bold 58, white + 4 px outline, centred; Y per shot from CAP_Y_F (default: chest band 998)."""
    cuts = PICTURE_CUTS
    f = font("Bold", CAP["size"]); st = CAP["stroke"]
    space = f.getlength(" ") + 2 * st
    groups = phrases(caption_words(), cuts)
    sheet, events = [], []
    for gi, g in enumerate(groups):
        toks = [show(w["text"]) for w in g]; widths = [f.getlength(s) for s in toks]
        full = sum(widths) + space * (len(toks) - 1)
        assert full + 2 * st <= SAFE_X1 - SAFE_X0, (toks, full)
        x0 = W / 2 - full / 2; asc, desc = f.getmetrics()
        cy = next((c for a, b, c in CAP_Y_OVERRIDE if a <= g[0]["start"] < b), None)
        y = (cy or CAP["center_y"]) - (asc + desc) / 2
        assert 163 <= y - st and y + asc + desc + st <= 1670
        nxt = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else None
        end = g[-1]["end"] + 0.4
        if nxt is not None and nxt - g[-1]["end"] <= 1.0: end = nxt
        end = min(end, nxt) if nxt is not None else min(end, TIMELINE_END)
        end = min([end] + [c for c in cuts if g[0]["start"] < c < end])
        for k, w in enumerate(g):
            img = blank(); d = ImageDraw.Draw(img); x = x0
            for j in range(k + 1):
                text_layer(d, (x, y), toks[j], f, st); x += widths[j] + space
            events.append((w["start"], img))
        events.append((end, None))
        sheet.append(f"{g[0]['start']:6.2f}-{end:6.2f}  {' '.join(toks)}")
    t0 = round(events[0][0] * FPS)
    frames, cur_img, cur_f = [], None, t0
    for t, img in events + [(TIMELINE_END, None)]:
        fr = round(t * FPS)
        if fr > cur_f:
            frames.append((cur_img or blank(), fr - cur_f)); cur_f = fr
        if img is not None or fr >= cur_f:
            cur_img = img
    print("\n".join(sheet)); print(f"captions start at frame {t0}  (place on V3 at frame {t0})")
    (OUT.parent / "captions-sheet.txt").write_text("\n".join(sheet) + f"\nstart_frame {t0}\n")
    return encode(frames, "captions")


if __name__ == "__main__":
    assert END_F > 0 and HOOK_F > 0, "fill in the JOB CONFIG block first (END_F, HOOK_F)"
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("title", "all"): build_daymark()
    if what in ("pops", "all"): build_pops()
    if what in ("ts", "all"): build_ts(sys.argv[2] if len(sys.argv) > 2 else None)
    if what in ("slate", "all"): build_slate()
    if what in ("captions", "all"): build_captions()
