#!/usr/bin/env node
/* global process, console */
/**
 * One-command TikTok Shop video maker.
 *
 *   npm run make                 # render every project in projects/
 *   npm run make -- tudung-satin # render only projects/tudung-satin/
 *   npm run make -- tudung-satin --dry   # only prepare props, no render
 *
 * For each project folder it:
 *   1. finds raw videos (.mp4 .mov .m4v .webm .mkv .3gp), sorted by filename
 *   2. creates a normalised H.264 *copy* in public/cache/ (originals are only read)
 *   3. writes project.json with editable Malay defaults if it does not exist
 *   4. picks segments, zoom moves, captions (.srt sidecar or project.json text)
 *   5. adds background music (project folder or assets/music/) if available
 *   6. renders out/<project>.mp4 at 1080x1920 H.264/AAC and verifies the output
 */
import { execFileSync, spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseSrt } from "@remotion/captions";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PROJECTS_DIR = path.join(ROOT, "projects");
const PUBLIC_DIR = path.join(ROOT, "public");
const CACHE_DIR = path.join(PUBLIC_DIR, "cache");
const OUT_DIR = path.join(ROOT, "out");
const GLOBAL_MUSIC_DIR = path.join(ROOT, "assets", "music");

const VIDEO_EXT = new Set([".mp4", ".mov", ".m4v", ".webm", ".mkv", ".3gp"]);
const AUDIO_EXT = new Set([".mp3", ".m4a", ".aac", ".wav", ".ogg"]);
const FPS = 30;

// ---------- Malay defaults ---------------------------------------------------

const HOOKS = [
  { kicker: "JANGAN SCROLL!", text: "Tudung ni memang VIRAL!", highlight: ["VIRAL!"] },
  { kicker: "WAJIB TENGOK", text: "Tudung paling SELESA pernah saya pakai", highlight: ["SELESA"] },
  { kicker: "STOK TERHAD", text: "Cantik gila, harga MURAH je!", highlight: ["MURAH"] },
  { kicker: "RAMAI DAH ORDER", text: "Tak perlu iron, terus CANTIK!", highlight: ["CANTIK!"] },
  { kicker: "PROMO HARI INI", text: "Bawal premium yang ramai CARI!", highlight: ["CARI!"] },
];

const DEFAULT_CAPTIONS = [
  "Kain lembut dan selesa dipakai",
  "Senang nak bentuk, tak perlu banyak pin",
  "Tak jarang, sesuai untuk harian",
  "Warna cantik, nampak lebih berseri",
  "Sesuai untuk kerja, kuliah dan majlis",
];

const ZOOM_PATTERN = ["punch", "in", "out", "in", "punch", "out"];

// ---------- helpers ------------------------------------------------------------

const log = (...a) => console.log("•", ...a);
const hash = (s) => crypto.createHash("sha1").update(s).digest("hex").slice(0, 16);
const seedIndex = (s, n) => parseInt(hash(s).slice(0, 8), 16) % n;
const round2 = (n) => Math.round(n * 100) / 100;

const ffprobe = (file) => {
  const out = execFileSync(
    "ffprobe",
    ["-v", "error", "-print_format", "json", "-show_streams", "-show_format", file],
    { encoding: "utf8" },
  );
  return JSON.parse(out);
};

const probeVideo = (file) => {
  const info = ffprobe(file);
  const v = info.streams.find((s) => s.codec_type === "video");
  if (!v) throw new Error(`No video stream in ${file}`);
  const rotationTag = Number(v.tags?.rotate ?? 0);
  const sideRot = Number(
    (v.side_data_list ?? []).find((d) => d.rotation !== undefined)?.rotation ?? 0,
  );
  const rotation = Math.abs(rotationTag || sideRot) % 180 === 90;
  return {
    width: rotation ? v.height : v.width,
    height: rotation ? v.width : v.height,
    duration: Number(info.format.duration ?? v.duration ?? 0),
    hasAudio: info.streams.some((s) => s.codec_type === "audio"),
  };
};

