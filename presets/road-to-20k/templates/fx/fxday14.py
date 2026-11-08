# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy", "pillow"]
# ///
"""Retimed effect orchestration example B, retaining original timing/math and neutral sample labels.
From a job fx/ directory: uv run build/fxday14.py <name> ... | all
SEG values and word times are illustrative only and MUST be re-authored for the supplied footage.
Relative sample asset references require user-supplied replacements; no private footage or transcript is included."""
import math, os, sys
from pathlib import Path

if __name__ == "__main__" and not (Path.cwd() / "src").is_dir():
    sys.exit("refusing to render outside a job fx directory that already contains src/.")

os.environ["NOLABEL"] = "1"
sys.path.insert(0, str(Path(__file__).parent))
import fx, fx17  
from fx import W, H, FPS, YELLOW, font, ease_out, ease_io, over  
from fx17 import (blank, put, shadowed, rounded, pop, behind, run, Track, scale_about, pill, polaroid, note)  
import cv2  
import numpy as np  
from PIL import Image, ImageDraw, ImageFilter  

JOB = Path.cwd()
A = JOB / "assets"
SEG = {"couch": (47, 113), "glass": (113, 164), "checklist": (164, 330), "doodle": (330, 495), "phone": (495, 615),
       "green": (615, 756), "chart": (756, 823), "headline": (918, 1017), "zoom": (1017, 1049), "frame": (1049, 1142),
       "orbit": (1142, 1270)}


def rel(name, word_t):
    return word_t - SEG[name][0] / FPS



def fx_couch():
    r = lambda w: rel("couch", w)
    spots = [("sample-b-1.jpg", "SCENE B", 175, 560, -7, r(2.00)), ("sample-c-1.jpg", "SCENE C", 890, 540, 6, r(2.42)),
             ("sample-b-2.jpg", "SCENE B", 380, 400, 4, r(2.72)), ("sample-c-2.jpg", "SCENE C", 700, 380, -5, r(2.88)),
             ("sample-b-3.jpg", "SCENE B", 185, 900, 5, r(3.08)), ("sample-c-3.jpg", "SCENE C", 885, 880, -6, r(3.20))]
    cards = [(polaroid(A / p, 230, tag=tag), x, y, rr, t0) for p, tag, x, y, rr, t0 in spots]

    def f(t, fr, a, i):
        wall = blank()
        for im, x, y, rr, t0 in cards:
            k = pop(t, t0, 0.3, 0.15)
            put(wall, im, x, y, scale=0.7 + 0.3 * k if k else 0, rot=rr + 8 * (1 - min(k, 1)), alpha=min(1, k * 2))
        return behind(fr, a, wall)
    run("couch", f, matte=True)



def fx_glass():
    fnt = font("Inter-Black.otf", 300)
    txt = "WRAP-UP"
    m = Image.new("L", (W, H), 0)
    tw = ImageDraw.Draw(m).textlength(txt, font=fnt)
    sc = min(1.0, (W - 60) / tw)
    big = Image.new("L", (int(tw) + 40, 380), 0)
    ImageDraw.Draw(big).text((20, 0), txt, font=fnt, fill=255)
    big = big.resize((int(big.width * sc), int(big.height * sc)), Image.LANCZOS)
    m.paste(big, (int((W - big.width) / 2), 300))
    M = np.asarray(m, np.float32) / 255
    soft = cv2.GaussianBlur(M, (0, 0), 9)
    gy, gx = np.gradient(soft)
    edge = np.clip(M - cv2.erode(M, np.ones((7, 7), np.uint8)), 0, 1)
    light = np.clip((-gx - gy) * 25, 0, 1)
    shadow = cv2.GaussianBlur(np.roll(M, (22, 8), (0, 1)), (0, 0), 16)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t_in, t_sh = 0.10, rel("glass", 5.03)                     

    def f(t, fr, a, i):
        k = ease_out((t - t_in) / 0.5)
        dy = 60 * (1 - k)
        Mk = np.roll(M, int(dy), 0) * k
        bl = cv2.GaussianBlur(fr, (0, 0), 14).astype(np.float32)
        ref = np.roll(cv2.remap(bl, xx + gx * 900, yy + gy * 900, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), int(dy), 0)
        glass = np.clip(ref * 1.08 + 28, 0, 255)
        sweep = 0.0
        if t > t_sh:
            sx = -300 + (t - t_sh) / 0.6 * (W + 600)
            sweep = np.clip(1 - np.abs((xx + yy * 0.4) - sx - 400) / 90, 0, 1)[:, :, None] * 0.55
        rim = np.roll(np.clip(edge * 0.5 + light, 0, 1), int(dy), 0)[:, :, None] * k
        shd = np.roll(shadow, int(dy), 0)[:, :, None] * 0.28 * k
        out = fr.astype(np.float32) * (1 - shd)
        mk = Mk[:, :, None]
        out = out * (1 - mk) + glass * mk
        out = out + (255 - out) * np.clip(rim + sweep * mk, 0, 1)
        return (a * fr + (1 - a) * out).astype(np.uint8)
    run("glass", f, matte=True)



