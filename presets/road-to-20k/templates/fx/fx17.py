# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy", "pillow"]
# ///
"""Seventeen-effect recipe library and compositing/tracking helpers.
Review copy with neutral sample literals; no media/assets/models accompany it.
Usage from projects/<job>/fx/: uv run build/fx17.py <01..17>
FAST, SET16 and NOLABEL toggles are preserved; rendered UI is an illustrative effect, not the editor UI."""
import math, os, sys
from pathlib import Path

if __name__ == "__main__" and not (Path.cwd() / "src").is_dir():
    sys.exit("refusing to render outside a job fx directory that already contains src/.")

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import fx  
from fx import W, H, FPS, YELLOW, font, frames, writer, ease_out, ease_io, over  

JOB = Path.cwd()
ASSETS = JOB / "assets"

FAST = os.environ.get("FAST") == "1"

SET16 = os.environ.get("SET16") == "1"
ORDER = ["orbit", "couch wall", "ui world", "frame break", "digital zoom", "phone mockup", "checklist",
         "headline wall", "zoom-through cut", "chart grow", "pull-back reveal", "green screen", "paper cut",
         "vertigo", "cover story", "glass type", "doodle boil"]
if SET16:
    ORDER.remove("doodle boil")


NOLABEL = os.environ.get("NOLABEL") == "1"          


def chip(img, _n, name):
    if NOLABEL:
        return
    n = ORDER.index(name) + 1
    d = ImageDraw.Draw(img)
    f = font("Inter-Bold.otf", 34)
    a, b = f"{n:02d}/{len(ORDER)}", f"  {name}"
    wa, wb = d.textlength(a, font=f), d.textlength(b, font=f)
    x0 = (W - wa - wb) / 2 - 26
    d.rounded_rectangle([x0, 1540, x0 + wa + wb + 52, 1604], 32, fill=(0, 0, 0, 170))
    d.text((x0 + 26, 1553), a, font=f, fill=YELLOW)
    d.text((x0 + 26 + wa, 1553), b, font=f, fill=(255, 255, 255))


fx.chip = chip  



def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def put(layer, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    """Composite img centred at (cx, cy) with scale/rotation/opacity, clipped to the canvas."""
    if alpha <= 0 or scale <= 0:
        return
    im = img
    if scale != 1:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    l, t = max(0, -x), max(0, -y)
    r, b = min(im.width, W - x), min(im.height, H - y)
    if r <= l or b <= t:
        return
    layer.alpha_composite(im.crop((l, t, r, b)), (x + l, y + t))


def shadowed(im, blur=18, off=(0, 14), op=110):
    pad = blur * 3
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, op), (pad + off[0], pad + off[1]), im.getchannel("A"))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(im, (pad, pad))
    return out


def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


def pop(t, t0, dur=0.28, over_=0.12):
    """0 before t0, overshoots to 1+over_ then settles at 1."""
    x = (t - t0) / dur
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return ease_out(x) * (1 + over_ * math.sin(math.pi * x))


def behind(fr, a, layer):
    """layer goes behind the subject: subject pixels (alpha a) stay on top."""
    b = over(fr, layer).astype(np.float32)
    return (a * fr + (1 - a) * b).astype(np.uint8)


