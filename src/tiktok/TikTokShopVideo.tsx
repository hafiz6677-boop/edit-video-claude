import { Audio } from "@remotion/media";
import {
  linearTiming,
  springTiming,
  TransitionSeries,
  type TransitionPresentation,
  type TransitionPresentationComponentProps,
} from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { pushCut } from "@remotion/transitions/push-cut";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import React from "react";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  staticFile,
  useVideoConfig,
  type CalculateMetadataFunction,
} from "remotion";
import { FONT_FAMILY } from "./fonts";
import { CallToAction, ClipCaptions, Hook, ProductBadge } from "./Overlays";
import type { TikTokShopProps } from "./types";
import { ZoomClip } from "./ZoomClip";

// ---------- timing helpers (shared by component + calculateMetadata) -------

export const clipFrames = (props: TikTokShopProps) =>
  props.clips.map((c) => Math.max(1, Math.round(c.durationSec * props.fps)));

export const transitionFrames = (props: TikTokShopProps) => {
  const frames = clipFrames(props);
  const wanted = Math.round(props.transitionSec * props.fps);
  // A transition can never be longer than either neighbouring clip.
  return frames.slice(1).map((f, i) => Math.max(0, Math.min(wanted, f - 1, frames[i] - 1)));
};

export const totalFrames = (props: TikTokShopProps) => {
  if (props.clips.length === 0) {
    return Math.round(5 * props.fps);
  }
  const clips = clipFrames(props).reduce((a, b) => a + b, 0);
  const trans = transitionFrames(props).reduce((a, b) => a + b, 0);
  return Math.max(1, clips - trans);
};

export const calculateTikTokShopMetadata: CalculateMetadataFunction<
  TikTokShopProps
> = ({ props }) => ({
  durationInFrames: totalFrames(props),
  fps: props.fps,
  width: 1080,
  height: 1920,
});

// ---------- custom "zoom punch" transition ---------------------------------

const ZoomPunchPresentation: React.FC<
  TransitionPresentationComponentProps<Record<string, never>>
> = ({ children, presentationDirection, presentationProgress }) => {
  const p = presentationProgress;
  const style: React.CSSProperties =
    presentationDirection === "exiting"
      ? { transform: `scale(${1 + p * 0.35})`, opacity: 1 - p, filter: `blur(${p * 12}px)` }
      : { transform: `scale(${1.35 - p * 0.35})`, opacity: p, filter: `blur(${(1 - p) * 12}px)` };
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};

const zoomPunch = (): TransitionPresentation<Record<string, never>> => ({
  component: ZoomPunchPresentation,
  props: {},
});

// Rotate through a set of clean, professional transitions.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const pickTransition = (i: number): TransitionPresentation<any> => {
  switch (i % 5) {
    case 0:
      return zoomPunch();
    case 1:
      return slide({ direction: "from-right" });
    case 2:
      return pushCut({ flashOpacity: 0.35 });
    case 3:
      return wipe({ direction: "from-bottom-left" });
    default:
      return fade();
  }
};

// ---------- main component --------------------------------------------------

export const TikTokShopVideo: React.FC<TikTokShopProps> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();
  const frames = clipFrames(props);
  const trans = transitionFrames(props);
  const hookFrames = Math.min(Math.round(props.hook.durationSec * fps), durationInFrames);
  const ctaFrames = Math.min(Math.round(props.cta.durationSec * fps), durationInFrames);
  const badgeFrom = hookFrames;
  const badgeDuration = durationInFrames - ctaFrames - badgeFrom;
  const music = props.music;

  if (props.clips.length === 0) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor: "#111",
          color: "white",
          justifyContent: "center",
          alignItems: "center",
          fontFamily: FONT_FAMILY,
          fontSize: 56,
          fontWeight: 800,
          textAlign: "center",
          padding: 80,
        }}
      >
        Letak video tudung dalam projects/&lt;nama&gt;/ dan jalankan npm run make
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <TransitionSeries name="Klip produk">
        {props.clips.map((clip, i) => (
          <React.Fragment key={i}>
            {i > 0 && trans[i - 1] > 0 ? (
              <TransitionSeries.Transition
                presentation={pickTransition(i - 1)}
                timing={
                  i % 2 === 0
                    ? linearTiming({ durationInFrames: trans[i - 1] })
                    : springTiming({
                        durationInFrames: trans[i - 1],
                        config: { damping: 200 },
                      })
                }
              />
            ) : null}
            <TransitionSeries.Sequence
              name={`Klip ${i + 1}`}
              durationInFrames={frames[i]}
            >
              <ZoomClip clip={clip} volume={props.originalAudioVolume} />
              {clip.captions.length > 0 ? (
                <ClipCaptions
                  captions={clip.captions}
                  startSec={clip.startSec}
                  theme={props.theme}
                />
              ) : null}
            </TransitionSeries.Sequence>
          </React.Fragment>
        ))}
      </TransitionSeries>

      {badgeDuration > fps ? (
        <Sequence name="Harga produk" from={badgeFrom} durationInFrames={badgeDuration}>
          <ProductBadge product={props.product} theme={props.theme} />
        </Sequence>
      ) : null}

      <Sequence name="Hook" durationInFrames={hookFrames}>
        <Hook hook={props.hook} theme={props.theme} />
      </Sequence>

      <Sequence
        name="CTA"
        from={durationInFrames - ctaFrames}
        durationInFrames={ctaFrames}
      >
        <CallToAction cta={props.cta} theme={props.theme} />
      </Sequence>

      {music ? (
        <Audio
          name="Muzik latar"
          src={staticFile(music.src)}
          trimBefore={Math.round(music.startSec * fps)}
          loop
          volume={(f) =>
            music.volume *
            interpolate(
              f,
              [0, fps * 0.6, durationInFrames - fps * 1.2, durationInFrames],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            )
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};
