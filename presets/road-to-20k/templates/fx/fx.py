# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy", "pillow"]
# ///
"""Reusable effects helpers and digital zoom, checklist, cover-story and doodle recipes.
Review copy: sample labels only; source footage/model/fonts are not included.
Designed to be copied to projects/<job>/fx/build/fx.py (parents[4] locates repository root).
Writer carries source audio; placement must strip linked effect audio to avoid doubled voice."""
import math, os, subprocess, sys
from pathlib import Path

if __name__ == "__main__" and not (Path.cwd() / "src").is_dir():
    sys.exit("refusing to render outside a job fx directory that already contains src/.")

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]   
FONTS = ROOT / "assets/fonts"
W, H, FPS = 1080, 1920, 30
YELLOW = (255, 216, 77)


def font(name, size, index=0):
    """A bundled font by file name, or a system font by absolute path (a .ttc takes `index`)."""
    path = name if name.startswith("/") else str(FONTS / name)
    return ImageFont.truetype(path, size, index=index)



def frames(path, pix="rgb24", ch=3):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo",
                          "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    n = W * H * ch
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, ch)


def writer(out, src):
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(src), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], stdin=subprocess.PIPE)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def chip(img, n, name):
    """Small label so the four effects can be told apart in the compare reel."""
    d = ImageDraw.Draw(img)
    f = font("Inter-Bold.otf", 34)
    a, b = f"{n:02d}/04", f"  {name}"
    wa, wb = d.textlength(a, font=f), d.textlength(b, font=f)
    x0 = (W - wa - wb) / 2 - 26
    d.rounded_rectangle([x0, 1540, x0 + wa + wb + 52, 1604], 32, fill=(0, 0, 0, 170))
    d.text((x0 + 26, 1553), a, font=f, fill=YELLOW)
    d.text((x0 + 26 + wa, 1553), b, font=f, fill=(255, 255, 255))


def over(base_rgb, layer_rgba):
    im = Image.fromarray(base_rgb).convert("RGBA")
    im.alpha_composite(layer_rgba)
    return np.asarray(im.convert("RGB"))


def face_center(frame, det):
    f = det.detect(frame[:, :, ::-1])[1]
    if f is None:
        return None
    x, y, w, h = f[0][:4]
    return np.array([x + w / 2, y + h * 0.45])



def scale_at(t):
    return 1.0 + 0.45 * ease_out((t - 1.86) / 0.14)    
    return s


def run_a(src, out, extra=None):
    det = cv2.FaceDetectorYN_create(str(ROOT / "assets/models/face_detection_yunet_2023mar.onnx"),
                                    "", (W, H), score_threshold=0.6)
    w, anchor = writer(out, src), None
    for i, fr in enumerate(frames(src)):
        t = i / FPS
        c = face_center(fr, det)
        if c is not None:
            anchor = c if anchor is None else anchor * 0.85 + c * 0.15   
        a = anchor if anchor is not None else np.array([W / 2, H / 2])
        s = scale_at(t)
        M = np.float32([[s, 0, a[0] * (1 - s)], [0, s, a[1] * (1 - s)]])
        fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if extra:
            extra(layer, t)
        chip(layer, 1, "digital zoom")
        w.stdin.write(over(fr, layer).tobytes())
    w.stdin.close(); w.wait()



ROWS = [("clean", 2.38), ("crisp", 2.70), ("on topic", 3.06)]   


