"""대구 어르신 도시철도 무임승차 쇼츠(9:16, 1080x1920) 렌더러.

그래픽(도시 야경 + 고가 모노레일)과 정보 카드·자막으로 구성한 무음성 버전을 만든다.
내레이션은 같은 폴더의 script.txt 를 MoneyPrinterTurbo 에 넣어 입힌다.

    python render.py --font-regular 나눔고딕.ttf --font-bold 나눔고딕Bold.ttf
"""

from __future__ import annotations

import argparse
import math
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))

NAVY = (16, 28, 58)
ACCENT = (0, 122, 255)
RED = (214, 48, 49)
GREEN = (24, 150, 92)
GRAY = (90, 98, 112)

# (초, 제목, 본문 줄 목록, 자막=내레이션)
SCENES = [
    (5, "대구 어르신\n도시철도 무임승차", ["몇 세부터 무료일까요?", "", "2026년 기준 총정리"],
     "대구 어르신, 도시철도 무료는 몇 세부터일까요?"),
    (6, "2023년 7월 시작", ["시내버스 75세 이상 무임", "전국 광역자치단체 최초", "", "도시철도는 당시 65세 유지"],
     "대구시는 2023년 7월, 광역자치단체 최초로 75세 이상 시내버스 무임을 시작했습니다."),
    (9, "연령 단계적 조정", "TABLE",
     "도시철도는 65세에서 매년 한 살씩 올리고, 버스는 75세에서 한 살씩 낮춰 2028년 70세로 맞추는 구조입니다."),
    (7, "2026년 지금은?", ["68세 이상", "도시철도·광역철도 무료", "", "72세 이상", "시내버스까지 모두 무료"],
     "2026년에는 68세부터 도시철도가, 72세부터는 시내버스까지 무료입니다."),
    (7, "성과", ["비용 대비 편익(B/C) 1.53", "어르신 버스 이용률 9.67%에서 17.59%로", "이용자 만족 98.5%", "", "자료: 대구정책연구원(2026.6.)"],
     "대구정책연구원 분석 결과 비용 대비 편익은 1.53, 이용자 만족도는 98.5%였습니다."),
    (6, "과제", ["도시철도 무임 손실", "최근 5년 약 2,600억 원", "연평균 500억 원 이상", "", "재정 부담 대책 필요"],
     "다만 도시철도 무임 손실은 최근 5년간 약 2,600억 원으로, 재정 부담이 과제입니다."),
    (9, "향후 방향", ["도시철도 65세 환원 (시장 공약)", "2027년 7월 시행 검토 (보도)", "시내버스 70세: 2028년 1월", "", "조례 개정 전 · 미확정"],
     "도시철도 65세 환원은 2027년 7월 시행이 검토되고 있지만, 조례 개정 전으로 아직 확정되지 않았습니다."),
    (6, "꼭 확인하세요", ["대구시 · 대구교통공사", "공식 안내 기준", "", "근거: 대구광역시 어르신 무임교통", "지원에 관한 조례, 노인복지법 제26조"],
     "정확한 기준은 대구시와 대구교통공사의 공식 안내로 확인하세요."),
]

