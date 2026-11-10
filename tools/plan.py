"""Edit decision list for the FIZIMA BOUTIQUE 60s TikTok Shop ad.

All timestamps are SOURCE seconds inside the raw clip (v1..v4), taken from the
Whisper (large-v3-turbo) transcription + pause analysis. Every cut sits in a
pause between sentences so no sentence is cut halfway.

Running this file writes remotion/src/edl.json, which drives both the media
preparation (tools/prepare_media.py) and the Remotion composition.
"""
import json, os

FPS = 30
TOTAL = 60 * FPS  # exactly 1800 frames

# key -> (source clip, src start, src end, transition INTO this segment, sparkle zone)
# sparkle zone = (x0, y0, x1, y1, src_from, src_to) in 1080x1920 output coords
SEGMENTS = [
    dict(id="A", src="v2", s=3.93, e=12.71, tin="flash",
         kb=(1.00, 1.06, 0.50, 0.55),
         sparkle=[(330, 1250, 700, 1750, 3.93, 7.0), (90, 1100, 480, 1750, 9.0, 12.7)]),
    dict(id="B", src="v3", s=11.06, e=23.10, tin="whipL",
         kb=(1.03, 1.00, 0.50, 0.45),
         sparkle=[(330, 900, 800, 1650, 15.4, 19.0)]),
    dict(id="C", src="v2", s=25.62, e=28.25, tin="flash", kb=(1.00, 1.05, 0.5, 0.5), sparkle=[]),
    dict(id="D", src="v2", s=28.25, e=32.87, tin="zoom", kb=(1.05, 1.00, 0.55, 0.6),
         sparkle=[(560, 1150, 980, 1800, 31.3, 32.9)]),
    dict(id="E", src="v4", s=36.12, e=46.65, tin="whipR", kb=(1.00, 1.06, 0.35, 0.55),
         sparkle=[(40, 800, 360, 1700, 39.4, 46.6)]),
    dict(id="F", src="v4", s=23.85, e=26.11, tin="flash", kb=(1.04, 1.00, 0.45, 0.6),
         sparkle=[(120, 900, 760, 1750, 23.85, 26.11)]),
    dict(id="G", src="v4", s=49.21, e=56.85, tin="whipU", kb=(1.00, 1.05, 0.5, 0.55), sparkle=[]),
    dict(id="H", src="v2", s=54.61, e=59.62, tin="zoom", kb=(1.04, 1.00, 0.55, 0.55),
         sparkle=[(600, 1150, 1000, 1800, 56.0, 59.6)]),
    dict(id="I", src="v2", s=39.06, e=40.84, tin="flash", kb=(1.00, 1.05, 0.5, 0.5), sparkle=[]),
]

# Captions per segment: (src start, src end, text). *word* = yellow keyword.
# Text follows what the host actually says (light spelling clean-up only).
CAPTIONS = {
    "A": [(3.93, 5.26, "Akak, *full* *diamond*!"),
          (5.26, 6.73, "Material *cotton* *Japanese*,"),
          (6.73, 7.45, "*bawal* *asli*"),
          (8.46, 11.21, "Dia design *laser* *cut* *2* *layer*,"),
          (11.21, 12.71, "*full* *diamond* *sampai* *hujung*!")],
    "B": [(11.06, 13.05, "Okay, saya pakai *style* *shawl*"),
          (13.05, 15.00, "Sebelah pendek, sebelah panjang,"),
          (15.00, 16.30, "akak lilit, nampak tak?"),
          (16.30, 17.60, "*Batu* *dia* *lawa* *sangat*!"),
          (17.60, 19.15, "Pakai style biasa pun *cantik*,"),
          (19.15, 20.90, "kalau nak lagi *wow*,"),
          (20.90, 21.99, "pakai style macam mana pun,"),
          (21.99, 23.10, "sebab dia *full* *diamond*!")],
    "C": [(25.62, 27.45, "Bidang kita bidang *45* *plus*,"),
          (27.45, 28.25, "*bawal* *asli* *Japanese*.")],
    "D": [(28.25, 29.70, "Design ni *sangat* *lawa*,"),
          (29.70, 31.55, "design ni kan, dia punya corak"),
          (31.55, 32.87, "dia *macam* *sulam*!")],
    "E": [(36.12, 37.83, "Teal blue, *cantik* kan?"),
          (37.83, 39.42, "Ni *dua* *layer* tau!"),
          (39.42, 41.35, "Dia punya bunga,"),
          (41.35, 43.30, "bunga dia kan *lawa*, cantik!"),
          (43.30, 44.85, "Bunga dia bunga-bunga *ros*."),
          (44.85, 46.65, "Ha ni, *bunga-bunga* *ros* *tabur*!")],
    "F": [(23.85, 26.11, "Baby blue, *batu* *dia* *warna* *biru*!")],
    "G": [(49.21, 50.55, "*Layer* *pertama*,"),
          (50.55, 51.75, "*layer* *yang* *kedua*."),
          (51.75, 53.62, "Dia *dua-dua* *sampai* *hujung*!"),
          (53.62, 54.20, "Dia bukan satu."),
          (54.20, 55.30, "Biasa satu je sampai depan,"),
          (55.30, 56.85, "*ini* *dua-dua* *sampai* *depan*!")],
    "H": [(54.61, 56.20, "Design pertama yang saya pakai ni,"),
          (56.20, 57.30, "design *Rafflesia*."),
          (57.30, 58.90, "Design kedua, design *Fiona*,"),
          (58.90, 59.62, "macam ni akak!")],
    "I": [(39.06, 40.84, "Dalam *beg* *kuning* kita ada *dua* *corak*!")],
}

