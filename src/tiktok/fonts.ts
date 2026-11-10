import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Fonts are bundled locally (public/fonts) so rendering works offline.
export const FONT_FAMILY = "Montserrat";

const weights = ["600", "800", "900"] as const;

export const fontsLoaded = Promise.all(
  weights.map((weight) =>
    loadFont({
      family: FONT_FAMILY,
      url: staticFile(`fonts/montserrat-latin-${weight}-normal.woff2`),
      weight,
    }),
  ),
);
