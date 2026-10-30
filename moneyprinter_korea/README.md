# MoneyPrinterTurbo 한국 소재 애드온

MoneyPrinterTurbo(이하 MPT)에서 **한국 정경·도시·전통·정책 관련 사진·영상과 한국어 음성**을 쓰기 위한 설정 모음입니다.
설치된 MPT 코드는 고치지 않습니다. MPT가 원래 지원하는 **로컬 소재(local)**, **Pexels/Pixabay**, **한국어 음성** 기능을 활용합니다.

## 1. 한눈에 보기

| 필요 항목 | 해결 방법 | 키 발급처 | 비용 |
|---|---|---|---|
| 한국 정경·도시·관광지 **사진** | 한국관광공사 관광사진 API → 이 애드온으로 내려받기 → MPT `local` 소재 | 공공데이터포털 「한국관광공사_관광사진 정보」 | 무료(개발계정 트래픽 1,000건 수준, 운영계정 신청 시 증량) |
| 한국 **동영상** | MPT 기본 Pexels/Pixabay + 영문 한국 검색어(`Seoul city` 등) | pexels.com/api, pixabay.com/api/docs | 무료 |
| **부드러운 한국어 목소리** | MPT 기본 음성 `ko-KR-SunHiNeural`(여), `ko-KR-InJoonNeural`(남), `ko-KR-HyunsuMultilingualNeural`(남) | 키 필요 없음(Edge TTS) | 무료 |
| **정책 사진** | 공개 API 없음 → 기관 보유 사진·정책브리핑 공공누리 표시 사진을 직접 받아 `local` 폴더에 넣기 | — | — |

## 2. 한국관광공사 관광사진 API 등록