const fingerprint = (file) => {
  const st = fs.statSync(file);
  return `${file}|${st.size}|${st.mtimeMs}`;
};

/** Normalised H.264 copy for reliable rendering (handles HEVC/iPhone .mov, rotation, VFR). */
const makeProxy = (file, meta) => {
  const dir = path.join(CACHE_DIR, "proxies");
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, `${hash(fingerprint(file))}.mp4`);
  if (fs.existsSync(out)) return out;
  const portrait = meta.height >= meta.width;
  const scale = portrait ? "scale=-2:'min(1920,ih)'" : "scale='min(1920,iw)':-2";
  log(`  membuat salinan proxy: ${path.basename(file)}`);
  const tmp = `${out}.tmp.mp4`;
  const args = [
    "-y", "-v", "error", "-i", file,
    "-vf", `${scale},fps=${FPS},format=yuv420p`,
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
    "-movflags", "+faststart",
  ];
  if (meta.hasAudio) args.push("-c:a", "aac", "-b:a", "192k", "-ar", "48000");
  else args.push("-an");
  args.push(tmp);
  execFileSync("ffmpeg", args, { stdio: "inherit" });
  fs.renameSync(tmp, out);
  return out;
};

/** Spread the words of a text line evenly over [fromMs, toMs] as Caption[] */
const textToCaptions = (text, fromMs, toMs) => {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  const step = (toMs - fromMs) / words.length;
  return words.map((w, i) => ({
    text: i === 0 ? w : ` ${w}`,
    startMs: Math.round(fromMs + i * step),
    endMs: Math.round(fromMs + (i + 1) * step),
    timestampMs: Math.round(fromMs + (i + 0.5) * step),
    confidence: null,
  }));
};

const srtToCaptions = (srtFile) => {
  const { captions } = parseSrt({ input: fs.readFileSync(srtFile, "utf8") });
  // SRT gives whole lines; split each line into words for word highlighting.
  return captions.flatMap((c) => textToCaptions(c.text.trim(), c.startMs, c.endMs));
};

const listFiles = (dir, exts) =>
  fs.existsSync(dir)
    ? fs
        .readdirSync(dir)
        .filter((f) => !f.startsWith(".") && exts.has(path.extname(f).toLowerCase()))
        .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
        .map((f) => path.join(dir, f))
    : [];

const defaultProjectConfig = (name, videoFiles) => {
  const hook = HOOKS[seedIndex(name, HOOKS.length)];
  return {
    $readme:
      "Edit teks di bawah, kemudian jalankan semula: npm run make -- " + name,
    targetSeconds: 20,
    maxClipSeconds: 5,
    transitionSec: 0.4,
    keepOriginalAudio: false,
    originalAudioVolume: 1,
    musicVolume: 0.35,
    hook: { ...hook, durationSec: 2.6 },
    product: {
      name: "Tudung Premium",
      price: "RM19.90",
      oldPrice: "RM39.90",
      badge: "Promosi hari ini",
    },
    cta: { text: "Tekan beg kuning sekarang!", sub: "Stok terhad", durationSec: 2.5 },
    theme: { accent: "#FFE135", accentText: "#111111" },
    clips: Object.fromEntries(
      videoFiles.map((f, i) => [
        path.basename(f),
        {
          caption: DEFAULT_CAPTIONS[i % DEFAULT_CAPTIONS.length],
          start: null,
          duration: null,
          zoom: null,
          focusX: 0.5,
          focusY: 0.45,
        },
      ]),
    ),
  };
};

// ---------- main per-project pipeline ----------------------------------------

