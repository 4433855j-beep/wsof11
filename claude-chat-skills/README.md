# Claude 채팅창(claude.ai)용 스킬 업로드 파일

| 파일 | 스킬 | 용도 |
|---|---|---|
| `kordoc.zip` | kordoc | HWP·HWPX·HML·PDF·DOCX·XLSX 읽기, 서식 채우기, 패치, 비교, 검증, 렌더 |
| `gongmunseo.zip` | gongmunseo | 내용 → 행정 공문서(기안문·보고서·계획서·통지·회의록) HWPX 생성 |

## 등록 방법 (zip 하나당 1회)

1. 이 폴더의 zip을 PC로 내려받는다(GitHub에서 파일 → Download raw file).
2. claude.ai → **설정(Settings) → 기능(Capabilities)** 에서 **코드 실행 및 파일 생성(Code execution)** 을 켠다.
3. 같은 화면 **스킬(Skills) → 스킬 업로드(Upload skill)** 에서 zip을 올리고 토글을 켠다.

## 주의

- 두 스킬 모두 `npx -y kordoc@4.22.16` (npm 패키지)를 실행한다. 채팅창 코드 실행 환경의
  네트워크 설정에서 npm 레지스트리(registry.npmjs.org) 접근이 허용돼야 작동한다.
- 원본: https://github.com/chrisryugj/kordoc (MIT License)
