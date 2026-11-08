# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Behind-subject DAY N cover-card template with cleaned-static-median matte stabilization.
Copy into a job hf-graphics/ directory; fill DAY, ISSUE and CARDS f0/n.
Usage there: uv run hf-graphics/build_daycard.py daycard|nextcard [--top <pixels>]
Maps real timeline frames; renders versioned 30fps ProRes4444 alpha and preview.
Typography and model assets are separately required/rights-gated. Frame 0 intentionally has zero title alpha; this fade is not a dropped-card defect."""
import json, subprocess, sys, tempfile
from pathlib import Path

if __name__ == "__main__":
    _here = Path(__file__).resolve()
    if "presets" in _here.parts and "hf-graphics" not in _here.parts:
        sys.exit("template only: copy into the job hf-graphics/ directory before rendering. This file will not write from presets/.")

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


DAY = 10                          
ISSUE = "THE ... ISSUE"           
CARDS = {
    
    "daycard":  dict(title=f"DAY {DAY}", kicker=f"ROAD TO 20K  ·  {ISSUE}", f0=0, n=0),
    
    "nextcard": dict(title=f"DAY {DAY + 1}", kicker="ROAD TO 20K  ·  NEXT ISSUE", f0=0, n=0),
}


JOB = Path(__file__).resolve().parents[1]
ROOT = JOB.parents[1]
FONTS = ROOT / "assets/fonts"
W, H, FPS = 1080, 1920, 30
SAFE_X0, SAFE_X1, SAFE_Y0, SAFE_Y1 = 92, 988, 163, 1670
MIN_COVER, MAX_GLYPH = 0.10, 0.50          
                                           


def ease_out(t):
    return 1 - (1 - t) ** 3


def shot_frames(f0, n, out):
    """The timeline frames f0..f0+n of V1 as 1080x1920 PNGs, mapped through premiere/timeline-clips.json."""
    tl = json.loads((JOB / "premiere/timeline-clips.json").read_text())
    f, k = f0, 0
    while f < f0 + n:
        c = next((c for c in tl if c["f0"] <= f < c["f1"]), None)
        if c is None:
            sys.exit(f"timeline frame {f} is not A-roll on V1 (timeline-clips.json): pick the card's frames on a talking shot")
        run = min(c["f1"], f0 + n) - f
        t = c["in"] + (f - c["f0"]) / FPS
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", str(JOB / "raw" / c["clip"]),
                        "-vf", "scale=1080:1920,setsar=1,fps=30", "-frames:v", str(run), "-start_number", str(k),
                        str(out / "f%03d.png")], check=True)
        f += run; k += run
    return k


def mattes(frames_dir, n, masks_dir):
    """Per-frame person matte: frames -> mp4 -> hyperframes remove-background (u2net_human_seg) -> alpha PNGs."""
    with tempfile.TemporaryDirectory() as td:
        clip, cut = Path(td) / "shot.mp4", Path(td) / "shot-cutout.mov"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(frames_dir / "f%03d.png"),
                        "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(clip)], check=True)
        subprocess.run(["npx", "-y", "hyperframes@0.8.16", "remove-background", str(clip), "-o", str(cut)],
                       check=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cut), "-vf", "alphaextract", "-frames:v", str(n),
                        "-start_number", "0", str(masks_dir / "f%03d.png")], check=True)


def title_ink(text):
    size = 640
    while True:
        tf = ImageFont.truetype(str(FONTS / "InstrumentSerif-Regular.ttf"), size)
        b = tf.getbbox(text)
        if b[2] - b[0] <= SAFE_X1 - SAFE_X0 or size < 100:
            break
        size -= 4
    b = tf.getbbox(text)
    tw, th = b[2] - b[0], b[3] - b[1]
    img = Image.new("L", (tw + 40, th + 40), 0)
    ImageDraw.Draw(img).text((20 - b[0], 20 - b[1]), text, font=tf, fill=255)
    glyphs = []                                    
    x = 20 - b[0]
    for ch in text:
        if ch.strip():
            gb = tf.getbbox(ch); glyphs.append((x + gb[0], x + gb[2]))
        x += tf.getlength(ch)
    return img, size, tw, th, glyphs


def pick_top(title, glyphs, th, masks, n):
    """First cap-top (scanning down) where subject crosses the title without covering too much of it or any whole letter."""
    med = np.median(np.stack([np.asarray(Image.open(masks / f"f{i:03d}.png").convert("L"), np.float32) / 255
                              for i in range(0, n, max(1, n // 12))]), axis=0)
    ink = np.asarray(title, np.float32) / 255
    x0 = round(W / 2 - title.width / 2)
    best = None
    for top in range(380, 1181, 10):
        y0 = top - 20
        if y0 < SAFE_Y0 or y0 + title.height > SAFE_Y1:
            continue
        m = med[y0:y0 + title.height, x0:x0 + title.width]
        cover = float((ink * m).sum() / ink.sum())
        worst = max(float((ink[:, int(a):int(b)] * m[:, int(a):int(b)]).sum() / max(ink[:, int(a):int(b)].sum(), 1)) for a, b in glyphs)
        if cover >= MIN_COVER and worst <= MAX_GLYPH:
            return top, cover, worst
        if cover >= 0.05 and (best is None or worst < best[2]):
            best = (top, cover, worst)
    if best is None:
        best = (380, 0.0, 0.0)
    print(f"  no height met the limits; using the least-covered one (top {best[0]})")
    return best


def main():
    card = sys.argv[1] if len(sys.argv) > 1 else "daycard"
    C = CARDS[card]
    if not C["n"]:
        sys.exit(f"fill CARDS['{card}'] f0/n (timeline frames) in the JOB CONFIG block first")
    work = JOB / "hf-graphics" / card
    (work / "frames").mkdir(parents=True, exist_ok=True); (work / "masks").mkdir(exist_ok=True)
    n = shot_frames(C["f0"], C["n"], work / "frames")
    print(f"{card}: {n} timeline frames {C['f0']}-{C['f0'] + n} pulled; matting (u2net_human_seg)...")
    mattes(work / "frames", n, work / "masks")

    title, size, tw, th, glyphs = title_ink(C["title"])
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1]); cover = worst = float("nan")
    else:
        top, cover, worst = pick_top(title, glyphs, th, work / "masks", n)
    print(f"  title {size}px, cap top y{top} (covers {cover:.0%} of the ink, worst letter {worst:.0%})")
    kicker_y = top - 52
    tcx, tcy = W / 2, top + th / 2
    kf = ImageFont.truetype(str(FONTS / "TikTokSans36pt-Bold.ttf"), 40)
    assert kf.getname() == ("TikTok Sans", "Bold"), kf.getname()

    def title_alpha(scale):
        t = title.resize((round(title.width * scale), round(title.height * scale)), Image.LANCZOS)
        canvas = Image.new("L", (W, H), 0)
        canvas.paste(t, (round(tcx - t.width / 2), round(tcy - t.height / 2)))
        return np.asarray(canvas, np.float32) / 255

    def kicker(op):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        bb = kf.getbbox(C["kicker"]); x = W / 2 - (bb[2] - bb[0]) / 2 - bb[0]; y = kicker_y - (bb[3] + bb[1]) / 2
        assert SAFE_X0 <= x + bb[0] and x + bb[2] <= SAFE_X1, "kicker outside the safe zone: shorten ISSUE"
        d.text((x, y), C["kicker"], font=kf, fill=(255, 255, 255, round(255 * op)))
        return layer

    
    
    
    
    raw_m = [np.asarray(Image.open(work / "masks" / f"f{i:03d}.png").convert("L"), np.float32) for i in range(n)]
    covers = [(m > 128).mean() for m in raw_m]
    keep = [i for i in range(n) if 0.25 <= covers[i] <= 0.80]
    if len(keep) < 12:
        keep = [i for i in range(n) if 0.15 <= covers[i] <= 0.90]
    if not keep:
        keep = list(range(n))
    stab_m = np.median(np.stack([raw_m[i] for i in keep], axis=0), axis=0)
    frames = []
    for i in range(n):
        sc = 1.15 - 0.15 * ease_out(min(i / 8, 1)) if i <= 8 else 1.0 + 0.03 * (i - 8) / max(1, n - 9)
        a = title_alpha(sc) * ease_out(min(i / 6, 1))
        m = Image.fromarray(stab_m.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2.0))
        a *= 1.0 - np.asarray(m, np.float32) / 255                           
        rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")
        if i >= 3:
            img.alpha_composite(kicker(ease_out(min((i - 3) / 5, 1))))
        frames.append(img)

    ver = 1
    while (JOB / "hf-graphics/renders" / f"{card}-v{ver}.mov").exists():
        ver += 1
    out = JOB / "hf-graphics/renders" / f"{card}-v{ver}.mov"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for i, f in enumerate(frames):
            f.save(f"{td}/{i:03d}.png")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30", "-i", f"{td}/%03d.png",
                        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16",
                        "-vendor", "apl0", str(out)], check=True)
    strip = []
    for i in sorted({0, 4, 9, n // 3, 2 * n // 3, n - 1}):
        base = Image.open(work / "frames" / f"f{i:03d}.png").convert("RGBA"); base.alpha_composite(frames[i])
        strip.append(base.resize((270, 480)))
    pv = Image.new("RGB", (270 * len(strip), 480)); [pv.paste(s, (270 * k, 0)) for k, s in enumerate(strip)]
    pv.save(work / f"preview-v{ver}.jpg")
    print(f"  wrote {out.relative_to(JOB)} ({n} frames) + {card}/preview-v{ver}.jpg")
    print(f'  place.json row: [3, "hf-graphics/renders/{out.name}", {C["f0"]}, {n}, null]')


if __name__ == "__main__":
    main()
