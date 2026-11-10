# edit-video-claude

Automated pipeline that cut 4 raw TikTok-Live hijab recordings into one 60-second
TikTok Shop ad: `output/FIZIMA_BOUTIQUE_TIKTOK_60SEC.mp4` (1080×1920, 30 fps, H.264 + AAC).

## Pipeline

1. **Transcribe**: Whisper large-v3-turbo (sherpa-onnx, int8) with Silero VAD, language `ms`.
   Pause detection plus growing-window re-transcription find sentence boundaries, so no cut lands mid-sentence.
2. **Edit plan**: `tools/plan.py` holds the edit decision list, Malay captions with yellow keywords,
   headlines, punch-in zooms and sparkle zones. It writes `remotion/src/edl.json`.
3. **Media prep**: `tools/prepare_media.py <raw dir> remotion/public`
   - Frame-accurate cuts, center 9:16 crop (only a 1.125× upscale), light denoise and sharpening, 30 fps.
   - Speed-ramped CTA b-roll (1.5× into 0.8× slow motion, motion-interpolated).
   - The host's original voice, untouched in pitch: high-pass, light FFT denoise, gentle EQ and compression, loudness normalisation.
   - Procedurally synthesised whoosh, swoosh, pop, sparkle, impact and riser SFX, plus a soft music bed that ducks automatically under speech. Everything is generated in code, so the audio is royalty-free.
   - Final mix at -14 LUFS, true peak ≤ -1.5 dBTP.
4. **Render**: Remotion (`remotion/src/FizimaAd.tsx`) adds Ken Burns zooms, punch-ins, gentle shake, whip-pan, zoom-blur and flash transitions, sparkles, kinetic captions, headlines and the CTA.
5. **Mux**: ffmpeg combines the Remotion video with `mix.wav` (AAC 256k, `+faststart`).

```bash
python3 tools/plan.py
python3 tools/prepare_media.py /path/to/raw remotion/public   # raw clips named v1..v4.mp4
cd remotion && npm install && npx remotion render src/index.ts FizimaAd out/video.mp4 --muted \
  --browser-executable=/path/to/chrome --crf=15
ffmpeg -i out/video.mp4 -i public/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k \
  -movflags +faststart -shortest ../output/FIZIMA_BOUTIQUE_TIKTOK_60SEC.mp4
```
