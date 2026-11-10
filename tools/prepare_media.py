"""Cut video segments, process the host's voice, synthesize SFX + music, mix audio.

usage: python3 tools/prepare_media.py <dir with v1..v4.mp4> <out dir (remotion/public)>

Every sound effect and the music bed is generated here from oscillators and
filtered noise (no third-party samples), so the audio is 100% royalty-free.
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, PUB = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(PUB, exist_ok=True)
TMP = os.path.join(PUB, "_tmp"); os.makedirs(TMP, exist_ok=True)
edl = json.load(open(os.path.join(ROOT, "remotion", "src", "edl.json")))
FPS, TOTAL = edl["fps"], edl["total"]
DUR = TOTAL / FPS

# Source is 960x1920 (1:2). Crop the centre 9:16 window and upscale only 1.125x.
VF = ("crop=960:1707:0:107,scale=1080:1920:flags=lanczos,"
      "hqdn3d=1.2:1.2:2.5:2.5,unsharp=5:5:0.45:5:5:0,fps=30,format=yuv420p")
ENC = ["-c:v", "libx264", "-preset", "slow", "-crf", "12", "-g", "15", "-bf", "0"]


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def cut_video():
    for s in edl["segments"]:
        out = os.path.join(PUB, f"seg_{s['id']}.mp4")
        if os.environ.get("REUSE") and os.path.exists(out):
            continue
        run(["ffmpeg", "-y", "-ss", f"{s['s']:.3f}", "-i", f"{SRC}/{s['src']}.mp4", "-an",
             "-vf", VF, "-frames:v", str(s["frames"]), *ENC, out])
    c = edl["cta"]
    fast_src = c["fast_src"]; fast_n = c["fast_out_frames"]; slow_n = c["frames"] - fast_n
    slow_src = slow_n / FPS * c["slow_rate"]
    a = os.path.join(TMP, "cta_a.mp4"); b = os.path.join(TMP, "cta_b.mp4")
    rate = fast_src / (fast_n / FPS)
    run(["ffmpeg", "-y", "-ss", f"{c['s']:.3f}", "-t", f"{fast_src + 0.2:.3f}", "-i", f"{SRC}/{c['src']}.mp4",
         "-an", "-vf", f"setpts=PTS/{rate:.4f}," + VF, "-frames:v", str(fast_n), *ENC, a])
    run(["ffmpeg", "-y", "-ss", f"{c['s'] + fast_src:.3f}", "-t", f"{slow_src + 0.3:.3f}", "-i",
         f"{SRC}/{c['src']}.mp4", "-an", "-vf",
         f"setpts=PTS/{c['slow_rate']},minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1," + VF,
         "-frames:v", str(slow_n), *ENC, b])
    lst = os.path.join(TMP, "cta.txt")
    open(lst, "w").write(f"file '{a}'\nfile '{b}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(PUB, "seg_CTA.mp4")])


def voice():
    """Original host voice, cut on the same frames as the video (lip-sync kept)."""
    parts = []
    for s in edl["segments"]:
        d = s["frames"] / FPS
        p = os.path.join(TMP, f"v_{s['id']}.wav")
        run(["ffmpeg", "-y", "-ss", f"{s['s']:.3f}", "-t", f"{d:.4f}", "-i", f"{SRC}/{s['src']}.mp4",
             "-vn", "-ac", "1", "-ar", str(SR),
             "-af", f"afade=t=in:d=0.012,afade=t=out:st={d - 0.018:.4f}:d=0.018,apad=whole_dur={d:.4f}",
             "-t", f"{d:.4f}", p])
        x, _ = sf.read(p, dtype="float32")
        n = s["frames"] * SR // FPS
        parts.append(np.pad(x, (0, max(0, n - len(x))))[:n])
    v = np.concatenate(parts)
    v = np.pad(v, (0, int(DUR * SR) - len(v)))
    raw = os.path.join(TMP, "voice_raw.wav"); sf.write(raw, v, SR)
    # gentle clean-up: rumble high-pass, light FFT denoise, presence, soft compression
    chain = ("highpass=f=75,afftdn=nr=8:nf=-50:tn=1,"
             "equalizer=f=3200:t=q:w=1.2:g=2,equalizer=f=250:t=q:w=1:g=-1.5,"
             "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2")
    stats = subprocess.run(["ffmpeg", "-i", raw, "-af", chain + ",loudnorm=I=-16:TP=-2:LRA=7:print_format=json",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(stats[stats.rindex("{"):stats.rindex("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-2:LRA=7:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    out = os.path.join(TMP, "voice.wav")
    run(["ffmpeg", "-y", "-i", raw, "-af", chain + "," + ln, "-ar", str(SR), out])
    x, _ = sf.read(out, dtype="float32")
    return np.pad(x, (0, max(0, int(DUR * SR) - len(x))))[:int(DUR * SR)]


# ----------------------------------------------------------------- synthesis
rng = np.random.default_rng(7)
t_ = lambda d: np.arange(int(d * SR)) / SR


def lp(x, fc):  # one-pole low-pass, fc may be an array
    a = np.exp(-2 * np.pi * np.broadcast_to(fc, x.shape) / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc; y[i] = acc
    return y


def bp_sweep(d, f0, f1, q=0.6):
    n = rng.standard_normal(int(d * SR))
    fc = np.geomspace(f0, f1, len(n))
    return lp(n, fc * (1 + q)) - lp(n, fc * (1 - q / 2))


def env(d, attack, shape=2.0):
    t = t_(d); a = np.clip(t / attack, 0, 1) ** shape
    r = np.clip((d - t) / (d - attack), 0, 1) ** shape
    return np.where(t < attack, a, r)


def norm(x, peak):
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def whoosh(d=0.5, f0=250, f1=3500):
    x = bp_sweep(d, f0, f1) * env(d, d * 0.62, 2.2)
    pan = np.linspace(-0.7, 0.7, len(x))
    return norm(np.stack([x * (1 - pan) / 2 * 1.4, x * (1 + pan) / 2 * 1.4], 1), 0.32)


def swoosh():
    x = bp_sweep(0.32, 900, 6000) * env(0.32, 0.18, 2.0)
    return norm(np.stack([x, x], 1), 0.22)


def pop():
    t = t_(0.12)
    f = 520 + 900 * np.exp(-t * 60)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    x[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return norm(np.stack([x, x], 1), 0.26)


def sparkle():
    d = 0.9; y = np.zeros((int(d * SR), 2))
    for k in range(9):
        st = rng.uniform(0, 0.45); f = rng.choice([2637, 3136, 3520, 3951, 4699, 5274])
        t = t_(0.35); s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 14)
        i = int(st * SR); p = rng.uniform(0.2, 0.8)
        y[i:i + len(s), 0] += s * (1 - p); y[i:i + len(s), 1] += s * p
    return norm(y, 0.13)


def impact():
    t = t_(0.7)
    f = 48 + 70 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    click = lp(rng.standard_normal(len(t)), 1800) * np.exp(-t * 45) * 2
    x = body + click
    return norm(np.stack([x, x], 1), 0.42)


def riser():
    x = bp_sweep(0.35, 2000, 9000) * env(0.35, 0.3, 2.5)
    return norm(np.stack([x, x], 1), 0.14)


def chime():
    t = t_(1.4); x = np.zeros(len(t))
    for f, a in ((1318.5, 1.0), (1975.5, 0.6), (2637, 0.35), (3951, 0.15)):
        x += a * np.sin(2 * np.pi * f * t) * np.exp(-t * (3 + f / 900))
    x[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    return norm(np.stack([x, x], 1), 0.2)


SFX = dict(whoosh=whoosh, swoosh=swoosh, pop=pop, sparkle=sparkle, impact=impact, riser=riser, chime=chime)


def music():
    """Soft, warm pad + pluck bed, 100 BPM, Fmaj7 - G6 - Em7 - Am7."""
    bpm = 100; beat = 60 / bpm; bar = 4 * beat
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n)
    m2f = lambda m: 440 * 2 ** ((m - 69) / 12)
    chords = [[53, 57, 60, 64], [55, 59, 62, 64], [52, 55, 59, 62], [57, 60, 64, 67]]
    bars = int(np.ceil(DUR / bar))
    for b in range(bars):
        ch = chords[b % 4]; i0 = int(b * bar * SR); d = bar + 0.4
        t = t_(d); e = np.minimum(1, t / 0.5) * np.minimum(1, (d - t) / 0.6)
        pad = np.zeros(len(t))
        for m in ch:
            for det in (-0.12, 0.12):
                ph = 2 * np.pi * m2f(m + det / 12) * t
                pad += np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
        pad *= e * 0.05
        seg = slice(i0, min(n, i0 + len(t))); k = seg.stop - seg.start
        L[seg] += pad[:k]; R[seg] += pad[:k]
        # bass
        tb = t_(bar); bs = np.sin(2 * np.pi * m2f(ch[0] - 12) * tb) * np.minimum(1, tb / 0.02) * np.exp(-tb * 1.2) * 0.12
        k2 = min(len(bs), n - i0); L[i0:i0 + k2] += bs[:k2]; R[i0:i0 + k2] += bs[:k2]
        # pluck arpeggio (8ths)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 24]
        for j, m in enumerate(arp):
            st = i0 + int(j * beat / 2 * SR)
            if st >= n: break
            tp = t_(0.5); f = m2f(m)
            s = (np.sin(2 * np.pi * f * tp) + 0.35 * np.sin(4 * np.pi * f * tp)) * np.exp(-tp * 7) * 0.05
            k3 = min(len(s), n - st); p = 0.35 if j % 2 else 0.65
            L[st:st + k3] += s[:k3] * (1 - p) * 2; R[st:st + k3] += s[:k3] * p * 2
        # soft kick on 1 and 3, shaker on off-beats
        for q in range(4):
            st = i0 + int(q * beat * SR)
            if st >= n: break
            if q in (0, 2):
                tk = t_(0.3); kk = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-tk * 30)) / SR) * np.exp(-tk * 12) * 0.16
                k4 = min(len(kk), n - st); L[st:st + k4] += kk[:k4]; R[st:st + k4] += kk[:k4]
            sh_st = st + int(beat / 2 * SR)
            if sh_st < n:
                ts = t_(0.08); sh = rng.standard_normal(len(ts)) * np.exp(-ts * 60) * 0.012
                sh = sh - lp(sh, 5000)
                k5 = min(len(sh), n - sh_st); L[sh_st:sh_st + k5] += sh[:k5]; R[sh_st:sh_st + k5] += sh[:k5]
    # cheap stereo reverb via FFT convolution with decaying noise
    ir_t = t_(1.2)
    for ch_ in (L, R):
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 4.5) * 0.02
        wet = np.fft.irfft(np.fft.rfft(ch_, 2 * n) * np.fft.rfft(ir, 2 * n))[:n]
        ch_ += wet
    x = np.stack([L, R], 1)
    return x / np.max(np.abs(x))


def export_sfx():
    """Write every SFX as its own WAV in public/sfx; Remotion places them on the timeline."""
    d = os.path.join(PUB, "sfx"); os.makedirs(d, exist_ok=True)
    for name, fn in SFX.items():
        for k in range(3):  # 3 random variants per type so repeats never sound identical
            sf.write(os.path.join(d, f"{name}{k}.wav"), fn().astype(np.float32), SR)


def main():
    cut_video()
    export_sfx()
    v = voice()
    n = len(v)
    bed = np.stack([v, v], 1).astype(np.float64)

    # music bed with automatic ducking under the host's speech
    mus = music()[:n]
    speech_end = edl["cta"]["start"] / FPS
    tt = np.arange(n) / SR
    w = int(0.05 * SR); e = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same"))
    active = (e > 10 ** (-38 / 20)).astype(float)
    active = np.convolve(active, np.ones(int(0.4 * SR)) / int(0.4 * SR), "same") > 0.05
    g = np.where(active, 10 ** (-27 / 20), 10 ** (-17 / 20))
    g = np.where(tt >= speech_end, 10 ** (-9 / 20), g)
    g = lp(g.astype(np.float64), 4.0)
    g *= np.clip(tt / 0.6, 0, 1) * np.clip((DUR - tt) / 1.2, 0, 1)
    bed += mus * g[:, None]
    # voice + music at -16 LUFS; SFX are layered on top inside Remotion
    pre = os.path.join(TMP, "bed_pre.wav"); sf.write(pre, bed.astype(np.float32), SR, subtype="FLOAT")
    run(["ffmpeg", "-y", "-i", pre, "-af", "volume=0dB", "-ar", str(SR), "-c:a", "pcm_s16le",
         "-t", f"{DUR}", os.path.join(PUB, "bed.wav")])
    print("bed + sfx exported")


if __name__ == "__main__":
    main()
