"""Compositor: zoom/speed-ramp/transitions/sparkle/text -> 1080x1920 30fps MP4.

usage: python3 render.py <clips_dir> <assets_dir> <audio.wav> <out.mp4> [t_start t_end]
"""
import math, subprocess, sys, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from timeline import CLIPS, TEXTS, FPS, W, H, TOTAL

CLIPS_DIR, ASSETS, AUDIO, OUT = sys.argv[1:5]
T0, T1 = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (0.0, TOTAL)
SRC_W, SRC_H, SRC_FPS = 960, 1920, 60
FONT = ASSETS + "/package/files/montserrat-latin-{}-normal.woff"
SERIF = ASSETS + "/package/files/playfair-display-latin-700-italic.woff"
EMOJI = ASSETS + "/package/img/google/64/{}.png"


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


# ------------------------------------------------------------------ source reading
class Reader:
    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx = -1
        self.frame = None

    def get(self, idx):
        while self.idx < idx:
            buf = self.p.stdout.read(SRC_W * SRC_H * 3)
            if len(buf) < SRC_W * SRC_H * 3:  # past the end: hold last frame
                break
            self.frame = buf
            self.idx += 1
        return Image.frombuffer("RGB", (SRC_W, SRC_H), self.frame, "raw", "RGB", 0, 1)


def interp_keys(keys, u):
    """smooth interpolation over [(u, v...)] keyframes."""
    if u <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if u <= b[0]:
            f = ease_io((u - a[0]) / (b[0] - a[0]))
            return tuple(x + (y - x) * f for x, y in zip(a[1:], b[1:]))
    return keys[-1][1:]


class Clip:
    def __init__(self, c):
        self.c = c
        self._reader = None
        # numerically integrate speed ramp -> source time per output time
        n = 2000
        us = np.linspace(-0.5, 1.4, n)  # allow running before/after (dissolves)
        sp = np.array([interp_keys(c["speed"], min(max(u, 0.0), 1.0))[0] for u in us])
        dt = c["d"] * (us[1] - us[0])
        acc = np.concatenate([[0], np.cumsum((sp[1:] + sp[:-1]) / 2 * dt)])
        self.src = c["off"] + acc - np.interp(0.0, us, acc)
        self.us = us

    def frame(self, t, extra_zoom=1.0):
        c = self.c
        u = (t - c["t"]) / c["d"]
        s = np.interp(u, self.us, self.src)
        if self._reader is None:
            self._reader = Reader(f"{CLIPS_DIR}/{c['file']}.mp4")
        img = self._reader.get(int(round(s * SRC_FPS)))
        z, cx, cy = interp_keys(c["zoom"], min(max(u, 0), 1))
        z *= extra_zoom
        # window in source px with output aspect, clamped inside the frame
        ww = SRC_W / z
        wh = ww * H / W
        x0 = min(max(cx * SRC_W - ww / 2, 0), SRC_W - ww)
        y0 = min(max(cy * SRC_H - wh / 2, 0), SRC_H - wh)
        return img.transform((W, H), Image.EXTENT, (x0, y0, x0 + ww, y0 + wh), Image.BICUBIC)


