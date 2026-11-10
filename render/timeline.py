"""Edit decision list for the tudung TikTok Shop promo.

All cut points sit on the 120 BPM beat grid (0.5 s). Source clips are pre-rendered
by prep_clips.sh (60 fps motion-interpolated + colour graded); `off` is the start
offset (s) inside that pre-rendered clip.

speed: [(u, speed)] keyframes over normalised clip time u in [0,1] (smooth ramp)
zoom:  [(u, zoom, cx, cy)] keyframes; zoom 1 = fill 9:16 frame; cx/cy = centre of
       interest in normalised source coordinates.
spark: region (x0,y0,x1,y1, normalised output) where existing stones get a glint.
"""

BPM = 120
FPS = 30
W, H = 1080, 1920
TOTAL = 22.0

# name, file, timeline start, duration, off, speed, zoom, transition-in, spark region
CLIPS = [
    # 0-2  HOOK: mint fabric right at the lens, stones visible -> pull back
    dict(file="A", t=0.0, d=2.0, off=0.2, speed=[(0, .75), (1, .75)],
         zoom=[(0, 1.38, .40, .52), (1, 1.06, .45, .50)], tin=("flash", .25),
         spark=(0.0, 0.25, 0.72, 1.0)),
    # 2-4.5  mint fabric swings to camera, speed ramp into slow-mo
    dict(file="B", t=2.0, d=2.5, off=0.2,
         speed=[(0, 1.1), (.3, 1.1), (.45, .5), (.85, .5), (1, .9)],
         zoom=[(0, 1.0, .45, .45), (1, 1.14, .42, .55)], tin=("zoom", .3)),
    # 4.5-6.5  gold / cream fabric brought to camera
    dict(file="C", t=4.5, d=2.0, off=0.4, speed=[(0, 1.0), (.4, .6), (1, .8)],
         zoom=[(0, 1.05, .40, .50), (1, 1.22, .38, .55)], tin=("whip", .3)),
    # 6.5-9  finger points at the stones -> dynamic push-in on the detail
    dict(file="D", t=6.5, d=2.5, off=0.2, speed=[(0, .7), (1, .7)],
         zoom=[(0, 1.25, .32, .66), (.5, 1.45, .28, .68), (1, 1.55, .28, .69)],
         tin=("zoom", .3), spark=(0.0, 0.35, 0.70, 1.0)),
    # 9-11  stones on the dusty-blue shawl being worn (chest detail)
    dict(file="E", t=9.0, d=2.0, off=0.35, speed=[(0, .8), (1, .8)],
         zoom=[(0, 1.55, .58, .66), (1, 1.28, .58, .62)], tin=("dissolve", .35),
         spark=(0.05, 0.40, 0.95, 1.0)),
    # 11-13.5  worn, front view
    dict(file="F", t=11.0, d=2.5, off=0.2, speed=[(0, .9), (1, .9)],
         zoom=[(0, 1.0, .60, .50), (1, 1.10, .62, .48)], tin=("flash", .3)),
    # 13.5-15.5  side turn showing the drape
    dict(file="G", t=13.5, d=2.0, off=0.2, speed=[(0, .9), (1, .9)],
         zoom=[(0, 1.12, .40, .45), (1, 1.0, .42, .48)], tin=("whip", .3)),
    # 15.5-18.5  colour choices, one per beat
    dict(file="H1", t=15.5, d=.5, off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.25, .30, .50), (1, 1.15, .30, .50)], tin=("zoom", .2)),
    dict(file="H2", t=16.0, d=.5, off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.25, .38, .55), (1, 1.15, .38, .55)], tin=("punch", .12)),
    dict(file="H3", t=16.5, d=.5, off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.75, .20, .38), (1, 1.62, .20, .38)], tin=("punch", .12)),
    dict(file="H4", t=17.0, d=.5, off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.35, .25, .55), (1, 1.25, .25, .55)], tin=("punch", .12)),
    dict(file="H5", t=17.5, d=.5, off=0.1, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.6, .76, .40), (1, 1.5, .76, .40)], tin=("punch", .12)),
    dict(file="E", t=18.0, d=.5, off=1.4, speed=[(0, 1), (1, 1)],
         zoom=[(0, 1.2, .55, .50), (1, 1.12, .55, .50)], tin=("punch", .12)),
    # 18.5-22  hero ending + CTA
    dict(file="I", t=18.5, d=3.5, off=0.35, speed=[(0, .66), (1, .66)],
         zoom=[(0, 1.18, .55, .42), (1, 1.0, .55, .45)], tin=("dissolve", .35)),
]

# text, emoji codepoint file, t_in, t_out, style, y (top of block, px)
TEXTS = [
    ("WEH|CANTIKNYA!", "1f60d", 0.10, 1.95, "hook", 260),
    ("Jatuh &|Beralun Cantik", "2728", 2.25, 6.35, "label", 300),
    ("Detail Batu|Memang Premium", "1f48e", 6.70, 8.90, "label", 300),
    ("Cantik & Elegan|Bila Dipakai", "1f497", 11.20, 15.35, "label", 300),
    ("Banyak Pilihan|Warna Cantik", "1f308", 15.60, 18.35, "label", 300),
    ("GRAB SEKARANG!", "1f6cd-fe0f", 18.75, 22.0, "cta", 215),
    ("Tekan beg kuning di bawah", None, 19.40, 22.0, "sub", 385),
]

# kind, time (s), gain, pan(-1..1)
SFX = [
    ("impact", 0.0, 0.7, 0), ("pop", 0.10, 0.8, 0), ("sparkle", 0.45, 0.45, .3),
    ("whoosh", 2.0, 0.8, -.2), ("pop", 2.25, 0.7, 0),
    ("whoosh", 4.5, 0.7, .3),
    ("whoosh", 6.5, 0.8, -.2), ("pop", 6.70, 0.7, 0), ("sparkle", 7.1, 0.5, -.3),
    ("sparkle", 9.15, 0.4, .3), ("whoosh", 9.0, 0.35, 0),
    ("whoosh", 11.0, 0.4, .2), ("pop", 11.20, 0.7, 0),
    ("whoosh", 13.5, 0.7, -.3),
    ("whoosh", 15.5, 0.7, .2), ("pop", 15.60, 0.7, 0),
    ("tick", 16.0, 0.5, -.4), ("tick", 16.5, 0.5, .4), ("tick", 17.0, 0.5, -.4),
    ("tick", 17.5, 0.5, .4), ("tick", 18.0, 0.5, 0),
    ("whoosh", 18.5, 0.45, 0), ("impact", 18.75, 0.45, 0), ("pop", 18.75, 0.85, 0),
    ("pop", 19.40, 0.45, .2), ("sparkle", 19.0, 0.35, 0),
]