def fx_checklist():
    r = lambda w: rel("checklist", w)
    rows = [("lock in", r(7.54)), ("be present", r(8.32)), ("breathe", r(9.31))]
    tin, tout = 0.15, SEG["checklist"][1] / FPS - SEG["checklist"][0] / FPS - 0.45
    X0, Y0, X1, Y1 = 90, 170, 990, 560                       

    def card(t):
        layer = blank()
        k = ease_out((t - tin) / 0.45) * (1 - ease_io((t - tout) / 0.35))
        if k <= 0:
            return layer
        c = blank()
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([X0, Y0, X1, Y1], 48, fill=(16, 16, 20, 205), outline=(255, 255, 255, 40), width=2)
        d.text((X0 + 56, Y0 + 30), "today:", font=font("Inter-Bold.otf", 44), fill=(255, 255, 255, 150))
        fr_ = font("Inter-Black.otf", 76)
        for j, (word, tw) in enumerate(rows):
            y = Y0 + 100 + j * 92
            p = ease_out((t - tw) / 0.18)
            pp = 1 + 0.18 * math.sin(math.pi * min(max((t - tw) / 0.22, 0), 1))
            bs = 70 * pp
            bx, by = X0 + 56 + 35 - bs / 2, y + 44 - bs / 2
            if p > 0:
                d.rounded_rectangle([bx, by, bx + bs, by + bs], 18, fill=YELLOW)
                pts = [(bx + bs * .24, by + bs * .52), (bx + bs * .43, by + bs * .70), (bx + bs * .77, by + bs * .30)]
                q = p * 2
                seg1 = pts[1] if q >= 1 else tuple(np.add(pts[0], np.subtract(pts[1], pts[0]) * q))
                d.line([pts[0], seg1], fill=(15, 15, 15), width=11, joint="curve")
                if q > 1:
                    d.line([pts[1], tuple(np.add(pts[1], np.subtract(pts[2], pts[1]) * (q - 1)))], fill=(15, 15, 15), width=11, joint="curve")
            else:
                d.rounded_rectangle([bx, by, bx + bs, by + bs], 18, outline=(255, 255, 255, 110), width=6)
            d.text((X0 + 160, y), word, font=fr_, fill=(255, 255, 255, 255) if p > 0 else (255, 255, 255, 105))
        c = c.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -40 * (1 - k)))
        c.putalpha(c.getchannel("A").point(lambda v: int(v * k)))
        layer.alpha_composite(c)
        return layer

    run("checklist", lambda t, fr, a, i: behind(fr, a, card(t)), matte=True)



def fx_doodle():
    src, matte, out = JOB / "src/doodle.mp4", JOB / "build/doodle-cutout.mov", JOB / "outputs/doodle.mp4"
    fx.run_d(src, matte, out)                                 
    print("wrote", out)