# ------------------------------------------------------------------ effects
def hblur(img, amount):
    k = max(1, int(amount))
    if k <= 1:
        return img
    return img.resize((max(8, W // k), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)


def radial_blur(img, strength):
    if strength < 0.01:
        return img
    out = np.asarray(img, dtype=np.float32)
    acc = out.copy()
    n = 8
    for k in range(1, n + 1):
        s = 1 + strength * 0.022 * k
        cw, ch = W / s, H / s
        z = img.transform((W, H), Image.EXTENT, ((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2),
                          Image.BILINEAR)
        acc += np.asarray(z, dtype=np.float32)
    return Image.fromarray((acc / (n + 1)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(strength * 2.5))


def make_star(size=128):
    """soft 4-point glint sprite (grayscale, used additively)."""
    y, x = np.mgrid[-1:1:size * 1j, -1:1:size * 1j]
    r = np.sqrt(x * x + y * y)
    core = np.exp(-(r / 0.10) ** 2)
    glow = np.exp(-(r / 0.30) ** 2) * 0.35
    rays = (np.exp(-(np.abs(x) / 0.025) ** 2) * np.exp(-(np.abs(y) / 0.85) ** 2) +
            np.exp(-(np.abs(y) / 0.025) ** 2) * np.exp(-(np.abs(x) / 0.85) ** 2))
    xr, yr = (x + y) / 1.414, (x - y) / 1.414
    rays2 = (np.exp(-(np.abs(xr) / 0.02) ** 2) * np.exp(-(np.abs(yr) / 0.4) ** 2) +
             np.exp(-(np.abs(yr) / 0.02) ** 2) * np.exp(-(np.abs(xr) / 0.4) ** 2)) * 0.5
    v = np.clip(core + glow + rays + rays2, 0, 1)
    return Image.fromarray((v * 255).astype(np.uint8), "L")


STAR = make_star()


def sparkle(img, t, region, strength=1.0):
    """add twinkling glints on top of the stones that are actually in the frame:
    find small high-contrast specks inside `region` and place glints on them."""
    small = img.convert("L").resize((W // 2, H // 2), Image.BILINEAR)
    g = np.asarray(small, dtype=np.float32)
    bl = np.asarray(small.filter(ImageFilter.BoxBlur(5)), dtype=np.float32)
    d = np.abs(g - bl)
    dimg = Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8))
    mx = np.asarray(dimg.filter(ImageFilter.MaxFilter(15)), dtype=np.float32)
    dd = np.clip(d * 4, 0, 255)
    x0, y0, x1, y1 = region
    hh, ww = dd.shape
    mask = np.zeros_like(dd, dtype=bool)
    mask[int(y0 * hh):int(y1 * hh), int(x0 * ww):int(x1 * ww)] = True
    peaks = (dd >= mx) & (dd > 40) & mask
    ys, xs = np.nonzero(peaks)
    if len(xs) == 0:
        return img
    score = dd[ys, xs]
    order = np.argsort(-score)[:40]
    layer = Image.new("L", (W, H), 0)
    drawn = 0
    for i in order:
        x, y = xs[i] * 2, ys[i] * 2
        h = (zlib.crc32(f"{x // 70},{y // 70}".encode()) % 1000) / 1000.0
        tw = max(0.0, math.sin(2 * math.pi * (t * 1.3 + h))) ** 4
        if tw < 0.15:
            continue
        sz = int((34 + 46 * h) * tw * strength)
        if sz < 10:
            continue
        st = STAR.resize((sz, sz), Image.BILINEAR)
        layer.paste(ImageChops.lighter(layer.crop((x - sz // 2, y - sz // 2, x - sz // 2 + sz, y - sz // 2 + sz)), st),
                    (x - sz // 2, y - sz // 2))
        drawn += 1
        if drawn >= 7:
            break
    warm = Image.merge("RGB", (layer, layer.point(lambda v: v * 0.96), layer.point(lambda v: v * 0.86)))
    return ImageChops.add(img, warm)


# ------------------------------------------------------------------ text
def font(weight, size):
    return ImageFont.truetype(FONT.format(weight), size)


def emoji(code, size):
    return Image.open(EMOJI.format(code)).convert("RGBA").resize((size, size), Image.LANCZOS)


def text_block(text, code, style):
    lines = text.split("|")
    if style == "hook":
        f, fill, stroke, sc, pad = font(800, 112), (255, 255, 255), 9, (74, 30, 58), 0
    elif style == "cta":
        f, fill, stroke, sc, pad = font(800, 76), (46, 28, 40), 0, None, 42
    elif style == "sub":
        f, fill, stroke, sc, pad = font(600, 44), (255, 255, 255), 0, None, 30
    else:
        f, fill, stroke, sc, pad = font(700, 70), (46, 28, 40), 0, None, 44
    es = int(f.size * 1.05) if code else 0
    gap = 16
    dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
    sizes = [dummy.textbbox((0, 0), ln, font=f, stroke_width=stroke) for ln in lines]
    lws = [b[2] - b[0] for b in sizes]
    if code:
        lws[-1] += gap + es
    lh = int(f.size * 1.18)
    tw = max(lws)
    bw = tw
    bh = lh * len(lines)
    PADY = int(pad * 0.55)
    cw, ch = bw + 2 * pad + 40, bh + 2 * PADY + 40
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ox, oy = 20, 20
    if style in ("label", "cta", "sub"):
        # soft shadow
        sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((ox, oy + 8, ox + bw + 2 * pad, oy + bh + 2 * PADY + 8),
                                             radius=(bh + 2 * PADY) // 2, fill=(40, 20, 30, 90))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(img)
        box = (ox, oy, ox + bw + 2 * pad, oy + bh + 2 * PADY)
        r = min((bh + 2 * PADY) // 2, 60)
        if style == "cta":
            grad = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]))
            ga = np.linspace(0, 1, grad.width)[None, :, None]
            c1, c2 = np.array([214, 172, 74]), np.array([247, 226, 160])
            arr = (c1 + (c2 - c1) * (0.5 - 0.5 * np.cos(ga * 2 * np.pi))) * np.ones((grad.height, 1, 1))
            grad = Image.fromarray(np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255)], 2).astype(np.uint8))
            m = Image.new("L", grad.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, grad.width - 1, grad.height - 1), radius=r, fill=255)
            img.paste(grad, box[:2], m)
            d.rounded_rectangle(box, radius=r, outline=(255, 255, 255, 200), width=3)
        elif style == "sub":
            d.rounded_rectangle(box, radius=r, fill=(46, 28, 40, 200))
        else:
            d.rounded_rectangle(box, radius=r, fill=(255, 251, 246, 238), outline=(201, 162, 74, 255), width=3)
    else:
        sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if style == "hook":
        shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        ds = ImageDraw.Draw(shadow)
    for k, (ln, b) in enumerate(zip(lines, sizes)):
        lw = lws[k]
        x = ox + pad + (tw - lw) // 2 - b[0]
        y = oy + PADY + k * lh + (lh - (b[3] - b[1])) // 2 - b[1]
        if style == "hook":
            ds.text((x, y + 8), ln, font=f, fill=(40, 10, 30, 140), stroke_width=stroke, stroke_fill=(40, 10, 30, 140))
        d.text((x, y), ln, font=f, fill=fill, stroke_width=stroke, stroke_fill=sc)
        if code and k == len(lines) - 1:
            ex, ey = x + b[0] + (b[2] - b[0]) + gap, oy + PADY + k * lh + (lh - es) // 2
    if style == "hook":
        img = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)), img)
    if code:
        img.alpha_composite(emoji(code, es), (ex, ey))
    return img


BLOCKS = [(text_block(tx, code, st), tx, t_in, t_out, st, y) for tx, code, t_in, t_out, st, y in TEXTS]


def spring(tau, k=9.0, w=13.0):
    return 1 - math.exp(-k * tau) * math.cos(w * tau)


def place_text(frame, t):
    for img, tx, t_in, t_out, st, y in BLOCKS:
        if not (t_in <= t < t_out):
            continue
        tau = t - t_in
        out = t_out - t
        alpha = min(1.0, tau / 0.12) * (min(1.0, out / 0.18) if t_out < TOTAL else 1.0)
        dy = 0
        if st in ("hook", "label"):
            s = 0.35 + 0.65 * spring(tau)
            if out < 0.18 and t_out < TOTAL:
                s *= 0.9 + 0.1 * out / 0.18
            if st == "hook":
                s *= 1 + 0.025 * math.sin(2 * math.pi * 2 * t)  # pulse on the beat
        elif st == "cta":
            # drop-in bounce then pulse on the beat
            dy = -160 * math.exp(-5 * tau) * abs(math.cos(9 * tau)) if tau < 1.2 else 0
            s = (0.6 + 0.4 * smooth(tau / 0.2)) * (1 + 0.035 * max(0, math.sin(2 * math.pi * 2 * (t - 18.5))) ** 2)
        else:  # sub: fade + slide up
            s = 1.0
            dy = 30 * (1 - smooth(tau / 0.35))
        im = img
        if abs(s - 1) > 1e-3:
            im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
        if alpha < 1:
            a = im.getchannel("A").point(lambda v: v * alpha)
            im = im.copy()
            im.putalpha(a)
        cx = W // 2
        cy = y + img.height // 2 + int(dy)
        frame.alpha_composite(im, (cx - im.width // 2, cy - im.height // 2))
    return frame


# ------------------------------------------------------------------ main loop
def main():
    clips = [Clip(c) for c in CLIPS]
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-ss", str(T0), "-t", str(T1 - T0), "-i", AUDIO,
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT],
        stdin=subprocess.PIPE)
    nf = int(round((T1 - T0) * FPS))
    for fi in range(nf):
        t = T0 + fi / FPS
        # active clip
        k = max(i for i, c in enumerate(CLIPS) if c["t"] <= t + 1e-6)
        c = CLIPS[k]
        nxt = CLIPS[k + 1] if k + 1 < len(CLIPS) else None
        img = None
        # transition handling: outgoing half (before next cut) and incoming half
        if nxt and t > nxt["t"] - nxt["tin"][1] / 2 and nxt["tin"][0] in ("zoom", "whip"):
            typ, L = nxt["tin"]
            p = (t - (nxt["t"] - L / 2)) / (L / 2)  # 0..1 approaching cut
            if typ == "zoom":
                img = radial_blur(clips[k].frame(t, 1 + 0.35 * p ** 2), p * 2)
            else:
                f = clips[k].frame(t)
                img = hblur(ImageChops.offset(f, int(-W * 0.5 * p ** 2), 0), 1 + 40 * p)
        elif nxt and nxt["tin"][0] == "dissolve" and t > nxt["t"] - nxt["tin"][1]:
            img = None  # handled in incoming branch below via look-ahead
        typ, L = c["tin"]
        u_in = t - c["t"]
        if img is None:
            if typ == "zoom" and u_in < L / 2:
                p = 1 - u_in / (L / 2)
                img = radial_blur(clips[k].frame(t, 1 + 0.35 * p ** 2), p * 2)
            elif typ == "whip" and u_in < L / 2:
                p = 1 - u_in / (L / 2)
                img = hblur(ImageChops.offset(clips[k].frame(t), int(W * 0.5 * p ** 2), 0), 1 + 40 * p)
            elif typ == "punch" and u_in < L:
                p = 1 - u_in / L
                img = clips[k].frame(t, 1 + 0.10 * p)
            else:
                img = clips[k].frame(t)
        # dissolve: blend outgoing (running past its end) into incoming
        if nxt and nxt["tin"][0] == "dissolve" and t > nxt["t"] - nxt["tin"][1]:
            L = nxt["tin"][1]
            p = smooth((t - (nxt["t"] - L)) / L)
            img = Image.blend(img, clips[k + 1].frame(t), p)
        if c.get("spark"):
            img = sparkle(img, t, c["spark"], strength=1.0)
        if typ == "flash" and u_in < L:
            p = 1 - u_in / L
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 252, 246)), 0.75 * p ** 1.5)
        # gentle vignette-free ending dip to keep loop clean
        frame = place_text(img.convert("RGBA"), t)
        enc.stdin.write(frame.convert("RGB").tobytes())
        if fi % 60 == 0:
            print(f"frame {fi}/{nf}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("done", OUT)


if __name__ == "__main__":
    main()