def card(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tin, tout = (1.0, 8.6) if os.environ.get("FAST") == "1" else (1.05, 8.6)
    k = ease_out((t - tin) / 0.45) * (1 - ease_io((t - tout) / 0.35))
    if k <= 0:
        return layer
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    x0, y0, x1, y1 = 60, 215, 1020, 800
    d.rounded_rectangle([x0, y0, x1, y1], 56, fill=(16, 16, 20, 205), outline=(255, 255, 255, 40), width=2)
    d.text((x0 + 64, y0 + 44), "keep it:", font=font("Inter-Bold.otf", 56), fill=(255, 255, 255, 150))
    fr = font("Inter-Black.otf", 104)
    for j, (word, tw) in enumerate(ROWS):
        y = y0 + 150 + j * 140
        p = ease_out((t - tw) / 0.18)                       
        pop = 1 + 0.18 * math.sin(math.pi * min(max((t - tw) / 0.22, 0), 1))
        bs = 96 * pop
        bx, by = x0 + 64 + 48 - bs / 2, y + 62 - bs / 2
        if p > 0:
            d.rounded_rectangle([bx, by, bx + bs, by + bs], 24, fill=YELLOW)
            
            pts = [(bx + bs * .24, by + bs * .52), (bx + bs * .43, by + bs * .70), (bx + bs * .77, by + bs * .30)]
            q = p * 2
            seg1 = pts[1] if q >= 1 else tuple(np.add(pts[0], np.subtract(pts[1], pts[0]) * q))
            d.line([pts[0], seg1], fill=(15, 15, 15), width=14, joint="curve")
            if q > 1:
                e = tuple(np.add(pts[1], np.subtract(pts[2], pts[1]) * (q - 1)))
                d.line([pts[1], e], fill=(15, 15, 15), width=14, joint="curve")
        else:
            d.rounded_rectangle([bx, by, bx + bs, by + bs], 24, outline=(255, 255, 255, 110), width=7)
        col = (255, 255, 255, 255) if p > 0 else (255, 255, 255, 105)
        d.text((x0 + 210, y), word, font=fr, fill=col)
    
    c = c.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -40 * (1 - k)))
    c.putalpha(c.getchannel("A").point(lambda v: int(v * k)))
    layer.alpha_composite(c)
    return layer


def run_b(src, out):
    w = writer(out, src)
    for i, fr in enumerate(frames(src)):
        layer = card(i / FPS)
        chip(layer, 2, "checklist")
        w.stdin.write(over(fr, layer).tobytes())
    w.stdin.close(); w.wait()



def masthead(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t0 = 0.72                                              
    k = ease_out((t - t0) / 0.45)
    if k <= 0:
        return layer
    d = ImageDraw.Draw(layer)
    txt = "DAY"
    f = font("InstrumentSerif-Regular.ttf", 470)
    f = font("InstrumentSerif-Regular.ttf", int(470 * 1000 / d.textlength(txt, font=f)))   
    tw = d.textlength(txt, font=f)
    grow = 1 + 0.035 * max(t - t0, 0) / 7                  
    big = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(big).text(((W - tw) / 2, 400 + 70 * (1 - k)), txt, font=f, fill=(255, 255, 255, int(255 * k)))
    if grow != 1:
        big = big.transform((W, H), Image.AFFINE, (1 / grow, 0, W / 2 * (1 - 1 / grow), 0, 1 / grow, 700 * (1 - 1 / grow)),
                            resample=Image.BICUBIC)
    layer.alpha_composite(big)
    fk = font("Inter-Bold.otf", 36)
    kick = "DAY IN THE LIFE  ·  THE COVER STORY"
    kw = d.textlength(kick, font=fk)
    d.text(((W - kw) / 2, 455 - 20 * (1 - k)), kick, font=fk, fill=(255, 255, 255, int(230 * k)))
    return layer


def run_c(src, matte, out):
    w = writer(out, src)
    for i, (fr, m) in enumerate(zip(frames(src), frames(matte, "rgba", 4))):
        t = i / FPS
        a = m[:, :, 3:4].astype(np.float32) / 255
        behind = over(fr, masthead(t)).astype(np.float32)
        comp = (a * fr + (1 - a) * behind).astype(np.uint8)          
        top = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        chip(top, 3, "cover story")
        w.stdin.write(over(comp, top).tobytes())
    w.stdin.close(); w.wait()



def outline_pts(alpha, rng, grow=26, step=7):
    m = (alpha > 127).astype(np.uint8)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1,) * 2))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)[:, 0, :].astype(np.float32)
    c = c[::step]
    
    k = np.ones(5) / 5
    c = np.stack([np.convolve(np.r_[c[-2:, j], c[:, j], c[:2, j]], k, "valid") for j in (0, 1)], 1)
    n = len(c)
    tang = np.roll(c, -1, 0) - np.roll(c, 1, 0)
    norm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    norm /= np.linalg.norm(norm, axis=1, keepdims=True) + 1e-6
    ph = rng.uniform(0, 2 * np.pi, 3)
    s = np.linspace(0, 2 * np.pi, n, endpoint=False)
    wob = 3.5 * np.sin(9 * s + ph[0]) + 2.0 * np.sin(23 * s + ph[1]) + rng.normal(0, 1.1, n)
    return c + norm * wob[:, None]


