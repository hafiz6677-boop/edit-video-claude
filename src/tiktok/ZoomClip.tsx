import { Video } from "@remotion/media";
import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { ClipInput } from "./types";

/**
 * Renders one raw clip full-screen (9:16) with a professional zoom move:
 *  - "in":    slow Ken-Burns push-in
 *  - "out":   slow pull-out
 *  - "punch": quick spring punch-in at the cut, then a gentle drift
 * Landscape / square footage gets a blurred fill background instead of
 * being cropped aggressively.
 */
export const ZoomClip: React.FC<{
  clip: ClipInput;
  volume: number;
}> = ({ clip, volume }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const durationInFrames = Math.max(1, Math.round(clip.durationSec * fps));
  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  let scale = 1;
  if (clip.zoom === "in") {
    scale = interpolate(progress, [0, 1], [1.0, 1.14]);
  } else if (clip.zoom === "out") {
    scale = interpolate(progress, [0, 1], [1.14, 1.0]);
  } else if (clip.zoom === "punch") {
    const punch = spring({
      frame,
      fps,
      config: { damping: 14, stiffness: 160, mass: 0.6 },
    });
    scale = interpolate(punch, [0, 1], [1.25, 1.06]) + progress * 0.05;
  }

  const sourceAspect = clip.width / clip.height;
  const targetAspect = width / height;
  // Treat footage within ~15% of 9:16 as portrait and fill the frame.
  const isPortraitish = sourceAspect <= targetAspect * 1.15;

  const trimBefore = Math.round(clip.startSec * fps);
  const trimAfter = trimBefore + durationInFrames;
  const src = staticFile(clip.src);
  const transformOrigin = `${clip.focusX * 100}% ${clip.focusY * 100}%`;

  if (isPortraitish) {
    return (
      <AbsoluteFill style={{ backgroundColor: "black", overflow: "hidden" }}>
        <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin }}>
          <Video
            src={src}
            trimBefore={trimBefore}
            trimAfter={trimAfter}
            volume={clip.hasAudio ? volume : 0}
            muted={!clip.hasAudio || volume === 0}
            objectFit="cover"
            style={{ width: "100%", height: "100%" }}
          />
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ backgroundColor: "black", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: "scale(1.2)", filter: "blur(40px) brightness(0.6)" }}>
        <Video
          src={src}
          trimBefore={trimBefore}
          trimAfter={trimAfter}
          muted
          objectFit="cover"
          style={{ width: "100%", height: "100%" }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          transform: `scale(${scale * 1.15})`,
          transformOrigin,
          justifyContent: "center",
        }}
      >
        <Video
          src={src}
          trimBefore={trimBefore}
          trimAfter={trimAfter}
          volume={clip.hasAudio ? volume : 0}
          muted={!clip.hasAudio || volume === 0}
          objectFit="contain"
          style={{ width: "100%", height: "100%" }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
