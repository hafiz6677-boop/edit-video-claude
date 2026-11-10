import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Audio, OffthreadVideo, Sequence, continueRender, delayRender, interpolate, random,
  spring, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import "@fontsource/anton/400.css";
import "@fontsource/montserrat/800.css";
import "@fontsource/montserrat/900.css";
import edl from "./edl.json";

const YELLOW = "#FFD700";
const W = 1080;
const H = 1920;
const T = 6; // transition half-length in frames

type Seg = (typeof edl.segments)[number];

const outline = (px: number, color = "#000") => {
  const s: string[] = [];
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    s.push(`${(Math.cos(a) * px).toFixed(1)}px ${(Math.sin(a) * px).toFixed(1)}px 0 ${color}`);
  }
  return s.join(",");
};

// ---------------------------------------------------------------- video layer
type TransitionState = { tx: number; ty: number; scale: number; bx: number; by: number; blur: number };

const transitionAt = (f: number, n: number, tin: string, tout: string | null): TransitionState => {
  const st: TransitionState = { tx: 0, ty: 0, scale: 1, bx: 0, by: 0, blur: 0 };
  const apply = (type: string, p: number, dir: 1 | -1) => {
    // p: 0 (no effect) .. 1 (at the cut). dir: +1 incoming, -1 outgoing
    const e = Easing.in(Easing.cubic)(p);
    if (type.startsWith("whip")) {
      const amp = 0.11;
      st.scale = Math.max(st.scale, 1 + 0.26 * e);
      if (type === "whipU") { st.ty += dir * e * amp * H; st.by = 60 * e; }
      else {
        const s = type === "whipL" ? 1 : -1; // whipL: content travels right -> left
        st.tx += (dir === 1 ? s : -s) * e * amp * W;
        st.bx = 70 * e;
      }
    } else if (type === "zoom") {
      st.scale = Math.max(st.scale, 1 + (dir === 1 ? 0.3 : 0.22) * e);
      st.blur = Math.max(st.blur, 12 * e);
    } else if (type === "flash") {
      st.scale = Math.max(st.scale, 1 + 0.04 * e);
    }
  };
  if (f < T && tin !== "none") apply(tin, 1 - f / T, 1);
  if (tout && f >= n - T) apply(tout, (f - (n - T) + 1) / T, -1);
  return st;
};

const Sparkles: React.FC<{ seg: Seg | null; zones: Seg["sparkles"]; offset: number }> = ({ zones, offset }) => {
  const frame = useCurrentFrame() + offset; // global frame
  const stars: React.ReactNode[] = [];
  zones.forEach((z, zi) => {
    for (let s = z.f0; s < z.f1; s += 4) {
      const life = 16 + Math.floor(random(`l${zi}-${s}`) * 8);
      const age = frame - s;
      if (age < 0 || age > life) continue;
      const x = z.x0 + random(`x${zi}-${s}`) * (z.x1 - z.x0);
      const y = z.y0 + random(`y${zi}-${s}`) * (z.y1 - z.y0);
      const size = 18 + random(`s${zi}-${s}`) * 30;
      const p = age / life;
      const k = Math.sin(p * Math.PI);
      stars.push(
        <svg key={`${zi}-${s}`} width={size} height={size} viewBox="-10 -10 20 20"
          style={{ position: "absolute", left: x - size / 2, top: y - size / 2, opacity: 0.9 * k,
            transform: `scale(${0.3 + 0.9 * k}) rotate(${p * 90}deg)`, mixBlendMode: "screen",
            filter: "drop-shadow(0 0 6px rgba(255,240,180,0.95)) drop-shadow(0 0 14px rgba(255,215,0,0.6))" }}>
          <path d="M0,-10 C1,-2 2,-1 10,0 C2,1 1,2 0,10 C-1,2 -2,1 -10,0 C-2,-1 -1,-2 0,-10Z" fill="#fff" />
        </svg>,
      );
    }
  });
  return <AbsoluteFill style={{ pointerEvents: "none" }}>{stars}</AbsoluteFill>;
};