def sparkle(d, cx, cy, r, rng, col, w):
    for ang in (0, 90, 45, 135):
        a = math.radians(ang + rng.uniform(-8, 8))
        rr = r if ang % 90 == 0 else r * 0.55
        j = rng.normal(0, 1.5, 4)
        d.line([(cx - rr * math.cos(a) + j[0], cy - rr * math.sin(a) + j[1]),
                (cx + rr * math.cos(a) + j[2], cy + rr * math.sin(a) + j[3])], fill=col, width=w)


def run_d(src, matte, out, extra=None):
    w = writer(out, src)
    t0, draw_on = 0.15, 0.45                                 
    pts = None
    for i, (fr, m) in enumerate(zip(frames(src), frames(matte, "rgba", 4))):
        t = i / FPS
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if t >= t0:
            hold = i // 4                                    
            rng = np.random.default_rng(hold)
            pts = outline_pts(m[:, :, 3], rng)
            if pts is not None:
                p = ease_out((t - t0) / draw_on)
                n = max(2, int(len(pts) * p))
                top = int(np.argmin(pts[:, 1]))              
                order = np.r_[np.arange(top, len(pts)), np.arange(0, top)]
                half = n // 2
                idx_a = order[:half + 1]
                idx_b = order[::-1][:half + 1] if half else order[:1]
                big = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
                d = ImageDraw.Draw(big)
                for idx in (idx_a, np.r_[order[0], idx_b]):
                    seq = [tuple(v * 2) for v in pts[idx]]
                    if p >= 1:
                        seq = [tuple(v * 2) for v in pts[order]] + [tuple(pts[order[0]] * 2)]
                    d.line(seq, fill=(255, 255, 255, 255), width=14, joint="curve")
                    if p >= 1:
                        break
                
                if p >= 1:
                    off = outline_pts(m[:, :, 3], np.random.default_rng(hold + 999), grow=36)
                    if off is not None:
                        d.line([tuple(v * 2) for v in off] + [tuple(off[0] * 2)], fill=(255, 216, 77, 230),
                               width=7, joint="curve")
                    hx, hy = pts[top]
                    r2 = np.random.default_rng(hold + 7)
                    for (dx, dy, r) in ((-150, 10, 34), (165, -40, 44), (120, 120, 22)):
                        sparkle(d, (hx + dx) * 2, (hy + dy) * 2, r * 2, r2, (255, 255, 255, 255), 10)
                layer.alpha_composite(big.resize((W, H), Image.LANCZOS))
        if extra:
            extra(layer, t)
        chip(layer, 4, "doodle boil")
        w.stdin.write(over(fr, layer).tobytes())
    w.stdin.close(); w.wait()


if __name__ == "__main__":
    job = Path.cwd()
    which = sys.argv[1]
    src = {"a": "a-zoom", "b": "b-checklist", "c": "c-cover", "d": "d-doodle"}[which]
    srcp, out = job / f"src/{src}.mp4", job / f"outputs/{src}.mp4"
    if which == "a":
        run_a(srcp, out)
    elif which == "b":
        run_b(srcp, out)
    else:
        run_c(srcp, job / f"build/{which}-cutout.mov", out) if which == "c" else \
            run_d(srcp, job / f"build/{which}-cutout.mov", out)
    print("wrote", out)
