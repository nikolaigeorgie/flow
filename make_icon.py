"""Draws Vox84's retro app icon (synthwave sunset + vintage chrome microphone) and menu bar glyphs."""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent / "assets"
OUT.mkdir(exist_ok=True)
S = 1024


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def vgradient(w, h, stops):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        for i in range(len(stops) - 1):
            (t0, c0), (t1, c1) = stops[i], stops[i + 1]
            if t0 <= t <= t1:
                c = lerp(c0, c1, (t - t0) / (t1 - t0))
                break
        for x in range(w):
            px[x, y] = c
    return img


def hgradient(w, h, stops):
    return vgradient(h, w, stops).rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)


def mask_rr(box, r, size=(S, S)):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, r, fill=255)
    return m


def app_icon():
    pad, r = 100, 185                      # macOS icon grid: 824px body inside 1024 canvas
    body = (pad, pad, S - pad, S - pad)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Sky: deep indigo -> purple -> hot pink horizon
    sky = vgradient(S, S, [(0, (20, 8, 48, 255)), (0.45, (66, 18, 102, 255)),
                           (0.66, (196, 40, 132, 255)), (1, (40, 6, 50, 255))])
    canvas = sky.copy()
    d = ImageDraw.Draw(canvas)

    # Stars
    import random
    random.seed(7)
    for _ in range(40):
        x, y = random.randint(pad, S - pad), random.randint(pad + 20, 470)
        a = random.randint(90, 220)
        rr = random.choice([2, 2, 3, 4])
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, 230, 255, a))

    # Retro sun with horizontal slats
    cx, cy, R = S // 2, 610, 270
    sun = vgradient(S, S, [(0, (255, 240, 120, 255)), (0.5, (255, 214, 90, 255)),
                           (0.62, (255, 120, 90, 255)), (0.75, (240, 60, 140, 255)), (1, (240, 60, 140, 255))])
    smask = Image.new("L", (S, S), 0)
    sd = ImageDraw.Draw(smask)
    sd.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    y, gap = cy + 10, 8
    while y < cy + R:
        sd.rectangle((0, y, S, y + gap), fill=0)
        y += gap + 26
        gap += 5
    glow = smask.filter(ImageFilter.GaussianBlur(40))
    canvas.paste((255, 120, 170, 255), (0, 0), glow.point(lambda v: int(v * 0.55)))
    canvas.paste(sun, (0, 0), smask)

    # Neon perspective grid floor
    horizon = 700
    floor = vgradient(S, S - horizon, [(0, (36, 6, 60, 255)), (1, (12, 2, 24, 255))])
    canvas.paste(floor, (0, horizon))
    grid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    neon = (255, 70, 200, 255)
    for i in range(-12, 13):
        g.line((cx + i * 22, horizon, cx + i * 170, S), fill=neon, width=4)
    yy, step = horizon, 10
    while yy < S:
        g.line((0, yy, S, yy), fill=neon, width=4)
        step *= 1.45
        yy += int(step)
    gglow = grid.filter(ImageFilter.GaussianBlur(6))
    canvas = Image.alpha_composite(canvas, gglow)
    canvas = Image.alpha_composite(canvas, grid)
    ImageDraw.Draw(canvas).line((0, horizon, S, horizon), fill=(255, 150, 230, 255), width=6)

    # Vintage chrome capsule microphone
    mic = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mw, mh = 300, 420
    mx0, my0 = cx - mw // 2, 190
    mbox = (mx0, my0, mx0 + mw, my0 + mh)
    chrome = hgradient(mw, mh, [(0, (110, 110, 135, 255)), (0.18, (245, 245, 255, 255)),
                                (0.35, (170, 170, 195, 255)), (0.62, (70, 70, 95, 255)),
                                (0.85, (200, 200, 225, 255)), (1, (90, 90, 115, 255))])
    cm = Image.new("L", (mw, mh), 0)
    ImageDraw.Draw(cm).rounded_rectangle((0, 0, mw - 1, mh - 1), mw // 2, fill=255)
    mic.paste(chrome, (mx0, my0), cm)
    md = ImageDraw.Draw(mic)
    # grille slots
    for k in range(9):
        yk = my0 + 95 + k * 26
        md.rounded_rectangle((mx0 + 48, yk, mx0 + mw - 48, yk + 11), 6, fill=(28, 20, 48, 235))
    # yoke (U-bracket attached at the band) + stand
    by = my0 + int(mh * 0.68)
    yr = mw // 2 + 34
    md.arc((cx - yr, by - 190, cx + yr, by + 190), 0, 180, fill=(235, 235, 250, 255), width=26)
    md.rectangle((cx - 15, by + 180, cx + 15, 830), fill=(225, 225, 245, 255))
    # pink band with pivot knobs where the yoke meets the mic
    md.rounded_rectangle((mx0 - 12, by - 20, mx0 + mw + 12, by + 20), 20, fill=(255, 92, 170, 255))
    for kx in (cx - yr, cx + yr):
        md.ellipse((kx - 26, by - 26, kx + 26, by + 26), fill=(245, 245, 255, 255))
        md.ellipse((kx - 10, by - 10, kx + 10, by + 10), fill=(255, 92, 170, 255))
    md.rounded_rectangle((cx - 120, 815, cx + 120, 855), 20, fill=(235, 235, 250, 255))
    # specular highlight
    hl = Image.new("L", (S, S), 0)
    ImageDraw.Draw(hl).rounded_rectangle((mx0 + 50, my0 + 22, mx0 + 82, my0 + mh - 90), 16, fill=150)
    mic.paste((255, 255, 255, 255), (0, 0), ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(5)),
                                                                mic.split()[3]))
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    shadow.paste((10, 0, 30, 200), (0, 0), mic.split()[3].filter(ImageFilter.GaussianBlur(26)))
    canvas = Image.alpha_composite(canvas, shadow.transform((S, S), Image.AFFINE, (1, 0, -14, 0, 1, -22)))
    canvas = Image.alpha_composite(canvas, mic)

    # Clip to rounded square, add inner rim light
    img.paste(canvas, (0, 0), mask_rr(body, r))
    rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(body, r, outline=(255, 255, 255, 60), width=4)
    img = Image.alpha_composite(img, rim)
    return img


