"""장면별 한국어 내레이션을 오프라인 음성합성(Supertonic 3, sherpa-onnx)으로 만들고
장면 시작 시각에 맞춰 하나의 음성 트랙(narration.wav)으로 합친다.

    pip install sherpa-onnx soundfile numpy
    # 모델(MIT): https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-supertonic-3-tts-int8-2026-05-11.tar.bz2
    python narrate.py --model-dir sherpa-onnx-supertonic-3-tts-int8-2026-05-11 --out narration.wav
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
import sherpa_onnx
import soundfile as sf

# (장면 최소 길이 초, 내레이션) — scene.html 의 장면·자막(class="cap") 순서와 같다.
# 장면 길이는 내레이션 길이에 맞춰 늘어나며 timeline.json 으로 저장해 render.js 가 쓴다.
LINES = [
    (5, "대구 어르신, 도시철도 무료는 몇 세부터일까요?"),
    (6, "대구시는 2023년 7월, 광역자치단체 최초로 75세 이상 시내버스 무임을 시작했습니다."),
    (9, "도시철도는 65세에서 매년 한 살씩 올리고, 버스는 75세에서 한 살씩 낮춰, 2028년에는 70세로 맞추는 구조입니다."),
    (7, "2026년에는 68세부터 도시철도가, 72세부터는 시내버스까지 무료입니다."),
    (7, "대구정책연구원 분석 결과, 비용 대비 편익은 1.53, 이용자 만족도는 98.5%였습니다."),
    (6, "다만 도시철도 무임 손실은 최근 5년간 약 2,600억 원으로, 재정 부담이 과제입니다."),
    (9, "도시철도 65세 환원은 2027년 7월 시행이 검토되고 있지만, 조례 개정 전으로 아직 확정되지 않았습니다."),
    (6, "정확한 기준은 대구시와 대구교통공사의 공식 안내로 확인하세요."),
]

# 음성합성이 정확히 읽도록 바꿔 읽기(화면 자막은 숫자 그대로 유지)
READINGS = [
    ("1.53", "일 점 오삼"), ("98.5%", "구십팔 점 오 퍼센트"),
    ("2023년", "이천이십삼 년"), ("2026년", "이천이십육 년"), ("2027년", "이천이십칠 년"),
]

LEAD_IN = 0.5  # 장면 전환 후 말 시작까지 여유(초)
TAIL = 1.0  # 말이 끝난 뒤 다음 장면까지 여유(초)


def to_speech_text(text: str) -> str:
    for src, dst in READINGS:
        text = text.replace(src, dst)
    return text


def build_tts(md: str) -> sherpa_onnx.OfflineTts:
    f = lambda name: os.path.join(md, name)  # noqa: E731
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            supertonic=sherpa_onnx.OfflineTtsSupertonicModelConfig(
                duration_predictor=f("duration_predictor.int8.onnx"),
                text_encoder=f("text_encoder.int8.onnx"),
                vector_estimator=f("vector_estimator.int8.onnx"),
                vocoder=f("vocoder.int8.onnx"),
                tts_json=f("tts.json"),
                unicode_indexer=f("unicode_indexer.bin"),
                voice_style=f("voice.bin"),
            ),
            num_threads=4,
        ),
    )
    return sherpa_onnx.OfflineTts(cfg)


def synth(tts, text: str, sid: int, speed: float) -> tuple[np.ndarray, int]:
    g = sherpa_onnx.GenerationConfig()
    g.sid, g.speed, g.num_steps, g.extra = sid, speed, 10, {"lang": "ko"}
    audio = tts.generate(to_speech_text(text), g)
    return np.asarray(audio.samples, dtype=np.float32), audio.sample_rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--out", default="narration.wav")
    ap.add_argument("--timeline", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "timeline.json"))
    ap.add_argument("--sid", type=int, default=0, help="목소리 번호: 0~4 여성, 5~9 남성 (기본 0: 차분한 여성)")
    ap.add_argument("--speed", type=float, default=1.05, help="어르신 대상이므로 1.0~1.1 권장")
    args = ap.parse_args()

    tts = build_tts(args.model_dir)
    clips, scenes, t = [], [], 0.0
    for min_dur, line in LINES:
        samples, sr = synth(tts, line, args.sid, args.speed)
        dur = round(max(min_dur, LEAD_IN + len(samples) / sr + TAIL), 1)
        scenes.append([round(t, 1), round(t + dur, 1)])
        clips.append((t + LEAD_IN, samples))
        print(f"{t:5.1f}s ~ {t + dur:5.1f}s  음성 {len(samples) / sr:4.1f}초  {line}")
        t += dur
    total = round(t, 1)
    track = np.zeros(int(total * sr) + 1, dtype=np.float32)
    for begin, samples in clips:
        b = int(begin * sr)
        track[b:b + len(samples)] += samples[: len(track) - b]
    peak = float(np.max(np.abs(track))) or 1.0
    sf.write(args.out, track * (0.9 / peak), sr)
    with open(args.timeline, "w", encoding="utf-8") as f:
        json.dump({"total": total, "scenes": scenes, "captions": [l for _, l in LINES]}, f, ensure_ascii=False, indent=1)
    print(f"완료: {args.out} (총 {total}초), {args.timeline}")


if __name__ == "__main__":
    main()
