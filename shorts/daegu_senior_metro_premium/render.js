// scene.html 을 프레임 단위로 캡처해 9:16 쇼츠(mp4)로 만든다.
//   node render.js --font-dir <Pretendard OTF 폴더> [--fps 30] [--out 파일.mp4] [--still 초,초,...]
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, v, i, arr) => (v.startsWith("--") ? acc.concat([[v.slice(2), arr[i + 1]]]) : acc), [])
);
const FPS = Number(args.fps || 30);
const TIMELINE = args.timeline || path.join(__dirname, "timeline.json");
const tl = fs.existsSync(TIMELINE) ? JSON.parse(fs.readFileSync(TIMELINE, "utf8")) : null;
const TOTAL = tl ? tl.total : 55;
const NARRATION = args.narration; // narrate.py 로 만든 한국어 음성(wav)
const OUT = path.resolve(args.out || path.join(__dirname, "daegu_senior_metro_premium.mp4"));
const FONT_DIR = args["font-dir"];
if (!FONT_DIR) throw new Error("--font-dir 에 Pretendard OTF 폴더를 지정하세요");

const WEIGHTS = { Regular: 400, Medium: 500, SemiBold: 600, Bold: 700, ExtraBold: 800 };
const fontCss = Object.entries(WEIGHTS)
  .map(([name, w]) => `@font-face{font-family:"Pretendard";font-weight:${w};src:url("${pathToFileURL(path.join(FONT_DIR, `Pretendard-${name}.otf`)).href}")}`)
  .join("\n");

function audio(total) {
  // 배경음악만, 또는 한국어 내레이션 + 배경음악(작게) 혼합
  const m = music(total);
  if (!NARRATION) return m;
  return [
    m[0], m[1], m[2], m[3],
    "-i", path.resolve(NARRATION),
    "-filter_complex", `[1:a]${m[5]},volume=0.45[m];[2:a]aresample=44100,volume=1.0[v];[m][v]amix=inputs=2:normalize=0:duration=first[a]`,
    "-map", "0:v", "-map", "[a]",
  ];
}

function music(total) {
  // 잔잔한 패드: 화음(Am-F-C-G)을 7초마다 바꾸고 잔향을 더한다.
  const chords = [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392], [196, 246.94, 293.66]];
  const seg = 7;
  const voice = (k) => chords.map((c, i) => `between(mod(t,${seg * 4}),${i * seg},${(i + 1) * seg})*${c[k]}`).join("+");
  const env = `(0.55+0.45*sin(2*PI*t/${seg}-PI/2))`;
  const expr = [0, 1, 2].map((k) => `0.045*sin(2*PI*(${voice(k)})*t)`).join("+");
  return [
    "-f", "lavfi", "-i", `aevalsrc='(${expr})*${env}':s=44100:d=${total}`,
    "-af", `aecho=0.8:0.7:120|260:0.35|0.25,lowpass=f=2400,afade=t=in:d=2,afade=t=out:st=${total - 3}:d=3,volume=1.6`,
  ];
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(path.join(__dirname, "scene.html")).href);
  await page.addStyleTag({ content: fontCss });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([400, 500, 600, 700, 800].map((w) => document.fonts.load(`${w} 40px Pretendard`, "대구"))));
  if (tl) await page.evaluate((x) => window.applyTimeline(x), tl);

  if (args.still) {
    for (const s of args.still.split(",")) {
      await page.evaluate((t) => window.renderAt(t), Number(s));
      await page.screenshot({ path: path.join(path.dirname(OUT), `still_${s}.png`) });
    }
    await browser.close();
    return;
  }

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const ff = spawn("ffmpeg", [
    "-y", "-loglevel", "error",
    "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
    ...audio(TOTAL),
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT,
  ], { stdio: ["pipe", "inherit", "inherit"] });

  const frames = TOTAL * FPS;
  for (let i = 0; i < frames; i++) {
    await page.evaluate((t) => window.renderAt(t), i / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (i % (FPS * 5) === 0) process.stdout.write(`\r${Math.round((i / frames) * 100)}%`);
  }
  ff.stdin.end();
  await new Promise((r, j) => ff.on("close", (c) => (c === 0 ? r() : j(new Error("ffmpeg 실패")))));
  await browser.close();
  console.log(`\n완료: ${OUT}`);
})();