def menubar_glyph(px, color=(0, 0, 0, 255)):
    """Retro capsule mic silhouette for the menu bar (drawn big, downsampled for crisp edges)."""
    k = 8
    s = px * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = s * 0.42
    x0, y0 = (s - w) / 2, s * 0.04
    d.rounded_rectangle((x0, y0, x0 + w, y0 + s * 0.62), w / 2, fill=color)
    for i in range(4):  # grille cut-outs
        y = y0 + s * 0.17 + i * s * 0.09
        d.rounded_rectangle((x0 + w * 0.22, y, x0 + w * 0.78, y + s * 0.035), s * 0.02, fill=(0, 0, 0, 0))
    lw = int(s * 0.07)
    d.arc((s * 0.18, s * 0.12, s * 0.82, s * 0.80), 15, 165, fill=color, width=lw)
    d.rectangle((s / 2 - lw / 2, s * 0.79, s / 2 + lw / 2, s * 0.92), fill=color)
    d.rounded_rectangle((s * 0.30, s * 0.90, s * 0.70, s * 0.97), lw / 2, fill=color)
    return im.resize((px, px), Image.LANCZOS)


if __name__ == "__main__":
    icon = app_icon()
    icon.save(OUT / "icon_1024.png")
    # (build_app.sh turns icon_1024.png into the .icns)
    for px in (18, 36):  # "off" state: mic with a slash through it
        g = menubar_glyph(px)
        d = ImageDraw.Draw(g)
        w = max(2, px // 9)
        d.line((px * 0.12, px * 0.08, px * 0.88, px * 0.92), fill=(0, 0, 0, 0), width=w * 3)
        d.line((px * 0.12, px * 0.08, px * 0.88, px * 0.92), fill=(0, 0, 0, 255), width=w)
        g.save(OUT / ("menubar_off.png" if px == 18 else "menubar_off@2x.png"))
    for name, col in (("menubar", (0, 0, 0, 255)), ("menubar_rec", (255, 59, 92, 255)),
                      ("menubar_busy", (120, 170, 255, 255))):
        menubar_glyph(18, col).save(OUT / f"{name}.png")
        menubar_glyph(36, col).save(OUT / f"{name}@2x.png")
    print("ok")