def fx_phone():
    PW, PH = 400, 820
    t0 = 0.30
    msgs = [("SAMPLE", t0), ("SAMPLE!", t0 + 0.5), ("another sample", t0 + 1.0), ("sample three", t0 + 1.5),
            ("SAMPLE", t0 + 2.0), ("sample four", t0 + 2.5)]
    fm = font("Inter-Regular.otf", 30)

    def phone(t):
        im = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, PW - 1, PH - 1], 64, fill=(18, 18, 20))
        d.rounded_rectangle([12, 12, PW - 13, PH - 13], 54, fill=(0, 0, 0))
        d.rounded_rectangle([PW / 2 - 60, 26, PW / 2 + 60, 58], 16, fill=(18, 18, 20))
        fb = font("Inter-Bold.otf", 32)
        d.text((PW / 2 - d.textlength("Comments", font=fb) / 2, 100), "Comments", font=fb, fill=(255, 255, 255))
        n = sum(1 for _, tt in msgs if t >= tt)
        if n:
            badge = f"{n} unanswered"
            fbd = font("Inter-Bold.otf", 22)
            bw = d.textlength(badge, font=fbd) + 28
            d.rounded_rectangle([PW / 2 - bw / 2, 146, PW / 2 + bw / 2, 180], 17, fill=(230, 50, 50))
            d.text((PW / 2 - bw / 2 + 14, 150), badge, font=fbd, fill=(255, 255, 255))
        d.line([12, 204, PW - 12, 204], fill=(40, 40, 44), width=2)
        y = 232
        for text, tt in msgs:
            k = pop(t, tt, 0.25, 0.1)
            if k <= 0:
                break
            tw = d.textlength(text, font=fm)
            bw, bh = tw + 44, 62
            bub = Image.new("RGBA", (int(bw), bh), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bub)
            bd.rounded_rectangle([0, 0, bw - 1, bh - 1], 30, fill=(44, 44, 48))
            bd.text((22, 13), text, font=fm, fill=YELLOW if "SAMPLE" in text else (255, 255, 255))
            put(im, bub, 28 + bw / 2, y + bh / 2, scale=0.6 + 0.4 * k, alpha=min(1, k * 1.5))
            y += bh + 16
        return shadowed(im, 26, (0, 20), 130)

    def f(t, fr, a, i):
        layer = blank()
        k = ease_out(t / 0.45)
        put(layer, phone(t), 205, 560 + 900 * (1 - k), scale=0.80, rot=-6 * (1 - k) + 3 + 1.2 * math.sin(t * 1.4))
        return over(fr, layer)
    run("phone", f)



def fx_green():
    bg = Image.new("RGB", (W, H), (247, 243, 236))
    top = np.zeros((560, W, 3), np.float32)
    for x in range(W):
        u = x / W
        top[:, x] = np.array([91, 63, 217]) * (1 - u) + np.array([150, 95, 246]) * u
    bg.paste(Image.fromarray(top.astype(np.uint8)), (0, 0))
    d = ImageDraw.Draw(bg)
    d.text((80, 230), "SAMPLE PROJECT  ·  THE WORKFLOW", font=font("Inter-Bold.otf", 34), fill=(230, 222, 255))
    d.text((70, 270), "SAMPLE", font=font("Inter-Black.otf", 190), fill=(255, 255, 255))
    d.rounded_rectangle([80, 490, 1000, 512], 11, fill=(255, 255, 255, 90))
    d.rounded_rectangle([0, 540, W, H], 46, fill=(247, 243, 236))
    rows = [("Import clips", (60, 190, 110)), ("Create an edit", (255, 190, 60)), ("Review + export", (190, 182, 172))]
    for k, (txt, c) in enumerate(rows):
        y = 640 + k * 110
        d.ellipse([80, y + 6, 116, y + 42], fill=c)
        d.text((140, y), txt, font=font("Inter-Bold.otf", 46), fill=(40, 36, 32))
        d.line([80, y + 80, 1000, y + 80], fill=(228, 220, 210), width=2)
    bgn = np.asarray(bg).astype(np.float32)
    tr, st = Track(), {}
    t_sys, t_cap = rel("green", 22.74), rel("green", 24.28)    

    def f(t, fr, a, i):
        k = ease_out((t - t_sys) / 0.2)
        if k <= 0:
            out = fr
        else:
            scene = bgn.copy()
            pb = ease_io((t - t_sys - 0.2) / 2.0) * 0.70
            cv2.rectangle(scene, (80, 490), (int(80 + 920 * pb), 512), (255, 216, 77), -1)
            cx, cy, topy = tr(a)
            rws = np.nonzero((a[::4, ::4, 0] > 0.5).any(1))[0]
            feet = rws.max() * 4 if len(rws) else 1830
            st["feet"] = feet if "feet" not in st else st["feet"] * 0.8 + feet * 0.2
            sh = np.zeros((H, W), np.float32)
            cv2.ellipse(sh, (int(cx), int(st["feet"]) - 6), (200, 34), 0, 0, 360, 0.35, -1)
            sh = cv2.GaussianBlur(sh, (0, 0), 18)[:, :, None]
            comp = a * fr + (1 - a) * scene * (1 - sh)
            out = (k * comp + (1 - k) * fr).astype(np.uint8)
        layer = blank()
        if t >= t_cap:
            tag = pill("ready to capture", 58, fg=(15, 15, 15), bg=YELLOW, pad=(24, 12), r=10, fnt="Inter-Black.otf")
            put(layer, tag, W / 2, 1560, scale=pop(t, t_cap, 0.22, 0.12))
        return over(out, layer)
    run("green", f, matte=True)