YEARS = ["2023", "2024", "2025", "2026", "2027", "2028"]
METRO = ["65", "66", "67", "68", "69", "70"]
BUS = ["75", "74", "73", "72", "71", "70"]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def gradient(top, bottom) -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def skyline(seed: int, base_y: int, color, max_h: int, width: int) -> Image.Image:
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (width, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = 0
    while x < width:
        bw, bh = rnd.randint(60, 150), rnd.randint(max_h // 3, max_h)
        d.rectangle([x, base_y - bh, x + bw, base_y], fill=color)
        for wy in range(base_y - bh + 20, base_y - 20, 36):
            for wx in range(x + 12, x + bw - 16, 28):
                if rnd.random() < 0.35:
                    d.rectangle([wx, wy, wx + 10, wy + 14], fill=(255, 214, 120, 200))
        x += bw + rnd.randint(4, 20)
    return layer


def train(length: int) -> Image.Image:
    car_w, gap, h = 250, 14, 92
    img = Image.new("RGBA", (length, h + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(3):
        x = i * (car_w + gap)
        d.rounded_rectangle([x, 0, x + car_w, h], radius=34, fill=(240, 244, 250))
        d.rectangle([x + 10, h - 26, x + car_w - 10, h - 16], fill=ACCENT)
        for wx in range(x + 28, x + car_w - 40, 52):
            d.rounded_rectangle([wx, 18, wx + 38, 50], radius=8, fill=(40, 60, 100))
    return img


def wrap_lines(draw, text, fnt, max_w):
    # 어절(띄어쓰기) 단위로 줄바꿈해 '2,6/00억'처럼 단어가 잘리지 않게 한다.
    out = []
    for raw in text.split("\n"):
        line = ""
        for word in raw.split(" "):
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=fnt) > max_w and line:
                out.append(line)
                line = word
            else:
                line = trial
        out.append(line)
    return out


CARD_TOP = 330


def card(scene, fonts) -> tuple[Image.Image, int]:
    """카드 레이어와 카드 아래쪽 y 좌표를 돌려준다(높이는 내용에 맞춤)."""
    content = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bottom = _card_content(ImageDraw.Draw(content), scene, fonts) + 60
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0, x1 = 70, CARD_TOP, W - 70
    d.rounded_rectangle([x0, y0, x1, bottom], radius=48, fill=(255, 255, 255, 238))
    d.rounded_rectangle([x0, y0, x1, y0 + 16], radius=8, fill=ACCENT)
    img.alpha_composite(content)
    return img, bottom


def _card_content(d, scene, fonts) -> int:
    _, title, body, _ = scene
    y = CARD_TOP + 70
    for line in title.split("\n"):
        d.text((W // 2, y), line, font=fonts["title"], fill=NAVY, anchor="mt")
        y += 104
    y += 40
    if body == "TABLE":
        return draw_table(d, y, fonts)
    for line in body:
        if not line:
            y += 40
            continue
        big = line.endswith("이상") or line.startswith("최근") or line.startswith("비용")
        f = fonts["big"] if big else fonts["body"]
        color = RED if big else (GRAY if line.startswith(("자료", "근거", "지원에", "조례")) else NAVY)
        if line.startswith(("자료", "근거", "지원에")):
            f = fonts["small"]
        d.text((W // 2, y), line, font=f, fill=color, anchor="mt")
        y += f.size + 30
    return y - 30


def draw_table(d, y, fonts):
    left, col = 100, 112
    label_w = 250
    for i, yr in enumerate(YEARS):
        cx = left + label_w + i * col + col // 2 - 60
        if yr == "2026":
            d.rounded_rectangle([cx - 58, y - 10, cx + 58, y + 330], radius=20, fill=(255, 236, 200))
        d.text((cx, y), yr, font=fonts["small"], fill=GRAY, anchor="mt")
    rows = [("도시철도", METRO, ACCENT), ("시내버스", BUS, GREEN)]
    for r, (name, vals, color) in enumerate(rows):
        ry = y + 90 + r * 120
        d.text((left, ry + 8), name, font=fonts["body"], fill=color, anchor="lt")
        for i, v in enumerate(vals):
            cx = left + label_w + i * col + col // 2 - 60
            d.text((cx, ry), v, font=fonts["big"], fill=NAVY if YEARS[i] != "2026" else RED, anchor="mt")
    d.text((W // 2, y + 380), "단위: 세 이상 · 2027~2028년은 당초 계획", font=fonts["small"], fill=GRAY, anchor="mt")
    d.text((W // 2, y + 440), "2028년 70세 통합 (당초 계획)", font=fonts["body"], fill=RED, anchor="mt")
    return y + 440 + fonts["body"].size


def caption(text, fonts, top: int) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = wrap_lines(d, text, fonts["cap"], W - 160)
    lh = fonts["cap"].size + 16
    d.rounded_rectangle([50, top - 24, W - 50, top + lh * len(lines) + 12], radius=28, fill=(0, 0, 0, 170))
    for i, line in enumerate(lines):
        d.text((W // 2, top + i * lh), line, font=fonts["cap"], fill=(255, 255, 255), anchor="mt")
    return img


def header(fonts) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([70, 150, 560, 240], radius=45, fill=(255, 255, 255, 40))
    d.text((315, 195), "대구 어르신 무임교통", font=fonts["body"], fill=(255, 255, 255), anchor="mm")
    d.text((W - 70, 195), "2026.10. 기준", font=fonts["small"], fill=(220, 228, 240), anchor="rm")
    return img


def check_glyphs(path: str, texts: list[str]):
    from fontTools.ttLib import TTFont

    cmap = TTFont(path).getBestCmap()
    missing = {ch for t in texts for ch in t if not ch.isspace() and ord(ch) not in cmap}
    if missing:
        raise SystemExit(f"글꼴에 없는 문자: {''.join(sorted(missing))} ({path})")


def scene_texts():
    for _, title, body, cap in SCENES:
        yield title
        yield cap
        if body != "TABLE":
            yield from body
    yield from YEARS + METRO + BUS
    yield "도시철도시내버스단위: 세 이상 · 2027~2028년은 당초 계획2028년 70세 통합 (당초 계획)대구 어르신 무임교통2026.10. 기준"


def write_texts(out_dir: str):
    """내레이션 대본(script.txt)과 자막(subtitles.srt)을 장면 길이에 맞춰 저장한다."""
    def ts(sec):
        return f"00:00:{sec:02d},000" if sec < 60 else f"00:{sec // 60:02d}:{sec % 60:02d},000"

    start, srt = 0, []
    for i, (dur, _t, _b, cap) in enumerate(SCENES, 1):
        srt.append(f"{i}\n{ts(start)} --> {ts(start + dur)}\n{cap}\n")
        start += dur
    with open(os.path.join(out_dir, "subtitles.srt"), "w", encoding="utf-8") as f:
        f.write("\n".join(srt))
    with open(os.path.join(out_dir, "script.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(s[3] for s in SCENES) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font-regular", required=True)
    ap.add_argument("--font-bold", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "daegu_senior_metro_shorts.mp4"))
    args = ap.parse_args()

    for p in (args.font_regular, args.font_bold):
        try:
            check_glyphs(p, list(scene_texts()))
        except ImportError:
            pass
    fonts = {
        "title": font(args.font_bold, 88),
        "big": font(args.font_bold, 66),
        "body": font(args.font_bold, 46),
        "small": font(args.font_regular, 36),
        "cap": font(args.font_bold, 48),
    }

    sky = gradient((22, 30, 72), (238, 140, 96))
    far = skyline(7, 1480, (52, 50, 92, 255), 520, W)
    near = skyline(11, 1560, (28, 26, 54, 255), 380, W)
    rail = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rail)
    rd.rectangle([0, 1600, W, 1630], fill=(190, 196, 210))
    for px in range(40, W, 220):
        rd.rectangle([px, 1630, px + 36, H], fill=(150, 156, 172))
    rd.rectangle([0, 1760, W, H], fill=(20, 20, 36))
    tr = train(3 * 264)
    hdr = header(fonts)
    cards, caps = [], []
    for s in SCENES:
        layer, bottom = card(s, fonts)
        cards.append(layer)
        caps.append(caption(s[3], fonts, bottom + 70))

    total = sum(s[0] for s in SCENES)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i",
        f"aevalsrc='0.05*sin(2*PI*130.8*t)*(0.6+0.4*sin(2*PI*0.25*t))"
        f"+0.035*sin(2*PI*196*t)+0.03*sin(2*PI*261.6*t)*(0.6+0.4*sin(2*PI*0.2*t))':s=44100:d={total}",
        "-af", f"afade=t=in:d=2,afade=t=out:st={total - 3}:d=3",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", args.out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    frame_no = 0
    for idx, (dur, *_rest) in enumerate(SCENES):
        n = dur * FPS
        for f in range(n):
            t = frame_no / FPS
            frame = sky.copy().convert("RGBA")
            for layer, speed in ((far, 12), (near, 30)):
                off = int(t * speed) % layer.width
                frame.alpha_composite(layer, (-off, 0))
                frame.alpha_composite(layer, (layer.width - off, 0))
            frame.alpha_composite(rail)
            tx = int((t * 260) % (W + tr.width)) - tr.width
            frame.alpha_composite(tr, (tx, 1600 - tr.height + 4))
            frame.alpha_composite(hdr)
            # 카드: 0.4초 페이드인 + 살짝 올라오기, 장면 끝 0.3초 페이드아웃
            fade = min(1.0, f / (0.4 * FPS), (n - f) / (0.3 * FPS))
            fade = max(0.0, fade)
            lift = int((1 - min(1.0, f / (0.4 * FPS))) * 40)
            for layer in (cards[idx], caps[idx]):
                lay = layer if fade >= 1 else Image.eval(layer, lambda v: v)
                if fade < 1:
                    a = lay.getchannel("A").point(lambda v, k=fade: int(v * k))
                    lay = lay.copy()
                    lay.putalpha(a)
                frame.alpha_composite(lay, (0, lift))
            proc.stdin.write(frame.convert("RGB").tobytes())
            frame_no += 1
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg 인코딩 실패")
    write_texts(os.path.dirname(os.path.abspath(args.out)))
    print(f"완료: {args.out} ({total}초)")


if __name__ == "__main__":
    main()
