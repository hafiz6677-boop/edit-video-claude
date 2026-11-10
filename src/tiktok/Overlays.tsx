import { createTikTokStyleCaptions, type Caption } from "@remotion/captions";
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { FONT_FAMILY } from "./fonts";
import type { TikTokShopProps } from "./types";

// TikTok UI covers roughly the bottom ~420px and the right ~140px of a
// 1080x1920 frame. All overlays stay inside this safe area.
const SAFE_SIDE = 70;
const SAFE_RIGHT = 150;

const textStroke = (px: number) =>
  `${px}px 0 0 #000, -${px}px 0 0 #000, 0 ${px}px 0 #000, 0 -${px}px 0 #000, ` +
  `${px}px ${px}px 0 #000, -${px}px -${px}px 0 #000, ${px}px -${px}px 0 #000, ` +
  `-${px}px ${px}px 0 #000, 0 10px 30px rgba(0,0,0,0.55)`;

const normalise = (w: string) =>
  w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

/** Animated Malay hook: kicker pill + word-by-word pop-in headline. */
export const Hook: React.FC<{
  hook: TikTokShopProps["hook"];
  theme: TikTokShopProps["theme"];
}> = ({ hook, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = Math.round(hook.durationSec * fps);
  const exit = interpolate(frame, [total - 8, total], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const highlights = new Set(hook.highlight.map(normalise));
  const words = hook.text.split(/\s+/).filter(Boolean);

  const kickerIn = spring({ frame, fps, config: { damping: 12 } });

  return (
    <AbsoluteFill
      style={{
        top: 230,
        paddingLeft: SAFE_SIDE,
        paddingRight: SAFE_RIGHT - 40,
        alignItems: "center",
        fontFamily: FONT_FAMILY,
        opacity: exit,
        transform: `translateY(${(1 - exit) * -40}px)`,
      }}
    >
      {hook.kicker ? (
        <div
          style={{
            backgroundColor: "#ff2d55",
            color: "white",
            fontWeight: 900,
            fontSize: 44,
            padding: "10px 28px",
            borderRadius: 999,
            letterSpacing: 2,
            transform: `scale(${kickerIn}) rotate(${interpolate(kickerIn, [0, 1], [-8, -3])}deg)`,
            marginBottom: 28,
            boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
          }}
        >
          {hook.kicker}
        </div>
      ) : null}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "6px 30px",
          textAlign: "center",
        }}
      >
        {words.map((word, i) => {
          const s = spring({
            frame: frame - 4 - i * 3,
            fps,
            config: { damping: 10, stiffness: 180, mass: 0.7 },
          });
          const isHighlight = highlights.has(normalise(word));
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                fontWeight: 900,
                fontSize: 96,
                lineHeight: 1.08,
                textTransform: "uppercase",
                color: isHighlight ? theme.accentText : "white",
                backgroundColor: isHighlight ? theme.accent : "transparent",
                padding: isHighlight ? "0 16px" : 0,
                borderRadius: 14,
                textShadow: isHighlight ? "none" : textStroke(5),
                transform: `scale(${s}) translateY(${(1 - s) * 40}px)`,
                opacity: Math.min(1, s * 1.5),
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/**
 * TikTok-style word-by-word captions. `captions` use timestamps relative to
 * the source clip; `startSec` is where the used segment starts in that clip.
 */
export const ClipCaptions: React.FC<{
  captions: Caption[];
  startSec: number;
  theme: TikTokShopProps["theme"];
}> = ({ captions, startSec, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pages = useMemo(
    () =>
      createTikTokStyleCaptions({
        captions,
        combineTokensWithinMilliseconds: 1400,
      }).pages,
    [captions],
  );
  const nowMs = startSec * 1000 + (frame / fps) * 1000;
  const page = pages.find(
    (p) => nowMs >= p.startMs && nowMs < p.startMs + Math.max(p.durationMs, 400),
  );
  if (!page) {
    return null;
  }
  const pageFrame = ((nowMs - page.startMs) / 1000) * fps;
  const pop = spring({
    frame: pageFrame,
    fps,
    config: { damping: 12, stiffness: 200 },
  });

  return (
    <AbsoluteFill
      style={{
        top: undefined,
        bottom: 520,
        height: "auto",
        paddingLeft: SAFE_SIDE,
        paddingRight: SAFE_RIGHT,
        alignItems: "center",
        fontFamily: FONT_FAMILY,
      }}
    >
      <div
        style={{
          textAlign: "center",
          fontWeight: 800,
          fontSize: 66,
          lineHeight: 1.2,
          color: "white",
          textShadow: textStroke(4),
          transform: `scale(${interpolate(pop, [0, 1], [0.85, 1])})`,
          whiteSpace: "pre-wrap",
        }}
      >
        {page.tokens.map((t, i) => {
          const active = nowMs >= t.fromMs && nowMs < t.toMs;
          return (
            <span
              key={i}
              style={{
                color: active ? theme.accent : "white",
              }}
            >
              {t.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Price / product badge that slides in after the hook. */
export const ProductBadge: React.FC<{
  product: TikTokShopProps["product"];
  theme: TikTokShopProps["theme"];
}> = ({ product, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });
  if (!product.name && !product.price) {
    return null;
  }
  return (
    <AbsoluteFill
      style={{
        top: 200,
        left: SAFE_SIDE,
        width: "auto",
        height: "auto",
        fontFamily: FONT_FAMILY,
        transform: `translateX(${(1 - s) * -700}px)`,
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(0,0,0,0.62)",
          borderLeft: `12px solid ${theme.accent}`,
          borderRadius: 18,
          padding: "18px 28px",
          maxWidth: 720,
        }}
      >
        {product.badge ? (
          <div
            style={{
              color: theme.accent,
              fontWeight: 900,
              fontSize: 34,
              letterSpacing: 1.5,
              textTransform: "uppercase",
            }}
          >
            {product.badge}
          </div>
        ) : null}
        {product.name ? (
          <div style={{ color: "white", fontWeight: 800, fontSize: 48, lineHeight: 1.15 }}>
            {product.name}
          </div>
        ) : null}
        {product.price ? (
          <div style={{ display: "flex", alignItems: "baseline", gap: 18, marginTop: 6 }}>
            <span style={{ color: theme.accent, fontWeight: 900, fontSize: 64 }}>
              {product.price}
            </span>
            {product.oldPrice ? (
              <span
                style={{
                  color: "rgba(255,255,255,0.7)",
                  fontWeight: 600,
                  fontSize: 38,
                  textDecoration: "line-through",
                }}
              >
                {product.oldPrice}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

/** Closing call-to-action ("Tekan beg kuning sekarang!"). */
export const CallToAction: React.FC<{
  cta: TikTokShopProps["cta"];
  theme: TikTokShopProps["theme"];
}> = ({ cta, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 11, stiffness: 150 } });
  const pulse = 1 + Math.sin((frame / fps) * Math.PI * 3) * 0.035;
  const dim = interpolate(frame, [0, 10], [0, 0.45], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY }}>
      <AbsoluteFill style={{ backgroundColor: `rgba(0,0,0,${dim})` }} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          paddingLeft: SAFE_SIDE,
          paddingRight: SAFE_RIGHT - 40,
          paddingBottom: 300,
        }}
      >
        <div
          style={{
            transform: `scale(${s * pulse})`,
            backgroundColor: theme.accent,
            color: theme.accentText,
            fontWeight: 900,
            fontSize: 78,
            lineHeight: 1.1,
            textAlign: "center",
            padding: "30px 46px",
            borderRadius: 36,
            boxShadow: "0 16px 50px rgba(0,0,0,0.45)",
            textTransform: "uppercase",
          }}
        >
          {cta.text}
        </div>
        {cta.sub ? (
          <div
            style={{
              marginTop: 34,
              color: "white",
              fontWeight: 800,
              fontSize: 50,
              textAlign: "center",
              textShadow: textStroke(4),
              opacity: interpolate(frame, [8, 18], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
            }}
          >
            {cta.sub}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