def fx_chart():
    X0, Y0, X1, Y1 = 110, 230, 970, 760
    rng = np.random.default_rng(14)
    xs = np.linspace(X0 + 30, X1 - 60, 40)
    base = np.r_[np.full(30, 0.04), np.linspace(0.04, 1.0, 10) ** 1.3]   
    ys = Y1 - 40 - (Y1 - Y0 - 120) * np.clip(base + rng.normal(0, 0.015, 40), 0, 1)
    grid = blank()
    d = ImageDraw.Draw(grid)
    for k in range(5):
        y = Y0 + 40 + k * (Y1 - Y0 - 80) / 4
        d.line([X0, y, X1, y], fill=(255, 255, 255, 60), width=2)
    for k, lab in enumerate(["A", "B", "C", "D", "E", "F", "G"]):
        d.text((X0 + 20 + k * (X1 - X0 - 100) / 6, Y0 - 10), lab, font=font("Inter-Bold.otf", 28), fill=(255, 255, 255, 200))
    tag = pill("PROGRESS  ↗", 34, fg=(20, 20, 20), bg=YELLOW, pad=(22, 12), r=14)
    t_first, t_quick = rel("chart", 26.37), rel("chart", 27.01)

    def f(t, fr, a, i):
        layer = blank()
        put(layer, grid, W / 2, H / 2, alpha=ease_out((t - 0.05) / 0.3))
        p = ease_io((t - 0.15) / (t_quick - 0.15))
        n = 1 + p * (len(xs) - 1)
        k = int(n)
        pts = [(xs[j], ys[j]) for j in range(k)]
        if k < len(xs):
            pts.append((xs[k - 1] + (xs[k] - xs[k - 1]) * (n - k), ys[k - 1] + (ys[k] - ys[k - 1]) * (n - k)))
        if len(pts) > 1:
            fill = blank()
            ImageDraw.Draw(fill).polygon(pts + [(pts[-1][0], Y1 - 40), (pts[0][0], Y1 - 40)], fill=(255, 216, 77, 70))
            layer.alpha_composite(fill)
            glow = blank()
            ImageDraw.Draw(glow).line(pts, fill=(255, 216, 77, 200), width=22, joint="curve")
            layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
            dd = ImageDraw.Draw(layer)
            dd.line(pts, fill=(255, 236, 150, 255), width=9, joint="curve")
            ex, ey = pts[-1]
            dd.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=(255, 255, 255))
            put(layer, tag, ex - 160, ey - 70, scale=pop(t, t_first + 0.2, 0.25, 0.2))
        return behind(fr, a, layer)
    run("chart", f, matte=True)



def fx_headline():
    r = lambda w: rel("headline", w)
    spec = [("“try a different approach”", "paper", 360, 230, 330, -3, r(30.98)), ("first approach", "black", 300, 860, 300, 4, r(31.27)),
            ("review.", "sticky", 220, 860, 560, -5, r(31.61)), ("creative", "paper", 220, 170, 600, 5, r(32.07)),
            ("editor", "paper", 300, 200, 820, -4, r(32.29)), ("NEW approach", "black", 320, 870, 800, 3, r(32.29) + 0.15)]
    notes = [(note(*s[:3]), *s[3:]) for s in spec]
    t_circ, t_x = r(32.75), r(33.00)                           

    def f(t, fr, a, i):
        wall = blank()
        for im, x, y, rr, t0 in notes:
            p = pop(t, t0, 0.22, 0.18)
            put(wall, im, x, y, scale=1.35 - 0.35 * p if p else 0, rot=rr, alpha=min(1, p * 2))
        d = ImageDraw.Draw(wall)
        c = ease_out((t - t_circ) / 0.3)
        if c > 0:
            pts = [(870 + 185 * math.cos(u) + 6 * math.sin(5 * u), 800 + 80 * math.sin(u))
                   for u in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.08 * c, 60)]
            d.line(pts, fill=(230, 40, 40, 255), width=10, joint="curve")
        xk = ease_out((t - t_x) / 0.25)
        if xk > 0:
            for (ax, ay, bx, by) in ((730, 250, 990, 350), (730, 350, 990, 250)):
                d.line([(ax, ay), (ax + (bx - ax) * xk, ay + (by - ay) * xk)], fill=(230, 40, 40, 255), width=12)
        return behind(fr, a, wall)
    run("headline", f, matte=True)



