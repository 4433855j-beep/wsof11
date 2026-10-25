# Claude 환경 점검표 — 계정 등록 항목과 PC별 설치 항목

- 작성일: 2026-10-25
- 계정: claude.ai 개인 계정
- 근거: Claude Code 클라우드 세션(노트북이 아닌 별도 컴퓨터)에서 별도 설치 없이 자동으로 나타난 항목을 「계정 등록」으로 판정함
- 노트북에만 있는 항목은 이 문서로 알 수 없으므로 노트북에서 `tools/claude-setup-check.ps1`을 실행해 확인한다(아래 3장)

## 1. 계정에 등록된 것 — 다른 PC에서 로그인만 하면 사용 가능 ✅

### 1-1. 스킬 (claude.ai 업로드, 34개)

| 분야 | 스킬 |
|---|---|
| 공문서·보고서(한글) | gongmunseo, hwpx, hwpx-new, korean-report-hwpx, daegu-report-hwpx, ministry-minister-report, safety-accident-report, handocsmith, kordoc |
| 법률 | korean-law, meka-gwak |
| 발표자료 | pptx, pptxgenjs, ppt-master, academic-pptx, daegu-policy-ppt, daegu-design-system-deck |
| 문서·데이터 | docx, docs, pdf, xlsx, excelize-xlsx, google-workspace |
| 조사·기타 | deep-research, morning, import-memory, skill-creator, brand-guidelines, canvas-design, design-taste-frontend, seedance-clean, built-in-browser, chrome-browser, computer-use |

### 1-2. MCP 커넥터 (claude.ai 설정 → 커넥터)

| 분야 | 커넥터 | 새 PC에서 |
|---|---|---|
| 법령·통계 | korealaw(국가법령정보), korea-law-alio(법령·공공기관 규정), korea-state(KOSIS 통계) | 바로 사용 |
| Google | Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, Google Slides, BigQuery | 첫 사용 때 재로그인 요청 가능 |
| 문서·디자인 | Notion, Canva, Figma, Gamma, Fonts, Claude Docs | 첫 사용 때 재로그인 요청 가능 |
| 기타 | PlayMCP(카카오맵·카카오톡·YouTube), Expedia, Melon, Norton, Pollo, Gemini | 첫 사용 때 재로그인 요청 가능 |

### 1-3. 플러그인 (claude.ai에서 추가, 11개)

pdf-viewer, operations, design, legal, engineering, figma, cowork-plugin-management, finance, product-management, data, marketing

> 참고: 이 클라우드 세션에서는 Slack·Asana·Box 등 일부 플러그인 MCP가 연결 실패로 표시되었다. 이는 클라우드 환경의 네트워크 정책(프록시 차단) 때문이며 계정 등록 여부와는 무관하다.

## 2. 저장소(GitHub)로 옮겨 다니는 것 — 저장소만 받으면 사용 가능 🔁

| 항목 | 위치 | 새 PC에서 할 일 |
|---|---|---|
| lawfirm 플러그인 v0.8.2 (스킬 14개) | `4433855j-beep/wsof11` 저장소 `plugins/lawfirm` | 저장소를 받아 Claude Code로 열고 신뢰 확인 1회. 또는 `/plugin marketplace add 4433855j-beep/wsof11@claude/hopeful-maxwell-cx39bq` → `/plugin install lawfirm@wsof11` |

## 3. PC마다 다시 해야 하는 것 — 점검 필요 ☐

| 확인 | 항목 | 확인 방법 | 새 PC에서 할 일 |
|---|---|---|---|
| ☐ | `%USERPROFILE%\.claude\skills`에 직접 푼 스킬 중 1장에 없는 것 | 점검 스크립트 | claude.ai에 zip 업로드(권장) 또는 폴더 복사 |
| ☐ | `claude mcp add`·데스크톱 앱 설정 파일로 등록한 MCP | 점검 스크립트 | 다시 등록 또는 claude.ai 커넥터로 전환 |
| ☐ | `/plugin install`로 직접 설치한 플러그인 중 1·2장에 없는 것 | 점검 스크립트 | `/plugin marketplace add` → `/plugin install` |
| ☐ | Python 패키지 (python-docx, kiwipiepy, kiwipiepy_model, pypdf) | 점검 스크립트 | `python -m pip install --use-pep517 <패키지>` |
| ☐ | 법제처 Open API 키(OC), 빅케이스 계정 | 점검 스크립트 | `/lawfirm:law-key-setup`, `/lawfirm:case-search-setup` |

### 노트북 점검 스크립트 실행 방법

1. 이 저장소의 `tools/claude-setup-check.ps1`을 노트북에 내려받는다.
2. PowerShell에서 실행한다.
   ```
   powershell -ExecutionPolicy Bypass -File .\claude-setup-check.ps1
   ```
3. 바탕화면에 `Claude_점검표_<컴퓨터이름>.md`가 생긴다. ☐ 표시가 다른 PC에서 다시 해야 할 항목이다.

스크립트는 읽기만 하며 아무것도 설치·삭제·변경하지 않는다. API 키 파일은 내용을 읽지 않고 있는지만 확인한다.
