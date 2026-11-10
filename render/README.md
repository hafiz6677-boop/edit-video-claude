# Tudung TikTok Shop promo: render pipeline

Output: `output/tudung_tiktokshop_final.mp4` (1080x1920, 30fps, 22s, H.264 + AAC)

1. Prep clips (60fps motion interpolation + colour grade):
   `cd clips && SRC=/path/raw.MP4 xargs -P4 -L1 ../render/prep_clip.sh < ../render/clip_list.txt`
2. Music + SFX (original, synthesised; safe for commercial use): `python3 audio.py audio.wav`
3. Compose: `python3 render.py <clips_dir> <assets_dir> audio.wav out.mp4`
   assets = npm packages `@fontsource/montserrat` and `emoji-datasource-google`, extracted.

Edit the shots, text, and SFX in `timeline.py`.