1. [공공데이터포털](https://www.data.go.kr) 로그인 → 「**한국관광공사_관광사진 정보**」 검색 → **활용신청**(자동 승인).
2. 마이페이지 → 개발계정에서 **일반 인증키(Decoding)** 를 복사합니다. (Encoding 키를 넣어도 자동 변환됩니다.)
3. MPT 폴더의 `config.toml` 의 `[app]` 아래, `pixabay_api_keys` 줄 밑에 추가합니다.

```toml
# 한국관광공사 관광사진 정보 (공공데이터포털)
kto_photo_api_keys = ["여기에_인증키"]
```

> 활용신청 직후 1시간가량은 `SERVICE KEY IS NOT REGISTERED` 오류가 날 수 있습니다(공공데이터포털 키 동기화 시간).

## 3. 한국 사진 내려받기 → MPT에서 사용

이 저장소(wsof11) 폴더에서 실행합니다(Python 3.10 이상, 추가 설치 없음).

```bash
python -m moneyprinter_korea 서울 야경 한옥마을 제주 경복궁 --count 15 --out 내려받을_폴더 --config MPT폴더/config.toml
```

- 검색어별 사진이 저장되고, **`credits.csv`(제목·촬영자·촬영지·출처)** 가 함께 만들어집니다.
- MPT WebUI → 영상 소재 출처 **「로컬 파일(local)」** 선택 → 내려받은 사진을 업로드하면, MPT가 사진을 천천히 확대되는 영상 클립으로 바꿉니다.

## 4. 한국 동영상 (Pexels / Pixabay)

`config.toml` 에 키를 넣고(`pexels_api_keys`, `pixabay_api_keys`), WebUI의 **영상 키워드**를 영문 한국 지명으로 입력하면 한국 영상 비율이 크게 올라갑니다.

| 주제 | 추천 영상 키워드 |
|---|---|
| 정경·자연 | `Korea landscape`, `Korean countryside`, `Jeju island`, `Korea mountains` |
| 도시·야경 | `Seoul city`, `Seoul skyline night`, `Han river night`, `Busan city` |
| 전통 | `Gyeongbokgung palace`, `Bukchon hanok village`, `Korean hanok` |
| 정책·행정 | `Seoul city hall`, `Korea government`, `Korean office workers` |
| 복지·교통 | `Korean elderly`, `Seoul subway`, `Korea KTX train` |

애드온 CLI를 실행하면 검색어별 추천 영문 키워드도 함께 출력됩니다(`keywords.py`에서 수정 가능).

## 5. 부드러운 한국어 목소리

MPT WebUI → 음성 설정에서 선택합니다.

| 음성 | 느낌 | 비고 |
|---|---|---|
| `ko-KR-SunHiNeural-Female` | 차분하고 부드러운 여성 (추천) | 무료 |
| `ko-KR-InJoonNeural-Male` | 안정적인 남성 | 무료 |
| `ko-KR-HyunsuMultilingualNeural-Male` | 자연스러운 남성 | 무료 |

- 더 부드럽게: **음성 속도 0.9~0.95**로 낮추면 공공 안내 영상에 어울립니다.
- 자막 글꼴은 한글 글꼴(예: `NanumGothic`, `Noto Sans KR`)을 MPT `resource/fonts`에 넣고 선택하세요.

## 6. 배경 프리셋: 대구 도시철도 (`daegu-metro`)

```bash
python -m moneyprinter_korea --preset daegu-metro --count 15 --out 대구도시철도_소재 --config MPT폴더/config.toml
```

- 사진 검색어: 대구 모노레일, 하늘열차, 대구 도시철도, 대구 지하철, 동대구역, 대구 3호선, 수성못, 대구 야경
- 실행이 끝나면 MPT **영상 키워드**에 붙여넣을 영문 키워드(`Daegu monorail, Daegu subway, ...`)가 출력됩니다.
- MPT 설정: 영상 비율 **9:16(쇼츠)**, 소재 출처 **로컬 파일**(내려받은 사진) → 부족하면 Pexels/Pixabay로 보충.

| 노선 | 구간(종점) | 배경으로 쓸 장면 |
|---|---|---|
| 1호선 | 설화명곡 ↔ 하양 (2024.12. 안심~하양 8.89km 연장 개통) | 지하 승강장, 하양 연장 신설역 |
| 2호선 | 문양 ↔ 영남대 | 반월당 환승역, 지하 대합실 |
| 3호선(하늘열차) | 칠곡경대병원 ↔ 용지, 국내 첫 모노레일(2015.4. 개통) | 고가 모노레일·도심 전경 — 대구다움이 가장 잘 드러남 |

> **주의(공공 홍보물):** Pexels/Pixabay의 `Korea subway train`, `monorail city` 영상은 **대구가 아닐 수 있습니다.**
> 대구시 공식 영상이라면 관광사진(대구 촬영분), 대구교통공사 홍보자료(사용 승인 후), **직접 촬영 영상**을 우선 쓰세요.
> 역사·열차 내부 촬영은 대구교통공사 사전 협의가 필요할 수 있고, 승객 얼굴이 식별되면 모자이크 처리하세요(「개인정보 보호법」).

## 7. 저작권·이용 조건 (반드시 확인)

| 자료 | 이용 조건 | 주의 |
|---|---|---|
| 한국관광공사 관광사진 | 공공누리 **제1유형(출처표시)** 또는 **제3유형(출처표시+변경금지)** 혼재 | 영상 끝 또는 설명란에 `credits.csv` 출처 표시. 제3유형은 확대·자르기·자막 합성이 '변경'에 해당할 수 있으므로 원본 페이지에서 유형 확인 후 제1유형 위주 사용. 인물 명예훼손·기업 CI/BI 사용 금지 |
| 정책브리핑(korea.kr) 사진 | 정부기관·연합뉴스 등 **저작권이 각각 다름** | 공공누리 표시가 있는 사진만 사용, 표시 없으면 담당 부서와 사전 협의 |
| Pexels / Pixabay | 각 사이트 라이선스(상업 이용 가능, 출처 표시 권장) | 인물·상표가 나오는 영상은 공공 홍보용 사용 시 추가 검토 |

공공누리 근거: 「공공데이터의 제공 및 이용 활성화에 관한 법률」 및 「저작권법」 제24조의2(공공저작물의 자유이용), 문화체육관광부 「공공누리」 유형 기준.
