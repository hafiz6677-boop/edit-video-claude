import { Composition, continueRender, delayRender } from "remotion";
import { fontsLoaded } from "./tiktok/fonts";
import {
  calculateTikTokShopMetadata,
  TikTokShopVideo,
} from "./tiktok/TikTokShopVideo";
import type { TikTokShopProps } from "./tiktok/types";

const fontHandle = delayRender("Loading fonts");
fontsLoaded.then(() => continueRender(fontHandle));

// Default props are only used when opening Remotion Studio without a project.
// `npm run make` passes real props generated from projects/<name>/.
export const defaultTikTokShopProps: TikTokShopProps = {
  fps: 30,
  transitionSec: 0.4,
  clips: [],
  hook: {
    text: "Tudung ni memang VIRAL!",
    highlight: ["VIRAL!"],
    kicker: "JANGAN SCROLL!",
    durationSec: 2.6,
  },
  product: {
    name: "Tudung Bawal Premium",
    price: "RM19.90",
    oldPrice: "RM39.90",
    badge: "Promosi hari ini",
  },
  cta: {
    text: "Tekan beg kuning sekarang!",
    sub: "Stok terhad",
    durationSec: 2.5,
  },
  music: null,
  originalAudioVolume: 0.0,
  theme: { accent: "#FFE135", accentText: "#111111" },
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="TikTokShop"
      component={TikTokShopVideo}
      durationInFrames={150}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultTikTokShopProps}
      calculateMetadata={calculateTikTokShopMetadata}
    />
  );
};
