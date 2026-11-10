"""Original background music + SFX, synthesised from scratch (no third-party audio,
so it is free for commercial use). 120 BPM, timed to the edit in timeline.py."""
import os, subprocess, sys, wave
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from timeline import TOTAL, BPM, SFX, VOICE

SR = 44100
N = int(SR * (TOTAL + 0.5))
rng = np.random.default_rng(7)
BEAT = 60.0 / BPM
BAR = 4 * BEAT


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a, d, sustain=0.0, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4))
    rel = np.exp(-curve * np.maximum(0, t - a) / max(d, 1e-4))
    return e * (sustain + (1 - sustain) * rel)


def add(buf, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for k in range(len(x)):
        s = (1 - a) * x[k] + a * s
        y[k] = s
    return y


def hp(x, fc):
    return x - onepole_lp(x, fc)


def reverb_ir(seconds=2.2, decay=3.2):
    n = int(SR * seconds)
    t = np.arange(n) / SR
    ir = rng.standard_normal((2, n)) * np.exp(-decay * t)
    ir[:, : int(0.012 * SR)] = 0
    for c in range(2):
        ir[c] = onepole_lp(ir[c], 5000)
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


def convolve(x, ir):
    n = len(x) + len(ir) - 1
    nfft = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return y


# ---------------------------------------------------------------- music
CHORDS = [  # (bass midi, voicing)
    (41, [53, 57, 60, 64]),        # Fmaj7
    (45, [57, 60, 64, 67]),        # Am7
    (38, [50, 53, 57, 60, 64]),    # Dm9
    (46, [58, 62, 65, 69]),        # Bbmaj7
]
END_GROOVE = TOTAL - 1.0   # drums stop, final chord rings out


def music():
    L = np.zeros(N)
    R = np.zeros(N)
    pad = np.zeros(N)
    pluck = np.zeros(N)
    bass = np.zeros(N)
    drums = np.zeros(N)
    side = np.ones(N)  # sidechain pump

    nbars = int(np.ceil(TOTAL / BAR))
    for b in range(nbars):
        t0 = b * BAR
        last = t0 + BAR > END_GROOVE
        root, voicing = CHORDS[b % 4] if not last else CHORDS[0]
        dur = BAR + (2.0 if last else 0.05)
        n = int(dur * SR)
        t = np.arange(n) / SR
        # pad: detuned soft saw (few harmonics) -> warm
        p = np.zeros(n)
        for m in voicing:
            f = mtof(m)
            for det in (-0.12, 0.12):
                ff = f * 2 ** (det / 12)
                for h in range(1, 6):
                    p += np.sin(2 * np.pi * ff * h * t + rng.uniform(0, 6.28)) / (h ** 1.6)
        p *= env(n, 0.25, dur, sustain=0.85, curve=0.6)
        if last:
            p *= np.exp(-np.maximum(0, t - BAR * 0.5) * 1.6)
        add(pad, p, t0, 0.018)
        # bass: pulse on each 8th with sine+2nd harmonic
        for k in range(8 if not last else 1):
            bt = t0 + k * BEAT / 2
            if bt >= END_GROOVE:
                break
            nn = int((BEAT / 2 if not last else 2.0) * SR)
            tt = np.arange(nn) / SR
            f = mtof(root)
            s = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt)
            s *= env(nn, 0.005, 0.18 if not last else 1.2, curve=2.5)
            add(bass, np.tanh(1.5 * s), bt, 0.22 if k % 2 == 0 else 0.15)
        # pluck arp: 16ths, pattern up/down over chord tones +12
        tones = [m + 12 for m in voicing[-4:]]
        pattern = [0, 1, 2, 3, 2, 1, 3, 2]
        for k in range(16):
            st = t0 + k * BEAT / 4
            if st >= END_GROOVE + (BAR if last else 0) or (last and k > 7):
                break
            m = tones[pattern[k % 8]]
            nn = int(0.6 * SR)
            tt = np.arange(nn) / SR
            f = mtof(m)
            s = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt) + 0.1 * np.sin(2 * np.pi * 3 * f * tt)
            s *= env(nn, 0.002, 0.16, curve=4.5)
            add(pluck, s, st, 0.05 * (1.0 if k % 4 == 0 else 0.7))

    # drums
    for k in range(int(END_GROOVE / BEAT)):
        bt = k * BEAT
        # kick
        nn = int(0.35 * SR)
        tt = np.arange(nn) / SR
        f = 48 + 110 * np.exp(-tt * 30)
        ph = 2 * np.pi * np.cumsum(f) / SR
        kick = np.sin(ph) * np.exp(-tt * 9)
        add(drums, kick, bt, 0.55)
        i = int(bt * SR)
        dl = int(0.28 * SR)
        side[i:i + dl] = np.minimum(side[i:i + dl], 0.45 + 0.55 * (np.arange(min(dl, N - i)) / dl) ** 0.7)
        # snap on 2 & 4
        if k % 2 == 1:
            nn = int(0.2 * SR)
            tt = np.arange(nn) / SR
            nz = hp(rng.standard_normal(nn), 1200)
            snap = nz * (np.exp(-tt * 28) + 0.5 * np.exp(-(tt - 0.012).clip(0) * 40) * (tt > 0.012))
            add(drums, snap, bt, 0.10)
        # shaker hats on 8th off-beats + soft 16ths
        for s16, g in ((0.5, 0.05), (0.25, 0.018), (0.75, 0.018)):
            nn = int(0.06 * SR)
            tt = np.arange(nn) / SR
            nz = hp(rng.standard_normal(nn), 7000) * np.exp(-tt * 70)
            add(drums, nz, bt + s16 * BEAT, g)

    ir = reverb_ir()
    wetsrc = pad * 0.6 + pluck * 1.0 + drums * 0.15
    revL = convolve(wetsrc, ir[0])
    revR = convolve(wetsrc, ir[1])
    # dotted-8th delay on pluck, ping-pong
    d = int(0.75 * BEAT * SR)
    dlyL = np.zeros(N)
    dlyR = np.zeros(N)
    dlyL[d:] += pluck[:-d] * 0.35
    dlyR[2 * d:] += pluck[:-2 * d] * 0.22
    padS = pad * side
    L = padS + bass * side + drums + pluck * 0.9 + dlyL + revL * 0.28
    R = padS + bass * side + drums + pluck * 0.9 + dlyR + revR * 0.28
    # slight width on pad
    sh = int(0.011 * SR)
    R[sh:] += padS[:-sh] * 0.25
    L += padS * 0.25
    return np.stack([L, R])


