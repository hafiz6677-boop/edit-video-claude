# edit-video-claude — TikTok Shop hijab video maker (Remotion)

Turn raw hijab product clips into a 1080×1920 vertical TikTok Shop video with
one command. Each video gets:

- **Zoom effects**: punch-in on the opening clip, slow push-in and pull-out moves, and a blurred fill behind landscape footage
- **Smooth transitions** that rotate between zoom-punch, slide, push-cut, wipe and fade
- **Animated Malay hook**: a kicker pill plus a word-by-word pop-in headline with highlighted words
- **TikTok-style captions** that highlight each word, taken from a `.srt` file or from the text in `project.json`
- **Price badge** and a closing **"Tekan beg kuning sekarang!"** CTA
- **Background music** that fades in and out, if you add an audio file
- Export as **MP4 (H.264 + AAC), 1080×1920, 30 fps**

Your original videos are **never modified**. The script only reads them and
renders from normalised H.264 copies in `public/cache/` (this also handles
iPhone HEVC `.MOV` files and their rotation). It also checks that each
original's size and modification time are unchanged.

## Quick start

```bash
npm install
mkdir -p projects/tudung-satin
# copy raw clips (and optionally music.mp3) into projects/tudung-satin/
npm run make -- tudung-satin      # → out/tudung-satin.mp4
npm run make                      # render every project
```

The first run writes `projects/<name>/project.json`. Edit it to change:

| Field | Meaning |
| --- | --- |
| `hook.text`, `hook.highlight`, `hook.kicker` | Opening Malay hook. Words listed in `highlight` get the yellow box |
| `product.name/price/oldPrice/badge` | Price badge shown after the hook |
| `cta.text/sub` | Closing call to action |
| `clips["IMG_1.MOV"].caption` | Caption text for that clip |
| `clips[...].start/duration` | Manual trim in seconds (`null` = automatic) |
| `clips[...].zoom` | `"in"`, `"out"`, `"punch"`, `"none"` or `null` (automatic) |
| `clips[...].focusX/focusY` | Zoom focus point from 0 to 1, e.g. the face or the hijab |
| `targetSeconds`, `maxClipSeconds`, `transitionSec` | Pacing |
| `keepOriginalAudio`, `musicVolume` | Audio mix. Music is automatically lowered when the original audio is kept |

**Captions:** put `IMG_1234.srt` next to `IMG_1234.MOV` to use timed captions
(for example, exported from CapCut). Otherwise the `caption` text is spread
across the clip.

**Music:** the script uses an audio file in the project folder first, then one
from `assets/music/`. If there's none, the video has no music. Only use music
you have the rights to (or add TikTok's licensed sounds in the TikTok app after uploading).

## Preview / tweak in Remotion Studio

```bash
npm run make:dry -- tudung-satin   # writes out/tudung-satin.props.json
npm run dev                        # open Studio, paste props
```

## Rendering in restricted sandboxes

Remotion downloads its own headless Chrome from `remotion.media` the first
time it renders. If that host is blocked, point it at a local
chrome-headless-shell:

```bash
REMOTION_BROWSER_EXECUTABLE=/path/to/chrome-headless-shell npm run make
```

## Project layout

```
projects/<name>/        raw clips + optional music, .srt, project.json (yours)
assets/music/           shared background music pool (optional)
src/tiktok/             Remotion template (TikTokShopVideo, ZoomClip, Overlays)
scripts/make-video.mjs  automation: probe → proxy → props → render → verify
.claude/skills/         official Remotion Agent Skills (remotion-dev/skills)
out/                    rendered MP4s (git-ignored)
```

Remotion is free for individuals and companies of up to 3 people; larger
companies need a license (see remotion.pro/license).
