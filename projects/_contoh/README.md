# Contoh projek (template)

Folders whose name starts with `_` are skipped by `npm run make`.

To make a new video:

1. Create a folder such as `projects/tudung-satin-hitam/`.
2. Put the raw videos inside, e.g. `IMG_1234.MOV`. They're used in filename order.
3. Optional: add `music.mp3` (or `.m4a`) for background music.
4. Optional: add `IMG_1234.srt` next to a video to use its exact spoken captions.
5. Run `npm run make -- tudung-satin-hitam`.

The first run creates `project.json`, where you can edit the hook, price, CTA,
captions and per-clip trims/zoom. Run the same command again to re-render.
The output goes to `out/tudung-satin-hitam.mp4` (1080x1920, H.264 + AAC).

Original videos are only read. The editor works on normalised copies in
`public/cache/`.
