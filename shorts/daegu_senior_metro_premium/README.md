# 쇼츠(프리미엄 모션그래픽): 대구 어르신 도시철도 무임승차

- 9:16(1080x1920), 55초, 30fps · 네이비/골드 톤 모션그래픽 + 자막 + 잔잔한 배경음악(내레이션 없음)
- 장면: 도입 → 2023.7 시작 → 연령 조정 그래프(도시철도↑·버스↓, 2028 통합) → 2026 현재(68세·72세) → 성과(B/C 1.53, 만족 98.5%, 버스 이용률) → 과제(무임손실 약 2,600억) → 향후(2026.5 공약·2027.7 검토·2028.1 버스 70세, 미확정) → 마무리

| 파일 | 내용 |
|---|---|
| `daegu_senior_metro_premium.mp4` | 완성 영상 |
| `scene.html` | 장면·문구·애니메이션 (브라우저로 열어 확인 가능) |
| `render.js` | 프레임 캡처 → mp4 렌더러 (Playwright + ffmpeg) |

## 문구를 고쳐 다시 만들기

1. `scene.html`에서 문구·수치를 수정 (자막은 아래쪽 `class="cap"` 부분)
2. 렌더링 (Node.js, Playwright, ffmpeg 필요 / 글꼴: [Pretendard](https://github.com/orioncactus/pretendard) OTF, OFL 라이선스)

```bash
node render.js --font-dir Pretendard폴더/public/static
```

장면 미리보기 이미지: `node render.js --font-dir ... --still 4,17,25` (지정한 초의 화면을 PNG로 저장)

## 목소리 입히기
`../daegu_senior_metro/script.txt` 대본을 MoneyPrinterTurbo(음성 `ko-KR-SunHiNeural-Female`)로 음성만 만들어 영상에 합치거나, 편집 앱(CapCut 등)에서 내레이션을 녹음해 얹으세요. 장면 시간은 `../daegu_senior_metro/subtitles.srt`와 같습니다.

## 근거 (게시 전 재확인)
「대구광역시 어르신 무임교통 지원에 관한 조례」, 「노인복지법」 제26조, 대구정책연구원 분석(2026.6. 보도), 대구MBC·TBC·경향신문 보도.
65세 환원은 조례 개정 전으로 **확정되지 않은 사항**입니다.