# ---------------------------------------------------------------- sfx
def svf_bandsweep(x, f0, f1, q=2.0):
    """time-varying band-pass (Chamberlin SVF)."""
    n = len(x)
    fc = f0 * (f1 / f0) ** (np.linspace(0, 1, n) ** 0.8)
    low = band = 0.0
    out = np.empty(n)
    damp = 1.0 / q
    for k in range(n):
        f = 2 * np.sin(np.pi * fc[k] / SR / 2)
        high = x[k] - low - damp * band
        band += f * high
        low += f * band
        out[k] = band
    return out


def whoosh(length=0.55, peak=0.62, f0=300, f1=4500):
    n = int(length * SR)
    t = np.linspace(0, 1, n)
    nz = rng.standard_normal(n)
    s = svf_bandsweep(nz, f0, f1, q=1.6)
    e = np.where(t < peak, (t / peak) ** 2.2, np.exp(-(t - peak) / (1 - peak) * 4))
    s = s * e
    s /= np.abs(s).max()
    return s


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 320 + 900 * np.exp(-t * 55)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)
    s[: int(0.002 * SR)] += rng.standard_normal(int(0.002 * SR)) * 0.3
    return s / np.abs(s).max()


def sparkle(length=1.4, notes=9):
    n = int(length * SR)
    s = np.zeros(n)
    base = [88, 91, 93, 95, 96, 98, 100, 103]
    for k in range(notes):
        st = int((k / notes) * 0.55 * SR + rng.uniform(0, 0.02) * SR)
        f = mtof(base[rng.integers(0, len(base))])
        nn = n - st
        tt = np.arange(nn) / SR
        tone = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 6)
        s[st:] += tone * (0.6 + 0.4 * rng.random())
    shimmer = hp(rng.standard_normal(n), 9000) * env(n, 0.3, 0.5, curve=3) * 0.15
    s += shimmer
    return s / np.abs(s).max()


def impact():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f = 40 + 90 * np.exp(-t * 12)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5)
    s += hp(rng.standard_normal(n), 3000) * np.exp(-t * 12) * 0.25
    return s / np.abs(s).max()


def tick():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    s = hp(rng.standard_normal(n), 3500) * np.exp(-t * 90)
    return s / np.abs(s).max()


def load_voice(src):
    """host speech from the raw clip: de-noise, de-rumble, gentle compression."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-af",
                          "highpass=f=85,afftdn=nr=10:nf=-40,equalizer=f=3000:t=q:w=1.2:g=2,"
                          "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=3",
                          "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T


def voice_track(src):
    v = load_voice(src)
    out = np.zeros((2, N))
    mask = np.zeros(N)
    fade = int(0.015 * SR)
    for s0, s1, t0 in VOICE:
        seg = v[:, int(s0 * SR):int(s1 * SR)].copy()
        ramp = np.linspace(0, 1, fade)
        seg[:, :fade] *= ramp
        seg[:, -fade:] *= ramp[::-1]
        i = int(t0 * SR)
        j = min(N, i + seg.shape[1])
        out[:, i:j] += seg[:, : j - i]
        mask[i:j] = 1
    # smooth ducking envelope (150 ms ramps)
    k = int(0.15 * SR)
    mask = np.convolve(mask, np.ones(k) / k, mode="same")
    return out, mask


def main(out, src):
    mus = music()
    voice, vmask = voice_track(src)
    rms = np.sqrt(np.mean(voice[:, vmask > 0.9] ** 2)) + 1e-9
    voice *= 0.12 / rms
    sfx = np.zeros((2, N))
    gen = {"whoosh": whoosh, "pop": pop, "sparkle": sparkle, "impact": impact, "tick": tick}
    cache = {}
    for kind, t, gain, pan in SFX:
        if kind not in cache:
            cache[kind] = gen[kind]()
        s = cache[kind]
        start = t - (0.62 * 0.55 if kind == "whoosh" else 0.0)  # whoosh peaks on the cut
        add(sfx[0], s, max(0, start), gain * (1 - max(0, pan)))
        add(sfx[1], s, max(0, start), gain * (1 + min(0, pan)))
    ir = reverb_ir(1.2, 5)
    for c in range(2):
        sfx[c] += convolve(sfx[c], ir[c]) * 0.12
    mus = mus / np.abs(mus).max()
    duck = 0.9 - 0.6 * vmask            # music sits ~15 dB under the voice
    mix = voice + mus * 0.45 * duck + sfx * 0.22
    end = int(TOTAL * SR)
    tail = int(0.8 * SR)
    mix[:, end - tail:end] *= np.linspace(1, 0, tail) ** 1.5
    mix = mix[:, :end]
    mix = mix / np.abs(mix).max() * 0.9
    tmp = out + ".pre.wav"
    pcm = (mix.T * 32767).astype(np.int16)
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", str(SR), out], check=True)
    os.remove(tmp)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
