import React from "react";
import { Composition } from "remotion";
import { FizimaAd } from "./FizimaAd";
import edl from "./edl.json";

export const RemotionRoot: React.FC = () => (
  <Composition id="FizimaAd" component={FizimaAd} durationInFrames={edl.total} fps={edl.fps} width={1080} height={1920} />
);
