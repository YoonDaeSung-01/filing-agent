# 08. 데이터 수집 — OpenDART · 파싱 · 캐싱 (★★)

> "데이터 엔지니어링 프로젝트 아닌가?"라는 압박 질문을 역으로 강점으로 만드는 영역.

---

## 8-1. OpenDART API

### 한 줄 정의
> 한국 금융감독원 전자공시(DART)의 공개 REST API. 무료 인증키로 기업 공시·재무 데이터를 받는다.

### 핵심 엔드포인트 (이 프로젝트가 쓴 것)
| 엔드포인트 | 용도 |
|---|---|
| `corpCode.xml` (zip) | 회사명 ↔ `corp_code`(8자리) 매핑 |
| `fnlttSinglAcnt.json` | 단일회사 **주요계정**(매출·이익·자산·부채) |
| `list.json` | 공시 목록(보고서 검색) |
| `document.xml` (zip) | 사업보고서 **원문**(서술 섹션 추출용) |

### ⚠️ DART의 함정 4가지 (전부 코드로 방어)
1. **corp_code ≠ 종목코드** — 8자리 고유번호를 `corpCode.xml`에서 먼저 매핑. **추측 금지**(CLAUDE.md).
2. **실패도 HTTP 200** — 본문 `status` 필드로 알림(`"000"` 정상, `"013"` 없음 등) → `status != "000"`면 예외.
3. **금액은 콤마 문자열** — `"300,870,903"` → 콤마 제거 후 `int`(원 단위 정수).
4. **연결(CFS) / 별도(OFS)** — 같은 회사도 두 재무제표가 있고 수치가 다름. 연결 우선, 없으면 별도 폴백.

### 이 프로젝트에서 실제 사용
- `ingest/dart_client.py` — 호출 + 캐싱 + corp_code 매핑(`corpCode.xml` zip 해제 → XML 파싱).
- `ingest/facts.py` — 순수 파싱 로직(`ensure_status_ok`, `_parse_amount`, CFS→OFS 폴백). 키·네트워크 불필요 → 픽스처 테스트.
- `ingest/filings.py` — `document.xml` zip에서 가장 큰 HTML 추출 → BeautifulSoup 텍스트화.

### 면접 Q&A
**Q. 외부 API의 비표준 동작을 어떻게 처리했나요?**
> DART는 실패도 HTTP 200으로 주고 본문 status로 알리는데, 이를 모르고 200만 보면 빈 데이터를 정상으로 오인합니다. 그래서 status를 먼저 검사해 예외로 올리고, 금액 콤마 문자열 파싱, 연결/별도 폴백을 순수 함수로 분리해 픽스처로 테스트했습니다.

**Q. "이거 데이터 엔지니어링 프로젝트 아닌가요?"**
> 그 위험을 알고 **범위를 공격적으로 잘랐습니다.** 기업 10개·계정 5개·주요계정 API만 써서 정규화 늪을 피했습니다. 목적은 데이터 정제가 아니라 AI 에이전트를 보여주는 것이라, 정형 데이터 비중을 의도적으로 눌렀습니다.

### 🎴 암기 카드
- corp_code ≠ 종목코드 (corpCode.xml 매핑)
- 실패도 200 + status (≠"000" 예외)
- 금액 = 콤마 문자열 → int
- CFS(연결) 우선, OFS(별도) 폴백

---

## 8-2. 캐싱 전략

### 왜 (필수)
- DART는 **키당 일일 호출 한도**가 있음 → 같은 데이터 재요청 금지.
- 두 노트북을 오가도 캐시가 있으면 네트워크 스킵.

### 작동 / 이 프로젝트
- `dart_client.py`: 응답을 `data/raw/facts/{corp_code}_{year}_{reprt_code}.json`에 저장. 있으면 네트워크 스킵.
- **중요 디테일**: `status != "000"`(데이터 없음/오류)은 **캐시하지 않음** → 실패를 영구 저장하지 않음.
- 서술 텍스트: `data/raw/filings/`에 캐싱. `data/raw/`는 git 제외(.gitignore).

### 면접 Q&A
**Q. API 한도를 어떻게 관리했나요?**
> 응답을 디스크에 캐싱하고 캐시 우선으로 동작하게 했습니다. 단, 정상(status 000) 응답만 캐싱해 일시적 오류를 영구화하지 않았고, 요청 직전에만 지연을 둬 호출을 분산했습니다.

### 🎴 암기 카드
- 캐싱 이유 = 일일 한도
- 캐시 우선, 정상(000)만 저장
- data/raw/ = git 제외

---

## 8-3. 파일 파싱 (zip · XML · HTML)

### 다룬 포맷
- **zip(binary)** — `corpCode.xml`, `document.xml`이 zip으로 옴. 매직바이트 `PK`로 판별, 아니면 에러 본문(XML).
- **XML** — `corpCode.xml`(회사 매핑), `ElementTree`로 파싱.
- **HTML** — 사업보고서 원문, BeautifulSoup+lxml로 텍스트 추출(가장 큰 HTML 파일 선택).

### 인코딩 방어
- HTML이 utf-8/euc-kr/cp949 등 섞임 → 순차 디코딩 시도 후 실패 시 `errors="replace"`.

### 면접 Q&A
**Q. 공시 원문에서 텍스트를 어떻게 뽑았나요?**
> document.xml zip을 받아 매직바이트로 zip 여부를 확인하고, 압축 안에서 가장 큰 HTML을 본문으로 골라 BeautifulSoup으로 script/style을 제거하고 텍스트만 추출했습니다. 인코딩이 섞여 있어 utf-8·euc-kr·cp949 순으로 디코딩을 시도했습니다.

### 🎴 암기 카드
- zip 판별 = 매직바이트 'PK'
- XML=ElementTree, HTML=BeautifulSoup+lxml
- 인코딩 = 순차 시도 + replace 폴백
