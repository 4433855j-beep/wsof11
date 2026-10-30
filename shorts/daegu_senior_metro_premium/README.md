# 쇼츠(프리미엄 모션그래픽 + 한국어 내레이션): 대구 어르신 도시철도 무임승차

- 9:16(1080x1920), 약 74초, 30fps · 네이비/골드 톤 모션그래픽
- **한국어 자막**(Pretendard) + **한국어 여성 내레이션**(Supertonic 3, 오프라인 합성) + 잔잔한 배경음악
- 장면: 도입 → 2023.7 시작 → 연령 조정 그래프(도시철도↑·버스↓, 2028 통합) → 2026 현재(68세·72세) → 성과(B/C 1.53, 만족 98.5%, 버스 이용률) → 과제(무임손실 약 2,600억) → 향후(2026.5 공약·2027.7 검토·2028.1 버스 70세, 미확정) → 마무리

| 파일 | 내용 |
|---|---|
| `daegu_senior_metro_premium.mp4` | 완성 영상 (자막 + 내레이션) |
| `narration.wav` | 한국어 내레이션 음성 |
| `subtitles.srt`, `script.txt` | 자막 파일(시각 포함), 내레이션 대본 |
| `timeline.json` | 내레이션 길이에 맞춘 장면 시각 (narrate.py 가 생성) |
| `scene.html` | 장면·문구·애니메이션 |
| `narrate.py` | 한국어 음성 합성 (sherpa-onnx + Supertonic 3) |
| `render.js` | 프레임 캡처 → mp4 (Playwright + ffmpeg) |

## 문구를 고쳐 다시 만들기

1. 문구 수정: `narrate.py` 의 `LINES`(내레이션=자막)와 `scene.html` 의 화면 문구
2. 음성 합성 → 장면 시각(timeline.json) 자동 계산

```bash
pip install sherpa-onnx soundfile numpy
python narrate.py --model-dir sherpa-onnx-supertonic-3-tts-int8-2026-05-11 --out narration.wav
```

모델(MIT 라이선스): `https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/sherpa-onnx-supertonic-3-tts-int8-2026-05-11.tar.bz2`
목소리: `--sid 0`(차분한 여성, 기본) · 0~4 여성, 5~9 남성 / 속도 `--speed 1.05`(어르신 대상 1.0~1.1 권장)

3. 영상 렌더링 (Node.js, Playwright, ffmpeg / 글꼴 [Pretendard](https://github.com/orioncactus/pretendard) OFL)

```bash
node render.js --font-dir Pretendard폴더/public/static --narration narration.wav
```

## 검수 방법
내레이션은 한국어 음성인식 모델(sherpa-onnx zipformer-korean)로 다시 받아써서 숫자·핵심어(2023년 7월, 75세, 68세·72세, 1.53, 98.5%, 2,600억, 2027년 7월)가 맞게 읽히는지 확인했습니다. 게시 전 사람이 한 번 더 들어 확인하세요.

## 근거 (게시 전 재확인)
「대구광역시 어르신 무임교통 지원에 관한 조례」, 「노인복지법」 제26조, 대구정책연구원 분석(2026.6. 보도), 대구MBC·TBC·경향신문 보도.
65세 환원은 조례 개정 전으로 **확정되지 않은 사항**입니다.