const prepareProject = (name) => {
  const dir = path.join(PROJECTS_DIR, name);
  const videoFiles = listFiles(dir, VIDEO_EXT);
  if (videoFiles.length === 0) {
    log(`[${name}] tiada video dijumpai, langkau.`);
    return null;
  }
  const before = new Map(videoFiles.map((f) => [f, fingerprint(f)]));

  const configPath = path.join(dir, "project.json");
  if (!fs.existsSync(configPath)) {
    fs.writeFileSync(configPath, JSON.stringify(defaultProjectConfig(name, videoFiles), null, 2) + "\n");
    log(`[${name}] project.json baharu dicipta (boleh edit teks hook/harga/caption).`);
  }
  const defaults = defaultProjectConfig(name, videoFiles);
  const user = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const cfg = {
    ...defaults,
    ...user,
    hook: { ...defaults.hook, ...user.hook },
    product: { ...defaults.product, ...user.product },
    cta: { ...defaults.cta, ...user.cta },
    theme: { ...defaults.theme, ...user.theme },
    clips: { ...defaults.clips, ...user.clips },
  };

  const n = videoFiles.length;
  const perClip = Math.min(cfg.maxClipSeconds, Math.max(1.8, cfg.targetSeconds / n));

  const clips = videoFiles.map((file, i) => {
    const base = path.basename(file);
    const o = { ...defaults.clips[base], ...(cfg.clips[base] ?? {}) };
    const meta = probeVideo(file);
    const proxy = makeProxy(file, meta);
    const pmeta = probeVideo(proxy);
    const usableEnd = Math.max(0.5, pmeta.duration - 0.15);

    let want = o.duration ?? perClip;
    if (i === 0) want = Math.max(want, cfg.hook.durationSec + 0.6);
    if (i === n - 1) want = Math.max(want, cfg.cta.durationSec + 1);
    let start = o.start ?? Math.max(0.2, (usableEnd - want) * 0.3);
    start = Math.min(Math.max(0, start), Math.max(0, usableEnd - 0.5));
    const durationSec = Math.max(0.5, Math.min(want, usableEnd - start));

    const srt = path.join(dir, `${path.parse(base).name}.srt`);
    let captions = [];
    if (fs.existsSync(srt)) {
      captions = srtToCaptions(srt);
      log(`  caption dari ${path.basename(srt)}`);
    } else if (o.caption) {
      // Keep the first clip's hook readable: start its caption after the hook.
      const capStart = i === 0 ? start + Math.min(durationSec * 0.6, cfg.hook.durationSec) : start + 0.15;
      const capEnd = start + durationSec - 0.1;
      if (capEnd - capStart > 0.6) captions = textToCaptions(o.caption, capStart * 1000, capEnd * 1000);
    }

    return {
      src: path.relative(PUBLIC_DIR, proxy).split(path.sep).join("/"),
      startSec: round2(start),
      durationSec: round2(durationSec),
      width: pmeta.width,
      height: pmeta.height,
      hasAudio: pmeta.hasAudio,
      zoom: o.zoom ?? ZOOM_PATTERN[i % ZOOM_PATTERN.length],
      focusX: o.focusX ?? 0.5,
      focusY: o.focusY ?? 0.45,
      captions,
    };
  });

  // Background music: projects/<name>/ first, else assets/music/, else none.
  const musicFiles = listFiles(dir, AUDIO_EXT);
  const pool = musicFiles.length ? musicFiles : listFiles(GLOBAL_MUSIC_DIR, AUDIO_EXT);
  let music = null;
  if (pool.length) {
    const src = pool[seedIndex(name, pool.length)];
    const mdir = path.join(CACHE_DIR, "music");
    fs.mkdirSync(mdir, { recursive: true });
    const dest = path.join(mdir, `${hash(fingerprint(src))}${path.extname(src).toLowerCase()}`);
    if (!fs.existsSync(dest)) fs.copyFileSync(src, dest);
    music = {
      src: path.relative(PUBLIC_DIR, dest).split(path.sep).join("/"),
      volume: cfg.keepOriginalAudio ? Math.min(cfg.musicVolume, 0.2) : cfg.musicVolume,
      startSec: 0,
    };
    log(`  muzik: ${path.relative(ROOT, src)}`);
  } else {
    log("  tiada muzik (letak .mp3/.m4a dalam folder projek atau assets/music/)");
  }

  const props = {
    fps: FPS,
    transitionSec: cfg.transitionSec,
    clips,
    hook: cfg.hook,
    product: cfg.product,
    cta: cfg.cta,
    music,
    originalAudioVolume: cfg.keepOriginalAudio ? cfg.originalAudioVolume : 0,
    theme: cfg.theme,
  };

  // Safety: originals must be byte-for-byte untouched (size + mtime unchanged).
  for (const [f, fp] of before) {
    if (fingerprint(f) !== fp) throw new Error(`Original file changed unexpectedly: ${f}`);
  }
  return props;
};