# Big animated headlines (top safe zone): (src start, src end, main, sub, sfx)
HEADLINES = {
    "A": [(3.93, 8.40, "FULL DIAMOND", "Material Cotton Japanese", "impact", 5.30),
          (8.50, 12.71, "LASER CUT 2 LAYER", "Full diamond sampai hujung", "pop", 11.25)],
    "B": [(16.25, 19.20, "BATU DIA LAWA SANGAT", None, "pop")],
    "C": [(25.65, 28.25, "BIDANG 45+", "Bawal Asli Japanese", "pop", 27.45)],
    "D": [(31.50, 32.87, "CORAK MACAM SULAM", None, "pop")],
    "E": [(37.85, 41.30, "2 LAYER", None, "pop"),
          (44.85, 46.65, "BUNGA ROS TABUR", None, "pop")],
    "F": [(23.90, 26.11, "BATU WARNA BIRU", "Baby Blue", "pop")],
    "G": [(51.75, 56.85, "DUA-DUA SAMPAI HUJUNG", "Layer pertama + layer kedua", "impact")],
    "H": [(56.20, 59.62, "2 DESIGN", "Rafflesia & Fiona", "pop", 56.35)],
}

# Punch-in zoom moments (src time, zoom, focus x, focus y, shake?)
PUNCH = {
    "A": [(11.21, 1.10, 0.35, 0.70, False)],
    "B": [(16.30, 1.10, 0.52, 0.62, False)],
    "E": [(44.85, 1.09, 0.20, 0.62, False)],
    "G": [(51.75, 1.08, 0.50, 0.60, True)],
    "H": [(56.20, 1.08, 0.70, 0.70, False)],
}

# CTA b-roll: light-blue stone close-up, speed-ramped (fast -> slow motion)
CTA = dict(src="v4", s=26.20, fast_src=1.5, fast_out_frames=30, slow_rate=0.8, tin="whipL")