def fx_zoom():
    t_w = rel("zoom", 34.78)
    fx.scale_at = lambda t: 1.0 + 0.05 * ease_out(t / max(t_w, 0.01)) + 0.40 * ease_out((t - t_w) / 0.10)
    fx.run_a(JOB / "src/zoom.mp4", JOB / "outputs/zoom.mp4")
    print("wrote", JOB / "outputs/zoom.mp4")



def fx_frame():
    
    
    CX0, CY0, CX1, CY1 = 260, 1150, 820, 1650
    S, PX, PY = 0.72, 540, 1480
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([CX0, CY0, CX1, CY1], 44, fill=255)
    card = np.asarray(mask, np.float32)[:, :, None] / 255
    border = blank()
    ImageDraw.Draw(border).rounded_rectangle([CX0 - 7, CY0 - 7, CX1 + 7, CY1 + 7], 50, outline=(255, 255, 255, 255), width=8)
    below = (np.arange(H)[:, None, None] < CY1 - 40).astype(np.float32)
    t_tune, t_fut = rel("frame", 35.84), rel("frame", 36.47)    

    def f(t, fr, a, i):
        p = ease_io((t - (t_tune - 0.2)) / 0.55)
        s = 1 + (S - 1) * p
        vid = scale_about(fr, s, PX, PY)
        al = scale_about(a[:, :, 0], s, PX, PY, border=cv2.BORDER_CONSTANT)[:, :, None]   
        bg = (cv2.resize(cv2.GaussianBlur(cv2.resize(fr, (W // 8, H // 8)), (0, 0), 6), (W, H)) * 0.45).astype(np.uint8)
        cm = card * p + (1 - p)
        out = (cm * vid + (1 - cm) * bg).astype(np.uint8)
        if p > 0.98:
            out = over(out, border)
        brk = ease_out((t - t_fut) / 0.12)
        if brk > 0:
            m = al * below * brk * (1 - card)
            out = (m * vid + (1 - m) * out).astype(np.uint8)
        return out
    run("frame", f, matte=True)



def fx_orbit():
    tiles = [shadowed(pill(t, 40, dot=c)) for t, c in
             [("sample goal", (255, 190, 60)), ("creative", (255, 90, 90)), ("editor", (90, 160, 255)),
              ("new ideas", (150, 110, 255)), ("in progress", (60, 200, 120))]]
    for p in ("sample-c-1.jpg", "sample-b-1.jpg"):
        im = Image.open(A / p).convert("RGB").resize((170, 302))
        tiles.append(shadowed(rounded(Image.fromarray(np.asarray(im)), 22)))
    n, tr = len(tiles), Track()
    t_goal = rel("orbit", 38.50)                                 

    def f(t, fr, a, i):
        cx, cy, top = tr(a)
        ocx, ocy = cx, top + 620                               
        grow = ease_out((t - t_goal) / 0.6)
        back, front = blank(), blank()
        for j, im in enumerate(tiles):
            th = 2 * math.pi * j / n + t * 2 * math.pi / 5.0
            x = ocx + 420 * grow * math.cos(th)
            y = ocy + 150 * grow * math.sin(th) - 40 * math.cos(th)
            depth = math.sin(th)
            s = 0.82 + 0.22 * (depth + 1) / 2
            put(front if depth > 0 else back, im, x, y, scale=s * grow, alpha=min(1, grow * 1.4) * (1 if depth > 0 else .85))
        return over(behind(fr, a, back), front)
    run("orbit", f, matte=True)


FX = {"couch": fx_couch, "glass": fx_glass, "checklist": fx_checklist, "doodle": fx_doodle, "phone": fx_phone,
      "green": fx_green, "chart": fx_chart, "headline": fx_headline, "zoom": fx_zoom, "frame": fx_frame, "orbit": fx_orbit}

if __name__ == "__main__":
    for name in (FX if sys.argv[1] == "all" else sys.argv[1:]):
        FX[name]()
