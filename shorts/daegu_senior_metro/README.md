# 쇼츠: 대구 어르신 도시철도 무임승차 (2026.10. 기준)

| 파일 | 내용 |
|---|---|
| `daegu_senior_metro_shorts.mp4` | 9:16(1080x1920), 55초, 그래픽 + 자막 + 잔잔한 배경음 (내레이션 없음) |
| `script.txt` | 내레이션 대본 8문장 (MoneyPrinterTurbo '영상 문안'에 붙여넣기) |
| `subtitles.srt` | 장면별 자막 |
| `render.py` | 영상 재생성 스크립트 (문구·수치를 고친 뒤 다시 실행) |

## 목소리 입히기 (MoneyPrinterTurbo)

1. 영상 문안: `script.txt` 내용 붙여넣기
2. 음성: `ko-KR-SunHiNeural-Female`, 속도 0.95
3. 영상 비율 9:16, 소재: 로컬 파일(대구 도시철도 사진) 또는 영상 키워드 `Daegu monorail, Daegu subway, Daegu city`
   - 사진 내려받기: `python -m moneyprinter_korea --preset daegu-metro`

## 다시 렌더링

```bash
pip install pillow fonttools
python render.py --font-regular C:\Windows\Fonts\malgun.ttf --font-bold C:\Windows\Fonts\malgunbd.ttf
```

## 내용 근거 (게시 전 재확인)

- 「대구광역시 어르신 무임교통 지원에 관한 조례」(2024.10.30. 개정) — 연도별 연령표는 부칙 원문 대조 필요
- 「노인복지법」 제26조(경로우대)
- 성과(B/C 1.53, 버스 이용률 9.67%→17.59%, 만족 98.5%): 대구정책연구원 분석(2026.6. 보도)
- 무임손실 5년 약 2,600억 원: 대구MBC 보도
- 65세 환원 2027.7. 검토: 시장직 인수위 관련 보도(2026.6.) — **조례 개정 전, 확정 아님**

배경은 실제 대구 도시철도 사진이 아닌 일러스트 그래픽입니다.