def caption(layer, words, t, y=1330, size=96, hi=None, t0=0.0, fnt="Inter-Black.otf", idx=0, t1=None,
            fg=(255, 255, 255), hi_col=YELLOW, stroke=(0, 0, 0, 90), sw=3):
    """Single-line keyword caption; `hi` words in hi_col. Pops in at t0, fades out from t1."""
    k = pop(t, t0, 0.22, 0.08)
    if t1 is not None:
        k *= 1 - ease_io((t - t1) / 0.2)
    if k <= 0:
        return
    f = font(fnt, size, idx)
    tmp = Image.new("RGBA", (W, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    total = d.textlength(" ".join(words), font=f)
    x = (W - total) / 2
    for i, w in enumerate(words):
        col = hi_col if hi and w in hi else fg
        d.text((x, size * 0.3), w, font=f, fill=col, stroke_width=sw, stroke_fill=stroke)
        x += d.textlength(w + " ", font=f)
    put(layer, tmp, W / 2, y, scale=0.9 + 0.1 * k, alpha=min(1, k))


def run(name, fn, matte=False, src=None):
    srcp = JOB / f"src/{src or name}.mp4"
    out = JOB / f"outputs/{name}{'-nolabel' if NOLABEL else '-16' if SET16 else '-fast' if FAST else ''}.mp4"
    w = writer(out, srcp)
    mats = frames(JOB / f"build/{name}-cutout.mov", "rgba", 4) if matte else None
    for i, fr in enumerate(frames(srcp)):
        a = next(mats)[:, :, 3:4].astype(np.float32) / 255 if mats else None
        w.stdin.write(np.ascontiguousarray(fn(i / FPS, fr, a, i)).tobytes())
    w.stdin.close(); w.wait()
    print("wrote", out)


class Track:
    """Smoothed subject centroid / top from the matte."""
    def __init__(self, k=0.2):
        self.k, self.c = k, None

    def __call__(self, a):
        m = a[:, :, 0] > 0.5
        ys, xs = np.nonzero(m[::4, ::4])
        if len(xs) == 0:
            return self.c
        v = np.array([xs.mean() * 4, ys.mean() * 4, ys.min() * 4])
        self.c = v if self.c is None else self.c * (1 - self.k) + v * self.k
        return self.c


def scale_about(img, s, cx, cy, interp=cv2.INTER_LINEAR, border=cv2.BORDER_REFLECT):
    M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
    return cv2.warpAffine(img, M, (W, H), flags=interp, borderMode=border)


def pill(text, size=40, fg=(20, 20, 20), bg=(255, 255, 255), dot=None, pad=(34, 20), r=None, fnt="Inter-Bold.otf"):
    f = font(fnt, size)
    tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(text, font=f))
    dw = size if dot else 0
    im = Image.new("RGBA", (tw + pad[0] * 2 + dw, size + pad[1] * 2 + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], r if r is not None else im.height // 2, fill=bg)
    if dot:
        cy = im.height / 2
        d.ellipse([pad[0], cy - size * .22, pad[0] + size * .44, cy + size * .22], fill=dot)
    d.text((pad[0] + dw, pad[1]), text, font=f, fill=fg)
    return im



def fx_orbit():
    tiles = [shadowed(pill(t, 40, dot=c)) for t, c in
             [("orbit", (255, 90, 90)), ("couch wall", (90, 160, 255)), ("ui world", (255, 190, 60)),
              ("frame break", (150, 110, 255)), ("glass type", (60, 200, 120))]]
    for p in ("post1.jpg", "post5.jpg"):
        im = Image.open(ASSETS / p).convert("RGB").resize((170, 302))
        tiles.append(shadowed(rounded(Image.fromarray(np.asarray(im)), 22)))
    n, tr = len(tiles), Track()

    def f(t, fr, a, i):
        cx, cy, top = tr(a)
        ocx, ocy = cx, top + 300
        grow = ease_out((t - 0.85) / 0.6)                     
        back, front = blank(), blank()
        for j, im in enumerate(tiles):
            th = 2 * math.pi * j / n + t * 2 * math.pi / 5.0
            x = ocx + 420 * grow * math.cos(th)
            y = ocy + 150 * grow * math.sin(th) - 40 * math.cos(th)
            depth = math.sin(th)
            s = (0.82 + 0.22 * (depth + 1) / 2)
            put(front if depth > 0 else back, im, x, y, scale=s * grow, alpha=min(1, grow * 1.4) * (1 if depth > 0 else .85))
        out = behind(fr, a, back)
        caption(front, ["floating", "around", "me"], t, y=1360, size=120, hi=["floating"], t0=3.65,
                fnt="InstrumentSerif-Italic.ttf")
        chip(front, 0, "orbit")
        return over(out, front)
    run("01-orbit", f, matte=True)



def polaroid(path, w=300, rot=0, tag=None):
    im = Image.open(path).convert("RGB")
    h = int(w * im.height / im.width)
    im = im.resize((w, h))
    card = Image.new("RGBA", (w + 28, h + 70), (250, 248, 242, 255))
    card.paste(im, (14, 14))
    d = ImageDraw.Draw(card)
    if tag:
        d.text((18, h + 22), tag, font=font("Inter-Bold.otf", 30), fill=(30, 30, 30))
    tape = Image.new("RGBA", (120, 40), (255, 240, 170, 190))
    card.alpha_composite(tape.rotate(-4, expand=True), ((card.width - 124) // 2, 0))
    return shadowed(card, 14, (0, 10), 120)


def fx_couch():
    spots = [("post1.jpg", "SCENE A", 175, 560, -7, 0.65), ("post5.jpg", "SCENE B", 890, 540, 6, 0.80),
             ("post2.jpg", "SCENE A", 380, 450, 4, 0.95), ("post6.jpg", "SCENE B", 700, 430, -5, 1.10),
             ("post3.jpg", "SCENE A", 185, 960, 5, 1.25), ("post7.jpg", "SCENE B", 885, 950, -6, 1.40)]
    cards = [(polaroid(ASSETS / p, 250, tag=tag), x, y, r, t0) for p, tag, x, y, r, t0 in spots]

    def f(t, fr, a, i):
        wall = blank()
        for im, x, y, r, t0 in cards:
            k = pop(t, t0, 0.3, 0.15)
            put(wall, im, x, y, scale=0.7 + 0.3 * k if k else 0, rot=r + 8 * (1 - min(k, 1)), alpha=min(1, k * 2))
        out = behind(fr, a, wall)
        top = blank()
        caption(top, ["AI", "editor"], t, hi=["editor"], t0=2.38)
        chip(top, 0, "couch wall")
        return over(out, top)
    run("02-couch", f, matte=True)



def fx_ui():
    WX0, WY0, WX1, WY1 = 90, 230, 990, 860
    thumbs = [rounded(Image.open(ASSETS / f"thumb{k}.jpg").convert("RGB").resize((108, 192)), 14) for k in range(1, 6)]
    base = Image.new("RGBA", (WX1 - WX0, WY1 - WY0), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([0, 0, base.width - 1, base.height - 1], 36, fill=(246, 242, 235, 250))
    for k, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 200, 64)]):
        d.ellipse([30 + k * 34, 30, 52 + k * 34, 52], fill=c)
    d.text((base.width / 2 - 70, 24), "new edit", font=font("Inter-Bold.otf", 30), fill=(90, 85, 80))
    d.line([0, 78, base.width, 78], fill=(225, 218, 208), width=2)
    d.text((48, 108), "What are we making today?", font=font("InstrumentSerif-Regular.ttf", 58), fill=(40, 36, 32))
    d.rounded_rectangle([48, 196, base.width - 48, 446], 26, outline=(205, 196, 184), width=3)
    base = shadowed(base, 24, (0, 18), 120)
    pad = 72
    fp = font("Inter-Regular.otf", 38)

    def f(t, fr, a, i):
        layer = blank()
        k = ease_out((t - 0.05) / 0.4)
        put(layer, base, (WX0 + WX1) / 2, (WY0 + WY1) / 2 + 40 * (1 - k), alpha=k)
        d = ImageDraw.Draw(layer)
        ox, oy = WX0, WY0 + int(40 * (1 - k))
        if k > 0.5:
            landed = 0
            for j, th in enumerate(thumbs):
                t0 = 0.45 + j * 0.22
                p = ease_out((t - t0) / 0.35)
                if p <= 0:
                    d.text((ox + 300, oy + 300), "drop clips here", font=fp, fill=(160, 150, 140)) if j == 0 else None
                    continue
                landed += 1
                tx, ty = ox + 110 + j * 134, oy + 322
                put(layer, th, tx, ty - 520 * (1 - p), rot=(1 - p) * (20 - j * 9))
            if landed == len(thumbs):
                tag = pill("RAW CLIPS", 28, fg=(20, 20, 20), bg=YELLOW, pad=(18, 10), r=8)
                put(layer, tag, ox + 800, oy + 230, scale=pop(t, 1.55, 0.2))
            
            typed = "/ui-world"[: max(0, int((t - 0.95) / 0.05))]
            d.rounded_rectangle([ox + 48, oy + 470, ox + WX1 - WX0 - 48, oy + 560], 22, fill=(255, 255, 255))
            d.text((ox + 78, oy + 492), typed or "How can I help you today?", font=fp,
                   fill=(30, 30, 30) if typed else (165, 158, 150))
            if typed and (i // 8) % 2 == 0:
                tw = d.textlength(typed, font=fp)
                d.line([ox + 82 + tw, oy + 494, ox + 82 + tw, oy + 538], fill=(30, 30, 30), width=3)
        
        back = blank()
        word = "CRISP" if t >= 4.45 else ("UI WORLD" if t >= 0.9 else "")
        if word:
            fw = font("Inter-Black.otf", 190)
            tw = ImageDraw.Draw(back).textlength(word, font=fw)
            ImageDraw.Draw(back).text(((W - tw) / 2, 1080), word, font=fw, fill=(255, 255, 255, 235))
        back.alpha_composite(layer)                
        out = behind(fr, a, back)
        top = blank()
        chip(top, 0, "ui world")
        return over(out, top)
    run("03-ui", f, matte=True)



def fx_frame():
    CX0, CY0, CX1, CY1 = 260, 930, 820, 1480
    S, PX, PY = 0.72, 540, 1180
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([CX0, CY0, CX1, CY1], 44, fill=255)
    card = np.asarray(mask, np.float32)[:, :, None] / 255
    border = blank()
    ImageDraw.Draw(border).rounded_rectangle([CX0 - 7, CY0 - 7, CX1 + 7, CY1 + 7], 50, outline=(255, 255, 255, 255), width=8)
    tag = pill(f"04/{len(ORDER)}", 30, fg=(255, 255, 255), bg=(0, 0, 0, 150), pad=(16, 8))
    below = (np.arange(H)[:, None, None] < CY1 - 40).astype(np.float32)

    def f(t, fr, a, i):
        p = ease_io((t - 0.25) / 0.55)                      
        s = 1 + (S - 1) * p
        vid = scale_about(fr, s, PX, PY)
        al = scale_about(a[:, :, 0], s, PX, PY)[:, :, None]
        bg = cv2.resize(cv2.GaussianBlur(cv2.resize(fr, (W // 8, H // 8)), (0, 0), 6), (W, H))
        bg = (bg * 0.45).astype(np.uint8)
        cm = card * p + (1 - p)                               
        out = (cm * vid + (1 - cm) * bg).astype(np.uint8)
        top = blank()
        if p > 0.98:
            out = over(out, border)
            put(top, tag, CX0 + 70, CY0 + 40)
        brk = ease_out((t - 1.03) / 0.12)                     
        if brk > 0:
            m = al * below * brk * (1 - card)
            out = (m * vid + (1 - m) * out).astype(np.uint8)
        caption(top, ["super", "immersive"], t, y=360, size=96, hi=["immersive"], t0=3.17)
        chip(top, 0, "frame break")
        return over(out, top)
    run("04-frame", f, matte=True)



def fx_phone():
    PW, PH = 400, 820
    msgs = [("l", "seen the new edit?", 0.55), ("r", "the phone mockup?", 1.85),
            ("l", "looks crisp", 3.00), ("r", "send it to me", 4.55)]
    fm = font("Inter-Regular.otf", 30)

    def phone(t):
        im = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, PW - 1, PH - 1], 64, fill=(18, 18, 20))
        d.rounded_rectangle([12, 12, PW - 13, PH - 13], 54, fill=(0, 0, 0))
        d.rounded_rectangle([PW / 2 - 60, 26, PW / 2 + 60, 58], 16, fill=(18, 18, 20))
        d.ellipse([PW / 2 - 34, 84, PW / 2 + 34, 152], fill=(90, 90, 100))
        d.text((PW / 2 - 13, 96), "S", font=font("Inter-Bold.otf", 40), fill=(255, 255, 255))
        d.text((PW / 2 - 14, 160), "Sample", font=font("Inter-Bold.otf", 24), fill=(200, 200, 205))
        d.line([12, 204, PW - 12, 204], fill=(40, 40, 44), width=2)
        y = 232
        for side, text, t0 in msgs:
            k = pop(t, t0, 0.25, 0.1)
            if k <= 0:
                if t > t0 - 0.8 and side == "l":                  
                    d.rounded_rectangle([28, y, 128, y + 54], 27, fill=(44, 44, 48))
                    for q in range(3):
                        on = (int(t * 6) % 3) == q
                        d.ellipse([48 + q * 26, y + 20, 62 + q * 26, y + 34], fill=(200, 200, 205) if on else (110, 110, 115))
                break
            tw = d.textlength(text, font=fm)
            bw, bh = tw + 44, 62
            x0 = 28 if side == "l" else PW - 28 - bw
            col = (44, 44, 48) if side == "l" else (10, 132, 255)
            bub = Image.new("RGBA", (int(bw), bh), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bub)
            bd.rounded_rectangle([0, 0, bw - 1, bh - 1], 30, fill=col)
            bd.text((22, 13), text, font=fm, fill=(255, 255, 255))
            put(im, bub, x0 + bw / 2, y + bh / 2, scale=0.6 + 0.4 * k, alpha=min(1, k * 1.5))
            y += bh + 16
        return shadowed(im, 26, (0, 20), 130)

    def f(t, fr, a, i):
        layer = blank()
        k = ease_out(t / 0.45)
        put(layer, phone(t), 205, 600 + 900 * (1 - k), scale=0.82, rot=-6 * (1 - k) + 3 + 1.2 * math.sin(t * 1.4))   
        caption(layer, ["show", "the", "texts"], t, hi=["texts"], t0=4.60)
        chip(layer, 0, "phone mockup")
        return over(fr, layer)
    run("06-phone", f)



def note(text, kind, w):
    fonts = {"paper": ("InstrumentSerif-Regular.ttf", (250, 247, 240), (25, 25, 25)),
             "sticky": ("Inter-Bold.otf", (255, 222, 89), (30, 30, 30)),
             "black": ("Inter-Black.otf", (18, 18, 18), (255, 255, 255))}
    fn, bg, fg = fonts[kind]
    size = 46 if kind != "paper" else 54
    f = font(fn, size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines, cur = [], ""
    for wd in text.split():
        if d0.textlength((cur + " " + wd).strip(), font=f) > w - 50:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    h = 40 + len(lines) * int(size * 1.15) + 20
    im = Image.new("RGBA", (w, h), bg + (255,))
    d = ImageDraw.Draw(im)
    for k, ln in enumerate(lines):
        d.text((25, 28 + k * int(size * 1.15)), ln, font=f, fill=fg)
    pin = Image.new("RGBA", (26, 26), (0, 0, 0, 0))
    ImageDraw.Draw(pin).ellipse([0, 0, 25, 25], fill=(220, 50, 50))
    im.alpha_composite(pin, (w // 2 - 13, 6))
    return shadowed(im, 12, (0, 8), 120)


def fx_headline():
    spec = [("Headline wall", "paper", 380, 540, 290, -2, 0.75), ("BIG.", "black", 240, 200, 470, -5, 2.55),
            ("Anything you want big and bold", "paper", 340, 840, 420, 4, 1.90), (f"{len(ORDER)} edits.", "black", 260, 190, 780, 5, 1.05),
            ("AI editor", "paper", 300, 880, 760, -4, 1.30), ("BOLD.", "sticky", 260, 860, 1040, -6, 2.90)]
    notes = [(note(*s[:3]), *s[3:]) for s in spec]

    def f(t, fr, a, i):
        wall = blank()
        for k, (im, x, y, r, t0) in enumerate(notes):
            p = pop(t, t0, 0.22, 0.18)
            put(wall, im, x, y, scale=1.35 - 0.35 * p if p else 0, rot=r, alpha=min(1, p * 2))
        
        c = ease_out((t - 3.55) / 0.35)
        if c > 0:
            d = ImageDraw.Draw(wall)
            pts = [(200 + 165 * math.cos(u) + 6 * math.sin(5 * u), 470 + 85 * math.sin(u))
                   for u in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.08 * c, 60)]
            d.line(pts, fill=(230, 40, 40, 255), width=10, joint="curve")
        out = behind(fr, a, wall)
        top = blank()
        chip(top, 0, "headline wall")
        return over(out, top)
    run("08-headline", f, matte=True)



def dark_center(fr):
    g = cv2.cvtColor(cv2.resize(fr, (W // 8, H // 8)), cv2.COLOR_RGB2GRAY)
    m = (g < 45).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return W / 2, H / 2
    j = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    return cen[j][0] * 8, cen[j][1] * 8


def fx_zoomthrough():
    CUT = 74 / FPS                                            
    det = cv2.FaceDetectorYN_create(str(fx.ROOT / "assets/models/face_detection_yunet_2023mar.onnx"),
                                    "", (W, H), score_threshold=0.6)
    st = {}

    def anchor(fr):
        c = fx.face_center(fr, det)
        return (W / 2, H / 2) if c is None else (float(c[0]), float(c[1]))

    def blurzoom(fr, s, cx, cy):
        acc = np.zeros((H, W, 3), np.float32)
        for q in (1.0, 0.94, 0.88, 0.82):
            acc += scale_about(fr, max(1.0, s * q), cx, cy)
        return (acc / 4).astype(np.uint8)

    def f(t, fr, a, i):
        if t < CUT:
            if "a" not in st:
                st["a"] = anchor(fr)
            p = ((t - 1.70) / (CUT - 1.70))                   
            s = 1 + 6 * max(0, p) ** 2.4
            out = blurzoom(fr, s, *st["a"]) if p > 0 else fr
        else:
            if "b" not in st:
                st["b"] = anchor(fr)
            p = ease_out((t - CUT) / 0.45)
            s = 1 + 2.5 * (1 - p)
            out = blurzoom(fr, s, *st["b"]) if s > 1.01 else fr
        top = blank()
        if t < CUT:
            caption(top, ["zoom", "through"], t, hi=["through"], t0=1.70)
        else:
            caption(top, ["looking", "clean"], t, hi=["clean"], t0=CUT + 2.10)
        chip(top, 0, "zoom-through cut")
        return over(out, top)
    run("09-zoom", f)



def fx_chart():
    X0, Y0, X1, Y1 = 110, 300, 970, 820
    rng = np.random.default_rng(4)
    xs = np.linspace(X0 + 30, X1 - 60, 40)
    base = np.linspace(0, 1, 40) ** 1.8
    ys = Y1 - 40 - (Y1 - Y0 - 120) * np.clip(base + rng.normal(0, 0.035, 40), 0, 1)
    grid = blank()
    d = ImageDraw.Draw(grid)
    for k in range(5):
        y = Y0 + 40 + k * (Y1 - Y0 - 80) / 4
        d.line([X0, y, X1, y], fill=(255, 255, 255, 60), width=2)
    for k, ch in enumerate("MTWTFSS"):
        d.text((X0 + 30 + k * (X1 - X0 - 90) / 6, Y0 - 10), ch, font=font("Inter-Bold.otf", 30), fill=(255, 255, 255, 200))
    goal = pill("STATS  ↗", 34, fg=(20, 20, 20), bg=YELLOW, pad=(22, 12), r=14)

    def f(t, fr, a, i):
        g = ease_out((t - (1.25 if FAST else 1.40)) / (0.15 if FAST else 0.4))   
        layer = blank()
        put(layer, grid, W / 2, H / 2, alpha=g)
        p = ease_io((t - 1.38) / 0.52) if FAST else ease_io((t - 1.55) / 2.3)
        n = 1 + p * (len(xs) - 1)
        k = int(n)
        pts = [(xs[j], ys[j]) for j in range(k)]
        if k < len(xs):
            fr_ = n - k
            pts.append((xs[k - 1] + (xs[k] - xs[k - 1]) * fr_, ys[k - 1] + (ys[k] - ys[k - 1]) * fr_))
        if len(pts) > 1:
            fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(fill).polygon(pts + [(pts[-1][0], Y1 - 40), (pts[0][0], Y1 - 40)], fill=(255, 216, 77, 70))
            layer.alpha_composite(fill)
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).line(pts, fill=(255, 216, 77, 200), width=22, joint="curve")
            layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
            dd = ImageDraw.Draw(layer)
            dd.line(pts, fill=(255, 236, 150, 255), width=9, joint="curve")
            ex, ey = pts[-1]
            dd.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=(255, 255, 255))
            put(layer, goal, ex - 120, ey - 70, scale=pop(t, 1.86 if FAST else 3.62, 0.18 if FAST else 0.25, 0.2))   
        out = behind(fr, a, layer)
        top = blank()
        chip(top, 0, "chart grow")
        return over(out, top)
    run("10-chart", f, matte=True)



def fx_pullback():
    WX0, WY0, WX1, WY1 = 40, 240, 1040, 1480
    VX0, VY0, VW = 452, 330, 560
    VH = VW * H / W
    win = Image.new("RGBA", (WX1 - WX0, WY1 - WY0), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    d.rounded_rectangle([0, 0, win.width - 1, win.height - 1], 34, fill=(246, 242, 235, 255))
    for k, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 200, 64)]):
        d.ellipse([28 + k * 32, 28, 48 + k * 32, 48], fill=c)
    d.rounded_rectangle([170, 18, win.width - 40, 58], 18, fill=(232, 226, 216))
    d.text((190, 23), f"{len(ORDER)}-edits.mp4", font=font("Inter-Regular.otf", 26), fill=(110, 104, 96))
    d.rounded_rectangle([28, 90, 392, 700], 24, fill=(255, 255, 255))
    d.text((52, 112), "Working on", font=font("Inter-Bold.otf", 28), fill=(120, 112, 104))
    d.text((52, 148), f"{len(ORDER)} edits", font=font("InstrumentSerif-Regular.ttf", 64), fill=(30, 28, 26))
    win = shadowed(win, 30, (0, 20), 140)
    pad = 90
    items = ["Orbit", "Couch wall", "UI world", "Frame break", "Pull-back reveal"]
    fi = font("Inter-Bold.otf", 29)

    def f(t, fr, a, i):
        p = ease_io((t - 0.90) / 0.8)                         
        bg = np.zeros((H, W, 3), np.uint8); bg[:] = (22, 22, 26)
        canvas = Image.fromarray(bg).convert("RGBA")
        put(canvas, win, (WX0 + WX1) / 2, (WY0 + WY1) / 2, scale=1.25 - 0.25 * p, alpha=p)
        d = ImageDraw.Draw(canvas)
        if p > 0.95:
            for k, it in enumerate(items):
                tk = 2.00 + k * 0.45
                y = WY0 + 280 + k * 66
                done = t >= tk
                d.ellipse([WX0 + 52, y, WX0 + 86, y + 34], fill=(40, 180, 90) if done else None,
                          outline=None if done else (190, 182, 172), width=3)
                if done:
                    d.line([(WX0 + 60, y + 18), (WX0+ 67, y + 25), (WX0 + 79, y + 10)], fill=(255, 255, 255), width=4)
                d.text((WX0 + 100, y + 1), it, font=fi, fill=(30, 28, 26) if done else (175, 168, 160))
        
        x0 = VX0 * p; y0 = VY0 * p; w = W + (VW - W) * p; h = H + (VH - H) * p
        vid = Image.fromarray(fr).resize((int(w), int(h)), Image.BILINEAR)
        vid = rounded(vid, int(28 * p))
        canvas.alpha_composite(vid, (int(x0), int(y0)))
        chip(canvas, 0, "pull-back reveal")
        return np.asarray(canvas.convert("RGB"))
    run("11-pullback", f)



def fx_green():
    bg = Image.new("RGB", (W, H), (247, 243, 236))
    top = np.zeros((560, W, 3), np.float32)
    for x in range(W):
        u = x / W
        top[:, x] = np.array([91, 63, 217]) * (1 - u) + np.array([150, 95, 246]) * u
    bg.paste(Image.fromarray(top.astype(np.uint8)), (0, 0))
    d = ImageDraw.Draw(bg)
    d.text((80, 230), "AI EDITOR  ·  GREEN SCREEN", font=font("Inter-Bold.otf", 34), fill=(230, 222, 255))
    d.text((70, 270), f"{len(ORDER)} EDITS", font=font("Inter-Black.otf", 190), fill=(255, 255, 255))
    d.rounded_rectangle([80, 490, 1000, 512], 11, fill=(255, 255, 255, 90))
    d.rounded_rectangle([0, 540, W, H], 46, fill=(247, 243, 236))
    rows = [("Paper cut", (190, 182, 172)), ("Green screen", (230, 60, 60)), ("Pull-back reveal", (60, 190, 110))]
    for k, (r, c) in enumerate(rows):
        y = 640 + k * 110
        d.ellipse([80, y + 6, 116, y + 42], fill=c)
        d.text((140, y), r, font=font("Inter-Bold.otf", 46), fill=(40, 36, 32))
        d.line([80, y + 80, 1000, y + 80], fill=(228, 220, 210), width=2)
    bgn = np.asarray(bg).astype(np.float32)
    tr = Track()
    st = {}

    def f(t, fr, a, i):
        k = ease_out((t - 1.10) / 0.2)                       
        if k <= 0:
            out = fr
        else:
            scene = bgn.copy()
            
            pb = ease_io((t - 1.4) / 2.0) * 0.70
            cv2.rectangle(scene, (80, 490), (int(80 + 920 * pb), 512), (255, 216, 77), -1)
            cx, cy, topy = tr(a)
            
            rows = np.nonzero((a[::4, ::4, 0] > 0.5).any(1))[0]
            feet = rows.max() * 4 if len(rows) else 1830
            st["feet"] = feet if "feet" not in st else st["feet"] * 0.8 + feet * 0.2
            sh = np.zeros((H, W), np.float32)
            cv2.ellipse(sh, (int(cx), int(st["feet"]) - 6), (200, 34), 0, 0, 360, 0.35, -1)
            sh = cv2.GaussianBlur(sh, (0, 0), 18)[:, :, None]
            scene = scene * (1 - sh)
            comp = a * fr + (1 - a) * scene
            out = (k * comp + (1 - k) * fr).astype(np.uint8)
        layer = blank()
        if t >= 2.52:                                        
            tag = pill("look behind me", 58, fg=(15, 15, 15), bg=YELLOW, pad=(24, 12), r=10, fnt="Inter-Black.otf")
            put(layer, tag, W / 2, 1330, scale=pop(t, 2.52, 0.22, 0.12))
        chip(layer, 0, "green screen")
        return over(out, layer)
    run("12-green", f, matte=True)



def torn(w, h, col, rng):
    pts = []
    for k in range(60):
        u = 2 * math.pi * k / 60
        r = 1 + rng.normal(0, 0.05)
        pts.append((w / 2 + w / 2 * r * math.cos(u) * (1 if abs(math.cos(u)) > .3 else 1), h / 2 + h / 2 * r * math.sin(u)))
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(x + 20, y + 20) for x, y in pts], fill=col)
    return im


def hatch(w, h, col, rng):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 0
    pts = []
    while x < w:
        pts += [(x, rng.uniform(0, 20)), (x + rng.uniform(10, 18), h - rng.uniform(0, 20))]
        x += rng.uniform(14, 22)
    d.line(pts, fill=col, width=7, joint="curve")
    return im


def fx_paper():
    rng = np.random.default_rng(13)
    paper = np.full((H, W, 3), (239, 234, 224), np.float32) + rng.normal(0, 6, (H, W, 1))
    paper = np.clip(paper, 0, 255)
    letters = []
    styles = [((20, 20, 20), (255, 255, 255), "InstrumentSerif-Regular.ttf"), ((255, 255, 255), (20, 20, 20), "Inter-Black.otf"),
              ((255, 216, 77), (20, 20, 20), "DMSerifDisplay-Italic.ttf"), ((70, 90, 200), (255, 255, 255), "Inter-Black.otf")]
    for k, ch in enumerate("PAPERCUT"):
        bgc, fgc, fn = styles[k % 4]
        im = Image.new("RGBA", (106, 136), bgc + (255,))
        f = font(fn, 100)
        tw = ImageDraw.Draw(im).textlength(ch, font=f)
        ImageDraw.Draw(im).text(((106 - tw) / 2, 4), ch, font=f, fill=fgc)
        letters.append(shadowed(im, 6, (0, 5), 120))

    def f(t, fr, a, i):
        if t < 0.70:                                         
            top = blank(); chip(top, 0, "paper cut")
            return over(fr, top)
        b = i // 4                                           
        jr = np.random.default_rng(b)
        j = lambda s=4: jr.uniform(-s, s)
        r2 = np.random.default_rng(5)
        layer = blank()
        put(layer, torn(560, 420, (255, 216, 77, 255), r2), 820 + j(), 1150 + j(), rot=-8 + j(1))
        put(layer, hatch(520, 300, (110, 130, 205, 255), r2), 560 + j(), 430 + j(), rot=4 + j(1))
        put(layer, torn(300, 220, (230, 80, 70, 255), r2), 200 + j(), 1250 + j(), rot=12)
        d = ImageDraw.Draw(layer)
        for (x, y) in ((150, 900), (930, 760), (880, 1400)):
            x += j(); y += j()
            d.line([x - 22, y - 22, x + 22, y + 22], fill=(25, 25, 25), width=7)
            d.line([x - 22, y + 22, x + 22, y - 22], fill=(25, 25, 25), width=7)
        scene = over(paper.astype(np.uint8), layer).astype(np.float32)
        
        m = (a[:, :, 0] * 255).astype(np.uint8)
        dil = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))).astype(np.float32)[:, :, None] / 255
        sh = cv2.GaussianBlur(np.roll(dil[:, :, 0], (14, 10), (0, 1)), (0, 0), 10)[:, :, None]
        scene = scene * (1 - 0.35 * sh)
        scene = dil * 252 + (1 - dil) * scene
        out = (a * fr + (1 - a) * scene).astype(np.uint8)
        top = blank()
        for k, im in enumerate(letters):
            p = pop(t, 0.80 + k * 0.06, 0.18, 0.2)
            rr = np.random.default_rng(k * 7 + b)
            put(top, im, 120 + k * 120, 330 + rr.uniform(-6, 6), scale=p, rot=rr.uniform(-9, 9))
        c = ease_out((t - 2.35) / 0.35)                          
        if c > 0:
            dd = ImageDraw.Draw(top)
            pts = [(540 + 505 * math.cos(u) + j(2), 330 + 130 * math.sin(u) + j(2))
                   for u in np.linspace(-2.8, -2.8 + 2 * math.pi * 1.06 * c, 60)]
            dd.line(pts, fill=(225, 40, 40, 255), width=9, joint="curve")
        chip(top, 0, "paper cut")
        return over(out, top)
    run("13-paper", f, matte=True)



def fx_vertigo():
    SUB, T0, T1 = (1.7, 0.42, 0.62) if FAST else (1.7, 0.50, 1.10)   
    tr = Track(0.08)

    def f(t, fr, a, i):
        cx, cy, topy = tr(a)
        ax, ay = cx, cy - 120
        p = ease_io((t - T0) / (T1 - T0)) - ease_io((t - T1 - 0.05) / (T1 - T0))
        z = SUB + (1.22 - SUB) * p                          
        bg = scale_about(fr, z, ax, ay, cv2.INTER_CUBIC)
        sub = scale_about(fr, SUB, ax, ay, cv2.INTER_CUBIC)
        sa = scale_about(a[:, :, 0], SUB, ax, ay)[:, :, None]
        
        
        twin = scale_about(a[:, :, 0], z, ax, ay)
        hole = cv2.dilate(((twin > 0.5) & (sa[:, :, 0] < 0.3)).astype(np.uint8), np.ones((9, 9), np.uint8))
        if p > 0.02 and hole.any():
            small = cv2.inpaint(cv2.resize(bg, (W // 3, H // 3)), cv2.resize(hole, (W // 3, H // 3)), 7, cv2.INPAINT_TELEA)
            fill = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
            hm = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 4)[:, :, None]
            bg = (hm * fill + (1 - hm) * bg).astype(np.uint8)
        out = (sa * sub + (1 - sa) * bg).astype(np.uint8)
        top = blank()
        caption(top, ["crazy", "illusion"], t, y=1330, size=110, hi=["illusion"], t0=1.75)
        chip(top, 0, "vertigo")
        return over(out, top)
    run("14-vertigo", f, matte=True)



def fx_glass():
    fnt = font("Inter-Black.otf", 300)
    txt = "GLASS"
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    tw = d.textlength(txt, font=fnt)
    sc = min(1.0, (W - 60) / tw)
    big = Image.new("L", (int(tw) + 40, 380), 0)
    ImageDraw.Draw(big).text((20, 0), txt, font=fnt, fill=255)
    big = big.resize((int(big.width * sc), int(big.height * sc)), Image.LANCZOS)
    m.paste(big, (int((W - big.width) / 2), 470))
    M = np.asarray(m, np.float32) / 255
    soft = cv2.GaussianBlur(M, (0, 0), 9)
    gy, gx = np.gradient(soft)
    edge = np.clip(M - cv2.erode(M, np.ones((7, 7), np.uint8)), 0, 1)
    light = np.clip((-gx - gy) * 25, 0, 1)                   
    shadow = cv2.GaussianBlur(np.roll(M, (22, 8), (0, 1)), (0, 0), 16)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def f(t, fr, a, i):
        k = ease_out((t - 0.45) / 0.55)                       
        dy = 60 * (1 - k)
        Mk = np.roll(M, int(dy), 0) * k
        bl = cv2.GaussianBlur(fr, (0, 0), 14).astype(np.float32)
        ref = cv2.remap(bl, xx + gx * 900, yy + gy * 900 + 0, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        ref = np.roll(ref, int(dy), 0)
        glass = np.clip(ref * 1.08 + 28, 0, 255)
        sweep = 0.0
        t_sh = 1.02 if FAST else 3.0                          
        if t > t_sh:
            sx = -300 + (t - t_sh) / 0.6 * (W + 600)
            sweep = np.clip(1 - np.abs((xx + yy * 0.4) - sx - 400) / 90, 0, 1)[:, :, None] * 0.55
        rim = np.roll(np.clip(edge * 0.5 + light, 0, 1), int(dy), 0)[:, :, None] * k
        shd = np.roll(shadow, int(dy), 0)[:, :, None] * 0.28 * k
        out = fr.astype(np.float32) * (1 - shd)
        mk = Mk[:, :, None]
        out = out * (1 - mk) + glass * mk
        out = out + (255 - out) * np.clip(rim + sweep * mk, 0, 1)
        out = (a * fr + (1 - a) * out).astype(np.uint8)
        top = blank()
        chip(top, 0, "glass type")
        return over(out, top)
    run("16-glass", f, matte=True)


SUF = "-16" if SET16 else ""


def fx_check():
    if FAST:                                                  
        fx.ROWS[:] = [(w, tk) for (w, _), tk in zip(fx.ROWS, (1.28, 1.46, 1.64))]

    def f(t, fr, a, i):
        out = behind(fr, a, fx.card(t))
        top = blank()
        chip(top, 0, "checklist")
        return over(out, top)
    run("07-checklist", f, matte=True)


def fx_doodle():
    def extra(layer, t):
        caption(layer, ["comment", "editor"], t, hi=["editor"], t0=0.65, t1=3.6)
        caption(layer, ["peace."], t, hi=["peace."], t0=12.80)
    fx.run_d(JOB / "src/17-doodle.mp4", JOB / "build/17-doodle-cutout.mov", JOB / "outputs/17-doodle.mp4", extra)
    print("wrote", JOB / "outputs/17-doodle.mp4")


def fx_zoom():
    fx.run_a(JOB / "src/05-zoom.mp4", JOB / f"outputs/05-zoom{SUF}.mp4",
             lambda layer, t: caption(layer, ["digital", "zoom"], t, hi=["zoom"], t0=1.86, t1=3.2))
    print("wrote", JOB / f"outputs/05-zoom{SUF}.mp4")


def fx_cover():
    fx.run_c(JOB / "src/15-cover.mp4", JOB / "build/15-cover-cutout.mov", JOB / f"outputs/15-cover{SUF}.mp4")
    print("wrote", JOB / f"outputs/15-cover{SUF}.mp4")


if __name__ == "__main__":
    {"01": fx_orbit, "02": fx_couch, "03": fx_ui, "04": fx_frame, "05": fx_zoom, "06": fx_phone, "07": fx_check,
     "08": fx_headline, "09": fx_zoomthrough, "10": fx_chart, "11": fx_pullback, "12": fx_green, "13": fx_paper,
     "14": fx_vertigo, "15": fx_cover, "16": fx_glass, "17": fx_doodle}[sys.argv[1]]()