def build():
    out, f = [], 0
    for seg in SEGMENTS:
        n = round((seg["e"] - seg["s"]) * FPS)
        seg = dict(seg, frames=n, start=f, e=seg["s"] + n / FPS)

        def g(t, seg=seg):  # source time -> global frame
            return seg["start"] + round((t - seg["s"]) * FPS)

        caps = []
        for (a, b, text) in CAPTIONS.get(seg["id"], []):
            words = text.split()
            wl = [max(len(w.strip("*,.!?")), 2) + 2 for w in words]
            tot, acc, ws = sum(wl), 0, []
            for w, l in zip(words, wl):
                ws.append(dict(t=w.replace("*", ""), k=w.startswith("*"),
                               f=g(a + (b - a) * 0.85 * acc / tot)))
                acc += l
            caps.append(dict(f0=g(a), f1=min(g(b), seg["start"] + n), words=ws))
        heads = [dict(f0=g(h[0]), f1=min(g(h[1]), seg["start"] + n), main=h[2], sub=h[3], sfx=h[4],
                  subDelay=(g(h[5]) - g(h[0])) if len(h) > 5 else 8)
                 for h in HEADLINES.get(seg["id"], [])]
        punch = [dict(f=g(t), z=z, x=x, y=y, shake=sh) for (t, z, x, y, sh) in PUNCH.get(seg["id"], [])]
        sparks = [dict(x0=x0, y0=y0, x1=x1, y1=y1, f0=max(g(a), seg["start"]), f1=min(g(b), seg["start"] + n))
                  for (x0, y0, x1, y1, a, b) in seg["sparkle"]]
        out.append(dict(id=seg["id"], src=seg["src"], s=seg["s"], e=seg["e"], start=f, frames=n,
                        tin=seg["tin"], kb=seg["kb"], captions=caps, headlines=heads,
                        punch=punch, sparkles=sparks))
        f += n
    cta_frames = TOTAL - f
    assert 90 <= cta_frames <= 180, cta_frames
    cta = dict(CTA, start=f, frames=cta_frames)
    return dict(fps=FPS, total=TOTAL, segments=out, cta=cta, sfx=sfx_timeline(out, cta))


def sfx_timeline(segs, cta):
    """Sound-effect cue list (frame, sound, volume) rendered by Remotion as <Audio> elements."""
    ev = []
    lead = {"whoosh": 9, "swoosh": 5, "riser": 9}
    tin = {"whipL": "whoosh", "whipR": "whoosh", "whipU": "whoosh", "zoom": "swoosh", "flash": "riser"}
    for s in segs[1:] + [cta]:
        k = tin[s["tin"]]
        ev.append((s["start"] - lead[k], k, 1.0, "transition"))
    ev += [(0, "impact", 1.0, "hook"), (2, "sparkle", 1.0, "hook")]
    for s in segs:
        for h in s["headlines"]:
            if h["f0"] > 3:
                ev.append((h["f0"], h["sfx"], 0.9, "headline"))
            if h["sub"] and h["subDelay"] > 12:
                ev.append((h["f0"] + h["subDelay"], "pop", 0.5, "subline"))
        for sp in s["sparkles"]:
            if sp["f0"] > 3:
                ev.append((sp["f0"] + 4, "sparkle", 1.0, "stones"))
        for p in s["punch"]:
            ev.append((p["f"] - 4, "swoosh", 0.7, "punch-in"))
        for c in s["captions"]:  # soft pop when a yellow keyword appears
            kw = [w for w in c["words"] if w["k"]]
            if kw:
                ev.append((kw[0]["f"], "pop", 0.35, "keyword"))
    c0 = cta["start"]
    ev += [(c0 + 10, "pop", 0.9, "cta"), (c0 + 19, "impact", 1.0, "cta"), (c0 + 19, "chime", 0.9, "cta"),
           (c0 + 28, "pop", 0.9, "cta"), (c0 + 33, "sparkle", 1.0, "cta"), (c0 + 36, "swoosh", 0.5, "cta"),
           (c0 + 80, "sparkle", 0.8, "cta")]
    ev.sort()
    kept, last_any, last = [], -99, {}
    for f, k, v, why in ev:
        if f < 0 or f - last.get(k, -99) < 10:
            continue
        if why == "keyword" and f - last_any < 12:
            continue
        last[k] = f; last_any = max(last_any, f)
        kept.append(dict(f=f, sfx=f"{k}{len(kept) % 3}", vol=v, why=why))
    return kept


if __name__ == "__main__":
    edl = build()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "remotion", "src", "edl.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(edl, open(path, "w"), ensure_ascii=False, indent=1)
    for s in edl["segments"]:
        print(f'{s["id"]} {s["src"]} {s["s"]:6.2f}-{s["e"]:6.2f}  out {s["start"]/FPS:6.2f}-{(s["start"]+s["frames"])/FPS:6.2f}')
    c = edl["cta"]
    print(len(edl["sfx"]), "sfx cues")
    print(f'CTA out {c["start"]/FPS:.2f}-{(c["start"]+c["frames"])/FPS:.2f}')
