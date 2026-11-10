import type { Caption } from "@remotion/captions";

/**
 * One segment of a raw product video, already resolved by
 * `scripts/make-video.mjs`. `src` points to a normalised H.264 proxy copy
 * inside `public/cache/` — the original upload is never touched.
 */
export type ClipInput = {
  /** Path relative to the public dir (passed to staticFile()). */
  src: string;
  /** Where to start inside the source clip, in seconds. */
  startSec: number;
  /** How long to use from the source clip, in seconds. */
  durationSec: number;
  /** Source width / height of the proxy (for portrait vs landscape layout). */
  width: number;
  height: number;
  hasAudio: boolean;
  /** Zoom style for this clip. */
  zoom: "in" | "out" | "punch" | "none";
  /** Zoom focus point, 0..1 (0.5/0.5 = centre). */
  focusX: number;
  focusY: number;
  /** Word-level captions with timestamps relative to the SOURCE clip. */
  captions: Caption[];
};

export type MusicInput = {
  src: string;
  /** 0..1 */
  volume: number;
  startSec: number;
};

export type TikTokShopProps = {
  fps: number;
  /** Transition length between clips, in seconds. */
  transitionSec: number;
  clips: ClipInput[];
  hook: {
    /** Main Malay hook line, e.g. "Tudung ni memang VIRAL!" */
    text: string;
    /** Words in `text` that get the highlight colour. */
    highlight: string[];
    /** Small line above the hook, e.g. "JANGAN SCROLL!" */
    kicker: string;
    durationSec: number;
  };
  product: {
    name: string;
    price: string;
    oldPrice: string;
    badge: string;
  };
  cta: {
    text: string;
    sub: string;
    durationSec: number;
  };
  music: MusicInput | null;
  /** Volume of the clips' own sound (0 = mute). */
  originalAudioVolume: number;
  theme: {
    accent: string;
    accentText: string;
  };
};