const render = (name, props) => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const propsFile = path.join(OUT_DIR, `${name}.props.json`);
  fs.writeFileSync(propsFile, JSON.stringify(props, null, 2));
  const outFile = path.join(OUT_DIR, `${name}.mp4`);
  log(`[${name}] render → ${path.relative(ROOT, outFile)}`);
  const res = spawnSync(
    "npx",
    [
      "remotion", "render", "src/index.ts", "TikTokShop", outFile,
      `--props=${propsFile}`,
      "--codec=h264", "--crf=18", "--pixel-format=yuv420p", "--audio-codec=aac",
      // Normally Remotion downloads its own headless browser. Only if that is
      // impossible (e.g. a sandbox blocking remotion.media) set
      // REMOTION_BROWSER_EXECUTABLE to a local chrome-headless-shell.
      ...(process.env.REMOTION_BROWSER_EXECUTABLE
        ? [`--browser-executable=${process.env.REMOTION_BROWSER_EXECUTABLE}`]
        : []),
    ],
    { cwd: ROOT, stdio: "inherit" },
  );
  if (res.status !== 0) throw new Error(`Render failed for ${name}`);

  const info = ffprobe(outFile);
  const v = info.streams.find((s) => s.codec_type === "video");
  const ok = v.width === 1080 && v.height === 1920 && v.codec_name === "h264";
  log(
    `[${name}] ${ok ? "✔" : "✘"} ${v.width}x${v.height} ${v.codec_name}, ` +
      `${Number(info.format.duration).toFixed(1)}s, audio: ${info.streams.some((s) => s.codec_type === "audio") ? "ya" : "tiada"}`,
  );
  if (!ok) throw new Error("Output is not 1080x1920 H.264");
  return outFile;
};

// ---------- CLI --------------------------------------------------------------

const args = process.argv.slice(2);
const dry = args.includes("--dry");
const names = args.filter((a) => !a.startsWith("--"));
const all = fs.existsSync(PROJECTS_DIR)
  ? fs
      .readdirSync(PROJECTS_DIR, { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith("_") && !d.name.startsWith("."))
      .map((d) => d.name)
  : [];
const targets = names.length ? names : all;
if (targets.length === 0) {
  console.log("Tiada projek. Buat folder projects/<nama-produk>/ dan letak video mentah di dalamnya.");
  process.exit(0);
}

const results = [];
for (const name of targets) {
  if (!fs.existsSync(path.join(PROJECTS_DIR, name))) {
    console.error(`Projek tidak wujud: projects/${name}`);
    process.exitCode = 1;
    continue;
  }
  log(`[${name}] menyediakan…`);
  const props = prepareProject(name);
  if (!props) continue;
  if (dry) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
    fs.writeFileSync(path.join(OUT_DIR, `${name}.props.json`), JSON.stringify(props, null, 2));
    log(`[${name}] props disimpan (dry run).`);
    continue;
  }
  results.push(render(name, props));
}
if (results.length) {
  console.log("\nSiap:\n" + results.map((r) => "  " + path.relative(ROOT, r)).join("\n"));
}
