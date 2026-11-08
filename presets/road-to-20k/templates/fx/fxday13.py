# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy", "pillow"]
# ///
"""Retimed effect orchestration example A, retaining original timing/math and neutral sample labels.
From a job fx/ directory: uv run build/fxday13.py <name> ... | all
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
from fx17 import (blank, put, shadowed, rounded, pop, behind, run, Track, scale_about, pill, polaroid, note,  
                  torn, hatch)
import cv2  
import numpy as np  
from PIL import Image, ImageDraw, ImageFilter  

JOB = Path.cwd()
A = JOB / "assets"
SEG = {"couch": (61, 176), "chart": (176, 236), "phone": (236, 340), "ui": (340, 461), "headline": (526, 659),
       "zoom": (713, 743), "zoomthrough": (776, 879), "paper": (990, 1063), "vertigo": (1063, 1128),
       "orbit": (1362, 1489), "pullback": (1573, 1675)}


def rel(name, word_t):
    """canonical transcript time -> seconds from the segment start"""
    return word_t - SEG[name][0] / FPS



def fx_couch():
    t_reel, t_ago = rel("couch", 4.08), rel("couch", 5.24)        
    spots = [("sample-a-1.jpg", "SCENE A", 175, 560, -7, t_reel), ("sample-b-1.jpg", "SCENE B", 890, 540, 6, t_reel + 0.15),
             ("sample-a-2.jpg", "SCENE A", 380, 420, 4, t_reel + 0.30), ("sample-b-2.jpg", "SCENE B", 700, 400, -5, t_reel + 0.45),
             ("sample-a-3.jpg", "SCENE A", 185, 900, 5, t_ago - 0.15), ("sample-b-3.jpg", "SCENE B", 885, 880, -6, t_ago)]
    cards = [(polaroid(A / p, 230, tag=tag), x, y, r, t0) for p, tag, x, y, r, t0 in spots]

    def f(t, fr, a, i):
        wall = blank()
        for im, x, y, r, t0 in cards:
            k = pop(t, t0, 0.3, 0.15)
            put(wall, im, x, y, scale=0.7 + 0.3 * k if k else 0, rot=r + 8 * (1 - min(k, 1)), alpha=min(1, k * 2))
        return behind(fr, a, wall)
    run("couch", f, matte=True)



def fx_chart():
    X0, Y0, X1, Y1 = 110, 260, 970, 800
    rng = np.random.default_rng(13)
    xs = np.linspace(X0 + 30, X1 - 60, 40)
    base = np.r_[np.linspace(0.08, 0.16, 28), np.linspace(0.16, 1.0, 12) ** 1.5]   
    ys = Y1 - 40 - (Y1 - Y0 - 120) * np.clip(base + rng.normal(0, 0.02, 40), 0, 1)
    grid = blank()
    d = ImageDraw.Draw(grid)
    for k in range(5):
        y = Y0 + 40 + k * (Y1 - Y0 - 80) / 4
        d.line([X0, y, X1, y], fill=(255, 255, 255, 60), width=2)
    for k, lab in enumerate(["A", "B", "C", "D", "E", "F", "G"]):
        d.text((X0 + 20 + k * (X1 - X0 - 100) / 6, Y0 - 10), lab, font=font("Inter-Bold.otf", 28), fill=(255, 255, 255, 200))
    tag = pill("VIEWS  ↗", 34, fg=(20, 20, 20), bg=YELLOW, pad=(22, 12), r=14)
    t_pop, t_off = rel("chart", 6.37), rel("chart", 6.67)            

    def f(t, fr, a, i):
        g = ease_out((t - 0.05) / 0.3)
        layer = blank()
        put(layer, grid, W / 2, H / 2, alpha=g)
        p = ease_io((t - 0.15) / (t_off + 0.1 - 0.15))
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
            put(layer, tag, ex - 130, ey - 70, scale=pop(t, t_off, 0.25, 0.2))
        return behind(fr, a, layer)
    run("chart", f, matte=True)



def fx_phone():
    PW, PH = 400, 820
    t_send = rel("phone", 8.05)                                     
    msgs = [("l", "SAMPLE", t_send + 0.20), ("l", "SAMPLE 🙏".replace(" 🙏", "!"), t_send + 0.85),
            ("l", "need this SAMPLE", t_send + 1.55), ("l", "SAMPLE pls", t_send + 2.25),
            ("r", "sample reply", t_send + 2.95)]
    fm = font("Inter-Regular.otf", 30)

    def phone(t):
        im = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, PW - 1, PH - 1], 64, fill=(18, 18, 20))
        d.rounded_rectangle([12, 12, PW - 13, PH - 13], 54, fill=(0, 0, 0))
        d.rounded_rectangle([PW / 2 - 60, 26, PW / 2 + 60, 58], 16, fill=(18, 18, 20))
        d.text((PW / 2 - d.textlength("Comments", font=font("Inter-Bold.otf", 32)) / 2, 100), "Comments",
               font=font("Inter-Bold.otf", 32), fill=(255, 255, 255))
        d.text((PW / 2 - d.textlength("sample conversation", font=font("Inter-Regular.otf", 22)) / 2, 148), "sample conversation",
               font=font("Inter-Regular.otf", 22), fill=(150, 150, 158))
        d.line([12, 204, PW - 12, 204], fill=(40, 40, 44), width=2)
        y = 232
        for side, text, t0 in msgs:
            k = pop(t, t0, 0.25, 0.1)
            if k <= 0:
                break
            tw = d.textlength(text, font=fm)
            bw, bh = tw + 44, 62
            x0 = 28 if side == "l" else PW - 28 - bw
            col = (44, 44, 48) if side == "l" else (10, 132, 255)
            bub = Image.new("RGBA", (int(bw), bh), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bub)
            bd.rounded_rectangle([0, 0, bw - 1, bh - 1], 30, fill=col)
            bd.text((22, 13), text, font=fm, fill=YELLOW if text.startswith("SAMPLE") else (255, 255, 255))
            put(im, bub, x0 + bw / 2, y + bh / 2, scale=0.6 + 0.4 * k, alpha=min(1, k * 1.5))
            y += bh + 16
        return shadowed(im, 26, (0, 20), 130)

    def f(t, fr, a, i):
        layer = blank()
        k = ease_out(t / 0.45)
        put(layer, phone(t), 205, 560 + 900 * (1 - k), scale=0.80, rot=-6 * (1 - k) + 3 + 1.2 * math.sin(t * 1.4))
        return over(fr, layer)
    run("phone", f)



def fx_ui():
    WX0, WY0, WX1, WY1 = 90, 230, 990, 860
    thumbs = [rounded(Image.open(A / f"thumb{k}.jpg").convert("RGB").resize((108, 192)), 14) for k in range(1, 6)]
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
    fp = font("Inter-Regular.otf", 38)
    t_onb, t_ai = rel("ui", 13.03), rel("ui", 14.37)                

    def f(t, fr, a, i):
        layer = blank()
        k = ease_out((t - 0.05) / 0.4)
        put(layer, base, (WX0 + WX1) / 2, (WY0 + WY1) / 2 + 40 * (1 - k), alpha=k)
        d = ImageDraw.Draw(layer)
        ox, oy = WX0, WY0 + int(40 * (1 - k))
        if k > 0.5:
            landed = 0
            for j, th in enumerate(thumbs):
                t0 = t_onb - 0.6 + j * 0.2
                p = ease_out((t - t0) / 0.35)
                if p <= 0:
                    if j == 0:
                        d.text((ox + 300, oy + 300), "drop clips here", font=fp, fill=(160, 150, 140))
                    continue
                landed += 1
                put(layer, th, ox + 110 + j * 134, oy + 322 - 520 * (1 - p), rot=(1 - p) * (20 - j * 9))
            if landed == len(thumbs):
                put(layer, pill("RAW CLIPS", 28, fg=(20, 20, 20), bg=YELLOW, pad=(18, 10), r=8), ox + 800, oy + 230,
                    scale=pop(t, t_onb + 0.45, 0.2))
            typed = "edit these sample clips"[: max(0, int((t - (t_ai - 0.5)) / 0.045))]
            d.rounded_rectangle([ox + 48, oy + 470, ox + WX1 - WX0 - 48, oy + 560], 22, fill=(255, 255, 255))
            d.text((ox + 78, oy + 492), typed or "How can I help you today?", font=fp,
                   fill=(30, 30, 30) if typed else (165, 158, 150))
            if typed and (i // 8) % 2 == 0:
                tw = d.textlength(typed, font=fp)
                d.line([ox + 82 + tw, oy + 494, ox + 82 + tw, oy + 538], fill=(30, 30, 30), width=3)
        back = blank()                                   
        back.alpha_composite(layer)                      
        return behind(fr, a, back)
    run("ui", f, matte=True)



def fx_headline():
    r = lambda w: rel("headline", w)
    spec = [("New idea", "black", 260, 210, 300, -5, r(19.01)), ("first step", "paper", 340, 850, 280, 4, r(18.41)),
            ("review pass", "sticky", 330, 200, 720, 5, r(20.23)), ("“try this”", "paper", 300, 880, 690, -4, r(20.99)),
            ("editing workflow", "paper", 360, 860, 860, 3, r(21.25)), ("SCENE C", "black", 240, 190, 870, -6, r(21.69))]
    notes = [(note(*s[:3]), *s[3:]) for s in spec]
    t_circ = r(21.25)                                                

    def f(t, fr, a, i):
        wall = blank()
        for im, x, y, rr, t0 in notes:
            p = pop(t, t0, 0.22, 0.18)
            put(wall, im, x, y, scale=1.35 - 0.35 * p if p else 0, rot=rr, alpha=min(1, p * 2))
        c = ease_out((t - t_circ) / 0.35)
        if c > 0:
            d = ImageDraw.Draw(wall)
            pts = [(200 + 180 * math.cos(u) + 6 * math.sin(5 * u), 730 + 80 * math.sin(u))
                   for u in np.linspace(-2.6, -2.6 + 2 * math.pi * 1.08 * c, 60)]
            d.line(pts, fill=(230, 40, 40, 255), width=10, joint="curve")
        return behind(fr, a, wall)
    run("headline", f, matte=True)



def fx_zoom():
    t_dude = rel("zoom", 24.56)
    fx.scale_at = lambda t: 1.0 + 0.06 * ease_out(t / max(t_dude, 0.01)) + 0.40 * ease_out((t - t_dude) / 0.12)
    fx.run_a(JOB / "src/zoom.mp4", JOB / "outputs/zoom.mp4")
    print("wrote", JOB / "outputs/zoom.mp4")



def fx_zoomthrough():
    CUT = 27 / FPS
    det = cv2.FaceDetectorYN_create(str(fx.ROOT / "assets/models/face_detection_yunet_2023mar.onnx"), "", (W, H), score_threshold=0.6)
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
            st.setdefault("a", anchor(fr))
            p = (t - 0.35) / (CUT - 0.35)                       
            s = 1 + 6 * max(0, p) ** 2.4
            return blurzoom(fr, s, *st["a"]) if p > 0 else fr
        st.setdefault("b", (W / 2, H * 0.45))
        p = ease_out((t - CUT) / 0.45)
        s = 1 + 2.5 * (1 - p)
        return blurzoom(fr, s, *st["b"]) if s > 1.01 else fr
    run("zoomthrough", f)



def fx_paper():
    rng = np.random.default_rng(13)
    paper = np.clip(np.full((H, W, 3), (239, 234, 224), np.float32) + rng.normal(0, 6, (H, W, 1)), 0, 255)
    styles = [((20, 20, 20), (255, 255, 255), "InstrumentSerif-Regular.ttf"), ((255, 255, 255), (20, 20, 20), "Inter-Black.otf"),
              ((255, 216, 77), (20, 20, 20), "DMSerifDisplay-Italic.ttf"), ((70, 90, 200), (255, 255, 255), "Inter-Black.otf")]
    letters = []
    for k, ch in enumerate("STORY"):
        bgc, fgc, fn = styles[k % 4]
        im = Image.new("RGBA", (130, 166), bgc + (255,))
        f = font(fn, 124)
        tw = ImageDraw.Draw(im).textlength(ch, font=f)
        ImageDraw.Draw(im).text(((130 - tw) / 2, 4), ch, font=f, fill=fgc)
        letters.append(shadowed(im, 6, (0, 5), 120))
    T_IN, T_ACTOR = rel("paper", 34.08), rel("paper", 34.61)        

    def f(t, fr, a, i):
        if t < T_IN:
            return fr
        b = i // 4                                              
        jr = np.random.default_rng(b)
        j = lambda s=4: jr.uniform(-s, s)
        r2 = np.random.default_rng(5)
        layer = blank()
        put(layer, torn(560, 420, (255, 216, 77, 255), r2), 820 + j(), 1150 + j(), rot=-8 + j(1))
        put(layer, hatch(520, 300, (110, 130, 205, 255), r2), 560 + j(), 560 + j(), rot=4 + j(1))
        put(layer, torn(300, 220, (230, 80, 70, 255), r2), 200 + j(), 1250 + j(), rot=12)
        d = ImageDraw.Draw(layer)
        for (x, y) in ((150, 900), (930, 760), (880, 1500)):
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
            p = pop(t, T_ACTOR + k * 0.06, 0.18, 0.2)
            rr = np.random.default_rng(k * 7 + b)
            put(top, im, W / 2 + (k - 2) * 150, 300 + rr.uniform(-6, 6), scale=p, rot=rr.uniform(-9, 9))
        c = ease_out((t - (T_ACTOR + 0.5)) / 0.35)
        if c > 0:
            dd = ImageDraw.Draw(top)
            pts = [(540 + 440 * math.cos(u) + j(2), 300 + 140 * math.sin(u) + j(2))
                   for u in np.linspace(-2.8, -2.8 + 2 * math.pi * 1.06 * c, 60)]
            dd.line(pts, fill=(225, 40, 40, 255), width=9, joint="curve")
        return over(out, top)
    run("paper", f, matte=True)



def fx_vertigo():
    SUB = 1.3                                                   
    T0, T1 = rel("vertigo", 35.98) - 0.05, rel("vertigo", 36.33) + 0.05   
    tr = Track(0.08)

    def f(t, fr, a, i):
        cx, cy, topy = tr(a)
        ax, ay = cx, cy - 120
        p = ease_io((t - T0) / (T1 - T0)) - ease_io((t - T1 - 0.05) / (T1 - T0))
        z = SUB + (1.0 - SUB) * p
        bg = scale_about(fr, max(z, 1.0), ax, ay, cv2.INTER_CUBIC)
        sub = scale_about(fr, SUB, ax, ay, cv2.INTER_CUBIC)
        sa = scale_about(a[:, :, 0], SUB, ax, ay)[:, :, None]
        twin = scale_about(a[:, :, 0], z, ax, ay)
        hole = cv2.dilate(((twin > 0.5) & (sa[:, :, 0] < 0.3)).astype(np.uint8), np.ones((9, 9), np.uint8))
        if p > 0.02 and hole.any():
            small = cv2.inpaint(cv2.resize(bg, (W // 3, H // 3)), cv2.resize(hole, (W // 3, H // 3)), 7, cv2.INPAINT_TELEA)
            fill = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC)
            hm = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 4)[:, :, None]
            bg = (hm * fill + (1 - hm) * bg).astype(np.uint8)
        
        if p <= 0.001:
            return fr
        k = min(1.0, p * 4)
        out = (sa * sub + (1 - sa) * bg).astype(np.float32)
        return (k * out + (1 - k) * fr).astype(np.uint8)
    run("vertigo", f, matte=True)



def fx_orbit():
    tiles = [shadowed(pill(t, 40, dot=c)) for t, c in
             [("new idea", (255, 90, 90)), ("sample topic", (90, 160, 255)), ("creative work", (255, 190, 60)),
              ("next step", (150, 110, 255)), ("review edit", (60, 200, 120))]]
    for p in ("sample-b-1.jpg", "thumb3.jpg"):
        im = Image.open(A / p).convert("RGB").resize((170, 302))
        tiles.append(shadowed(rounded(Image.fromarray(np.asarray(im)), 22)))
    n, tr = len(tiles), Track()
    t_goal = rel("orbit", 45.87)                                   

    def f(t, fr, a, i):
        cx, cy, top = tr(a)
        ocx, ocy = cx, top + 720                        
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



def fx_pullback():
    WX0, WY0, WX1, WY1 = 40, 200, 1040, 1440
    VX0, VY0, VW = 452, 290, 560
    VH = VW * H / W
    win = Image.new("RGBA", (WX1 - WX0, WY1 - WY0), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    d.rounded_rectangle([0, 0, win.width - 1, win.height - 1], 34, fill=(246, 242, 235, 255))
    for k, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 200, 64)]):
        d.ellipse([28 + k * 32, 28, 48 + k * 32, 48], fill=c)
    d.rounded_rectangle([170, 18, win.width - 40, 58], 18, fill=(232, 226, 216))
    d.text((190, 23), "sample-project / edit.mp4", font=font("Inter-Regular.otf", 26), fill=(110, 104, 96))
    d.rounded_rectangle([28, 90, 392, 760], 24, fill=(255, 255, 255))
    d.text((52, 112), "Sample project", font=font("Inter-Bold.otf", 28), fill=(120, 112, 104))
    d.text((52, 148), "Sample edit", font=font("InstrumentSerif-Regular.ttf", 64), fill=(30, 28, 26))
    win = shadowed(win, 30, (0, 20), 140)
    items = ["First clip", "Second clip", "Third clip", "Review", "Export"]
    fi = font("Inter-Bold.otf", 29)
    t_pull = rel("pullback", 53.99) - 0.2                         

    def f(t, fr, a, i):
        p = ease_io((t - t_pull) / 0.7)
        if p <= 0:
            return fr
        bg = np.zeros((H, W, 3), np.uint8); bg[:] = (22, 22, 26)
        canvas = Image.fromarray(bg).convert("RGBA")
        put(canvas, win, (WX0 + WX1) / 2, (WY0 + WY1) / 2, scale=1.25 - 0.25 * p, alpha=p)
        d = ImageDraw.Draw(canvas)
        if p > 0.95:
            for k, it in enumerate(items):
                tk = t_pull + 0.75 + k * 0.28
                y = WY0 + 280 + k * 66
                done = t >= tk
                d.ellipse([WX0 + 52, y, WX0 + 86, y + 34], fill=(40, 180, 90) if done else None,
                          outline=None if done else (190, 182, 172), width=3)
                if done:
                    d.line([(WX0 + 60, y + 18), (WX0 + 67, y + 25), (WX0 + 79, y + 10)], fill=(255, 255, 255), width=4)
                d.text((WX0 + 100, y + 1), it, font=fi, fill=(30, 28, 26) if done else (175, 168, 160))
        x0 = VX0 * p; y0 = VY0 * p; w = W + (VW - W) * p; h = H + (VH - H) * p
        vid = rounded(Image.fromarray(fr).resize((int(w), int(h)), Image.BILINEAR), int(28 * p))
        canvas.alpha_composite(vid, (int(x0), int(y0)))
        return np.asarray(canvas.convert("RGB"))
    run("pullback", f)


FX = {"couch": fx_couch, "chart": fx_chart, "phone": fx_phone, "ui": fx_ui, "headline": fx_headline, "zoom": fx_zoom,
      "zoomthrough": fx_zoomthrough, "paper": fx_paper, "vertigo": fx_vertigo, "orbit": fx_orbit, "pullback": fx_pullback}

if __name__ == "__main__":
    for name in (FX if sys.argv[1] == "all" else sys.argv[1:]):
        FX[name]()