const SegmentVideo: React.FC<{ seg: Seg | any; file: string; tout: string | null; cta?: boolean }> = ({ seg, file, tout, cta }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = seg.frames;
  const kb = seg.kb ?? [1.0, 1.06, 0.5, 0.55];
  const kbZoom = interpolate(f, [0, n], [kb[0], kb[1]], { easing: Easing.inOut(Easing.sin) });

  // punch-in zooms (spring in, ease back after ~1.6 s) + optional gentle shake
  let pz = 1, pox = 0.5, poy = 0.5, shx = 0, shy = 0;
  for (const p of seg.punch ?? []) {
    const lf = p.f - seg.start;
    if (f < lf) continue;
    const inn = spring({ frame: f - lf, fps, config: { damping: 15, stiffness: 140 } });
    const out = interpolate(f - lf, [48, 75], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
    pz = 1 + (p.z - 1) * inn * (1 - out);
    pox = p.x; poy = p.y;
    if (p.shake && f - lf < 14) {
      const d = 1 - (f - lf) / 14;
      shx = (random(`sx${f}`) - 0.5) * 14 * d;
      shy = (random(`sy${f}`) - 0.5) * 14 * d;
    }
  }

  const tr = transitionAt(f, n, cta ? seg.tin : (seg.start === 0 ? "none" : seg.tin), tout);
  const id = `blur-${seg.id ?? "cta"}`;
  const ctaBlur = cta ? interpolate(f, [30, 52], [0, 9], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const ctaDim = cta ? interpolate(f, [30, 52], [1, 0.62], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  const filters = [
    tr.bx || tr.by ? `url(#${id})` : "",
    tr.blur + ctaBlur > 0.05 ? `blur(${(tr.blur + ctaBlur).toFixed(2)}px)` : "",
    `contrast(1.03) brightness(${ctaDim.toFixed(3)})`,
  ].join(" ");

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", overflow: "hidden" }}>
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <filter id={id} x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={`${tr.bx.toFixed(1)} ${tr.by.toFixed(1)}`} edgeMode="duplicate" />
        </filter>
      </svg>
      <AbsoluteFill style={{
        transform: `translate(${(tr.tx + shx).toFixed(1)}px, ${(tr.ty + shy).toFixed(1)}px) scale(${(tr.scale * kbZoom).toFixed(4)})`,
        transformOrigin: `${kb[2] * 100}% ${kb[3] * 100}%`, filter: filters,
      }}>
        <AbsoluteFill style={{ transform: `scale(${pz.toFixed(4)})`, transformOrigin: `${pox * 100}% ${poy * 100}%` }}>
          <OffthreadVideo src={staticFile(file)} muted style={{ width: W, height: H }} />
          {seg.sparkles ? <Sparkles seg={seg} zones={seg.sparkles} offset={seg.start} /> : null}
          {cta ? <Sparkles seg={null} offset={seg.start}
            zones={[{ x0: 120, y0: 700, x1: 950, y1: 1700, f0: seg.start, f1: seg.start + seg.frames }]} /> : null}
        </AbsoluteFill>
      </AbsoluteFill>
      {/* subtle premium vignette */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.28) 100%)" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- flashes
const Flashes: React.FC = () => {
  const frame = useCurrentFrame();
  let o = 0;
  const cuts = [...edl.segments.map((s) => ({ f: s.start, t: s.tin })), { f: edl.cta.start, t: edl.cta.tin }];
  for (const c of cuts) {
    const peak = c.f === 0 ? 0.55 : c.t === "flash" ? 0.8 : c.t === "zoom" ? 0.3 : 0.15;
    const v = interpolate(frame, [c.f - 2, c.f, c.f + 8], [0, peak, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    o = Math.max(o, v);
  }
  return <AbsoluteFill style={{ backgroundColor: "#fff", opacity: o, mixBlendMode: "screen" }} />;
};

// ---------------------------------------------------------------- captions
const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const caps = edl.segments.flatMap((s) => s.captions);
  const idx = caps.findIndex((c, i) => {
    const next = caps[i + 1];
    const end = next && next.f0 - c.f1 <= 9 ? next.f0 : c.f1;
    return frame >= c.f0 && frame < end;
  });
  if (idx < 0) return null;
  const c = caps[idx];
  const next = caps[idx + 1];
  const end = next && next.f0 - c.f1 <= 9 ? next.f0 : c.f1;
  const exit = interpolate(frame, [end - 4, end], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 80, width: 860, top: 1300, display: "flex", flexWrap: "wrap",
        justifyContent: "center", alignContent: "flex-start", gap: "4px 16px", opacity: exit,
        transform: `scale(${0.96 + 0.04 * exit})` }}>
        {c.words.map((w, i) => {
          const s = spring({ frame: frame - w.f, fps, config: { damping: 11, stiffness: 220, mass: 0.6 } });
          const vis = frame >= w.f;
          return (
            <span key={i} style={{
              fontFamily: "Montserrat", fontWeight: 900, fontSize: w.k ? 66 : 60, lineHeight: 1.15,
              textTransform: "uppercase", color: w.k ? YELLOW : "#fff", letterSpacing: 0.5,
              textShadow: `${outline(5)}, 0 8px 18px rgba(0,0,0,0.55)`,
              opacity: vis ? Math.min(1, s * 1.6) : 0, display: "inline-block",
              transform: `translateY(${(1 - s) * 22}px) scale(${0.55 + 0.45 * s})`,
            }}>{w.t}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- headlines
const Headline: React.FC<{ main: string; sub: string | null; dur: number; subDelay: number }> = ({ main, sub, dur, subDelay }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = main.split(" ");
  const size = Math.min(132, Math.floor(1700 / Math.max(8, main.length)));
  const exit = interpolate(f, [dur - 6, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bar = spring({ frame: f - 6, fps, config: { damping: 20 } });
  const subS = spring({ frame: f - subDelay, fps, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ opacity: exit, transform: `scale(${0.9 + 0.1 * exit})`, transformOrigin: "50% 300px" }}>
      <div style={{ position: "absolute", top: 235, left: 70, width: 880, textAlign: "center" }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0 22px" }}>
          {words.map((w, i) => {
            const s = spring({ frame: f - i * 3, fps, config: { damping: 9, stiffness: 180, mass: 0.7 } });
            return (
              <span key={i} style={{ fontFamily: "Anton", fontSize: size, lineHeight: 1.08, color: YELLOW,
                display: "inline-block", letterSpacing: 1,
                textShadow: `${outline(7)}, 0 10px 24px rgba(0,0,0,0.6)`, opacity: Math.min(1, s * 2),
                transform: `translateY(${(1 - s) * 60}px) scale(${0.3 + 0.7 * s}) rotate(${(1 - s) * -6}deg)` }}>{w}</span>
            );
          })}
        </div>
        <div style={{ margin: "10px auto 0", height: 8, width: `${bar * 62}%`, borderRadius: 4, background: YELLOW,
          boxShadow: "0 0 0 3px #000, 0 0 18px rgba(255,215,0,0.7)" }} />
        {sub ? (
          <div style={{ marginTop: 18, display: "inline-block", padding: "8px 26px", borderRadius: 40,
            background: "rgba(0,0,0,0.55)", fontFamily: "Montserrat", fontWeight: 800, fontSize: 44, color: "#fff",
            opacity: subS, transform: `translateY(${(1 - subS) * 24}px)`, textShadow: outline(2) }}>{sub}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- CTA
const CtaText: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = (d: number, damping = 8) => spring({ frame: f - d, fps, config: { damping, stiffness: 170, mass: 0.8 } });
  const a = pop(10), b = pop(19, 7), c = pop(28), sub = pop(44, 14), arrow = pop(36, 12);
  const pulse = f > 50 ? 1 + 0.035 * Math.sin((f - 50) / 4.5) : 1;
  const line = (s: number, extra: React.CSSProperties = {}) => ({
    fontFamily: "Anton", display: "block", lineHeight: 1.05, opacity: Math.min(1, s * 2),
    transform: `scale(${0.2 + 0.8 * s}) translateY(${(1 - s) * 50}px)`, ...extra,
  });
  const fadeOut = interpolate(f, [edl.cta.frames - 6, edl.cta.frames], [1, 0.0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <div style={{ position: "absolute", top: 520, left: 60, width: 900, textAlign: "center", transform: `scale(${pulse})` }}>
        <span style={line(a, { fontSize: 128, color: "#fff", textShadow: `${outline(7)}, 0 10px 30px rgba(0,0,0,.6)` })}>TEKAN</span>
        <span style={line(b, { fontSize: 168, color: YELLOW, textShadow: `${outline(8)}, 0 0 40px rgba(255,215,0,.65), 0 10px 30px rgba(0,0,0,.6)` })}>BEG KUNING</span>
        <span style={line(c, { fontSize: 120, color: "#fff", textShadow: `${outline(7)}, 0 10px 30px rgba(0,0,0,.6)` })}>
          SEKARANG <span style={{ fontFamily: "Noto Color Emoji", textShadow: "none" }}>🛍️</span>
        </span>
        <div style={{ marginTop: 34, display: "inline-block", padding: "12px 30px", borderRadius: 50, background: "rgba(0,0,0,0.6)",
          border: `3px solid ${YELLOW}`, fontFamily: "Montserrat", fontWeight: 800, fontSize: 34, color: "#fff", whiteSpace: "nowrap",
          opacity: sub, transform: `translateY(${(1 - sub) * 30}px)` }}>
          Design <span style={{ color: YELLOW }}>Rafflesia</span> &amp; <span style={{ color: YELLOW }}>Fiona</span> · Full Diamond
        </div>
      </div>
      {/* arrow pointing toward the yellow bag / product link (bottom-left in TikTok) */}
      <svg width="170" height="170" viewBox="0 0 100 100" style={{ position: "absolute", left: 110, top: 1250 + Math.sin(f / 3.2) * 18,
        opacity: arrow, transform: `scale(${arrow}) rotate(35deg)`, filter: "drop-shadow(0 0 14px rgba(255,215,0,.7))" }}>
        <path d="M38 6 H62 V58 H82 L50 94 L18 58 H38 Z" fill={YELLOW} stroke="#000" strokeWidth="5" strokeLinejoin="round" />
      </svg>
    </AbsoluteFill>
  );
};

const Brand: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [4, 16], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", top: 160, left: 0, width: W - 120, textAlign: "center", opacity: o * 0.92 }}>
      <span style={{ fontFamily: "Montserrat", fontWeight: 800, fontSize: 30, letterSpacing: 6, color: "#fff",
        padding: "6px 22px", borderRadius: 30, background: "rgba(0,0,0,0.35)", border: "1.5px solid rgba(255,215,0,0.85)" }}>
        FIZIMA BOUTIQUE
      </span>
    </div>
  );
};

// ---------------------------------------------------------------- sound
// Host voice + ducked music bed, plus every sound effect placed on its cue frame.
const SoundTrack: React.FC = () => (
  <>
    <Audio src={staticFile("bed.wav")} />
    {edl.sfx.map((c, i) => (
      <Sequence key={`sfx${i}`} from={c.f} durationInFrames={Math.min(60, edl.total - c.f)} name={`sfx ${c.why}`}>
        <Audio src={staticFile(`sfx/${c.sfx}.wav`)} volume={c.vol} />
      </Sequence>
    ))}
  </>
);

// ---------------------------------------------------------------- main
export const FizimaAd: React.FC = () => {
  const [handle] = useState(() => delayRender("fonts"));
  useEffect(() => {
    Promise.all([
      document.fonts.load('400 100px "Anton"'),
      document.fonts.load('900 60px "Montserrat"'),
      document.fonts.load('800 40px "Montserrat"'),
    ]).then(() => continueRender(handle)).catch(() => continueRender(handle));
  }, [handle]);

  const segs = edl.segments;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <SoundTrack />
      {segs.map((s, i) => (
        <Sequence key={s.id} from={s.start} durationInFrames={s.frames}>
          <SegmentVideo seg={s} file={`seg_${s.id}.mp4`} tout={i + 1 < segs.length ? segs[i + 1].tin : edl.cta.tin} />
        </Sequence>
      ))}
      <Sequence from={edl.cta.start} durationInFrames={edl.cta.frames}>
        <SegmentVideo seg={{ ...edl.cta, id: "cta", kb: [1.02, 1.1, 0.5, 0.5], punch: [] }} file="seg_CTA.mp4" tout={null} cta />
      </Sequence>
      <Flashes />
      {segs.flatMap((s) => s.headlines).map((h, i) => (
        <Sequence key={`h${i}`} from={h.f0} durationInFrames={h.f1 - h.f0}>
          <Headline main={h.main} sub={h.sub} dur={h.f1 - h.f0} subDelay={h.subDelay} />
        </Sequence>
      ))}
      <Captions />
      <Sequence from={0} durationInFrames={edl.cta.start}><Brand /></Sequence>
      <Sequence from={edl.cta.start} durationInFrames={edl.cta.frames}><CtaText /></Sequence>
    </AbsoluteFill>
  );
};
