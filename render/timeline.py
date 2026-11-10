"""Edit decision list for the tudung TikTok Shop promo (host-voice version).

The host's own speech is the spine of the edit: VOICE lists whole phrases from the
raw audio (cut only at natural pauses) laid end to end at 1x speed. Picture is either
lip-synced A-roll from the same source time, or B-roll (slow-mo detail, colour
montage) laid over her voice where her mouth is not on screen.

Source clips are pre-rendered by prep_clip.sh (60 fps motion-interpolated + colour
graded); `off` is the start offset (s) inside that pre-rendered clip.
speed: [(u, speed)] keyframes over normalised clip time u in [0,1] (smooth ramp)
zoom:  [(u, zoom, cx, cy)] keyframes; zoom 1 = fill 9:16 frame; cx/cy = centre of
       interest in normalised source coordinates.
spark: region (x0,y0,x1,y1, normalised output) where existing stones get a glint.
"""

BPM = 120
FPS = 30
W, H = 1080, 1920
TOTAL = 22.0

# (source start, source end, timeline start) - phrases split at detected pauses
VOICE = [
    (0.00, 5.07, 0.00),
    (8.01, 13.02, 5.07),
    (17.36, 20.65, 10.08),
    (36.67, 41.09, 13.37),
    (55.29, 59.03, 17.79),
]


def sync(file, file_start, t, d, src, **kw):
    """lip-synced A-roll: picture source time == voice source time."""
    return dict(file=file, t=t, d=d, off=src - file_start, speed=[(0, 1), (1, 1)], **kw)


MONT = [15.10, 15.64, 16.18, 16.72, 17.26, 17.79]

CLIPS = [
    # 0-1.8  HOOK (B-roll over her opening line): stones on mint fabric, slow-mo pull-back
    dict(file="A", t=0.0, d=1.8, off=0.2, speed=[(0, .75), (1, .75)],
         zoom=[(0, 1.50, .30, .55), (1, 1.30, .30, .55)], tin=("flash", .25),
         spark=(0.0, 0.25, 0.72, 1.0)),
    # 1.8-5.07  host wearing the dusty-blue shawl, talking (sync)
    sync("S1v", 1.6, 1.8, 3.27, 1.8, zoom=[(0, 1.0, .60, .50), (1, 1.12, .60, .48)], tin=("zoom", .3)),
    # 5.07-7.06  gold fabric brought to camera (sync)
    sync("S2a", 7.9, 5.07, 1.99, 8.01, zoom=[(0, 1.05, .40, .50), (1, 1.18, .38, .52)], tin=("whip", .3)),
    # 7.06-9.30  B-roll: mint fabric swings to the lens, speed ramp into slow-mo
    dict(file="B", t=7.06, d=2.24, off=0.2,
         speed=[(0, 1.1), (.3, 1.1), (.45, .5), (.85, .5), (1, .9)],
         zoom=[(0, 1.35, .36, .66), (1, 1.50, .36, .70)], tin=("zoom", .3)),
    # 9.30-10.08  back to her (sync) with cream fabric
    sync("S2b", 12.1, 9.30, 0.78, 12.23, zoom=[(0, 1.12, .40, .52), (1, 1.06, .40, .52)], tin=("punch", .12)),
    # 10.08-13.37  pointing at the stones, dynamic push-in (sync)
    sync("S3", 17.2, 10.08, 3.29, 17.36,
         zoom=[(0, 1.25, .32, .66), (.55, 1.45, .28, .68), (1, 1.55, .28, .69)],
         tin=("zoom", .3), spark=(0.0, 0.35, 0.70, 1.0)),
    # 13.37-15.10  mint fabric opened out (sync)
    sync("S4a", 36.5, 13.37, 1.73, 36.67, zoom=[(0, 1.0, .40, .50), (1, 1.14, .36, .52)], tin=("whip", .3)),
    # 15.10-17.79  B-roll colour montage over her voice
    dict(file="H1", t=MONT[0], d=MONT[1] - MONT[0], off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.60, .25, .55), (1, 1.50, .25, .55)], tin=("zoom", .2)),
    dict(file="H2", t=MONT[1], d=MONT[2] - MONT[1], off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.60, .28, .62), (1, 1.50, .28, .62)], tin=("punch", .12)),
    dict(file="H3", t=MONT[2], d=MONT[3] - MONT[2], off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.75, .20, .38), (1, 1.62, .20, .38)], tin=("punch", .12)),
    dict(file="H5", t=MONT[3], d=MONT[4] - MONT[3], off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.6, .76, .40), (1, 1.5, .76, .40)], tin=("punch", .12)),
    dict(file="E", t=MONT[4], d=MONT[5] - MONT[4], off=1.4, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.5, .58, .70), (1, 1.4, .58, .70)], tin=("punch", .12),
         spark=(0.05, 0.30, 0.95, 1.0)),
    # 17.79-22  closing line + CTA (sync)
    sync("S5", 54.9, 17.79, 4.21, 55.29, zoom=[(0, 1.15, .55, .45), (1, 1.0, .55, .45)], tin=("dissolve", .3)),
]

# text, emoji codepoint file, t_in, t_out, style, y (top of block, px)
TEXTS = [
    ("WEH|CANTIKNYA!", "1f60d", 0.10, 1.75, "hook", 260),
    ("Cantik & Elegan|Bila Dipakai", "1f497", 2.05, 4.95, "label", 300),
    ("Jatuh &|Beralun Cantik", "2728", 5.30, 9.20, "label", 300),
    ("Detail Batu|Memang Premium", "1f48e", 10.30, 13.20, "label", 300),
    ("Banyak Pilihan|Warna Cantik", "1f308", 13.60, 17.65, "label", 300),
    ("GRAB SEKARANG!", "1f6cd-fe0f", 18.20, 22.0, "cta", 215),
    ("Tekan beg kuning di bawah", None, 18.80, 22.0, "sub", 385),
]

# kind, time (s), gain, pan(-1..1)  - kept light so the voice stays clear
SFX = [
    ("impact", 0.0, 0.5, 0), ("pop", 0.10, 0.6, 0), ("sparkle", 0.45, 0.3, .3),
    ("whoosh", 1.8, 0.45, -.2), ("pop", 2.05, 0.45, 0),
    ("whoosh", 5.07, 0.4, .3), ("pop", 5.30, 0.45, 0),
    ("whoosh", 7.06, 0.45, -.2),
    ("tick", 9.30, 0.35, 0),
    ("whoosh", 10.08, 0.45, .2), ("pop", 10.30, 0.45, 0), ("sparkle", 10.9, 0.3, -.3),
    ("whoosh", 13.37, 0.4, -.3), ("pop", 13.60, 0.45, 0),
    ("whoosh", 15.10, 0.4, .2),
    ("tick", 15.64, 0.3, -.4), ("tick", 16.18, 0.3, .4), ("tick", 16.72, 0.3, -.4),
    ("tick", 17.26, 0.3, .4),
    ("whoosh", 17.79, 0.3, 0), ("impact", 18.20, 0.3, 0), ("pop", 18.20, 0.55, 0),
    ("pop", 18.80, 0.3, .2),
]
