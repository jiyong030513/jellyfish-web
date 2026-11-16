# 04_웹_react — 해파리 위험도 조회 (React + FastAPI)

이 프로젝트의 **최종 웹**입니다 (처음 만든 Streamlit 버전은 이 버전으로 대체하고 삭제함).
DB 조회·위험도 계산은 `02_웹_수집\서비스로직.py`를 그대로 불러 쓰고, 이 폴더는 화면(React)과 API(FastAPI)만 담당합니다.
DB 접속 정보는 `02_웹_수집\db.py`가 `.env`에서 읽습니다 (이 폴더에는 비밀번호가 없음).

## 실행

```
cd 04_웹_react
python run.py
```

- 백엔드(FastAPI, 8000번)와 프론트엔드(Vite, 5173번)가 같이 켜지고 브라우저가 자동으로 열립니다 → http://localhost:5173
- 끌 때는 **Ctrl + C 한 번** → 둘 다 꺼집니다.
- 처음 실행할 때는 `npm install`을 자동으로 합니다 (1~2분). Node.js(LTS)가 있어야 하고, DB는 `.env`가 가리키는 곳(현재 클라우드 TiDB)을 씁니다.
- 주소로 바로 열기: `http://localhost:5173/?beach=B149&date=2023-08-10` (해수욕장ID, 날짜)
- API 문서(자동 생성): http://127.0.0.1:8000/docs
- 필요한 파이썬 패키지: `pip install -r backend\requirements.txt` (FastAPI, uvicorn, pandas, numpy, pymysql)

## 배포 (인터넷 공개)

**공유 링크: https://jellyfish-web-one.vercel.app**  (예: `?beach=B149&date=2023-08-10`)

| 역할 | 서비스 (모두 무료) | 주소 |
|---|---|---|
| 화면 (React) | Vercel | https://jellyfish-web-one.vercel.app |
| 백엔드 (FastAPI) | Render (싱가포르) | https://jellyfish-api-e3lz.onrender.com (`/docs`에서 API 확인) |
| DB | TiDB Cloud Starter (도쿄, MySQL 호환) | `02_웹_수집\.env`의 MYSQL_ 값 |

- DB 이전: `02_웹_수집\클라우드_이전.py`가 내 PC MySQL의 테이블·데이터를 그대로 옮기고, 뷰 7개는 원본 SQL2_views.sql로 다시 만든다.
  TiDB에는 공간 함수가 없어 v_해수욕장가중치의 `ST_Distance_Sphere`만 같은 하버사인 공식(반지름 6,370,986m)으로 바꿔 실행 (원본 파일은 그대로).
  이전 후 테이블 11개·뷰 7개의 모든 값이 내 PC와 같음을 확인.
- 비밀번호·키는 `02_웹_수집\.env`(GitHub에 올라가지 않음)와 Render 환경변수에만 있음.
- 매주 갱신: `update_all.py`가 클라우드 DB에 직접 쓰고, 마지막에 Render의 `/api/reload`를 호출해 웹이 새 자료를 읽음.
- Render 무료 서버는 15분간 접속이 없으면 잠든다 (깨우는 데 1분 정도).
  → UptimeRobot(무료)이 5분마다 `https://jellyfish-api-e3lz.onrender.com/api/health`에 접속해 잠들지 않게 함.
  Render 무료는 월 750시간이라 서버 1대를 24시간 켜 둬도 한도 안 (다른 무료 서버를 추가하면 시간을 나눠 씀).
- 코드 수정 반영
  - 백엔드: GitHub `main`에 push한 뒤 Render 화면에서 **Manual Deploy → Deploy latest commit** (자동 배포 설정은 켜져 있지만 실제로는 동작하지 않는 경우가 있었음)
  - 화면: `04_웹_react\frontend`에서 `npx vercel deploy --prod` (Vercel 로그인 또는 토큰 필요)

## 폴더 구조

```
04_웹_react
├─ run.py                 백엔드 + 프론트엔드 같이 실행
├─ backend
│  └─ main.py             FastAPI. 02_웹_수집의 서비스로직.py · db.py를 import
└─ frontend               Vite + React + TypeScript
   ├─ index.html          Pretendard 글꼴
   └─ src
      ├─ App.tsx          전체 화면 (조건 · 지도 · 상세 · 그래프 · SQL)
      ├─ api.ts           API 호출과 자료형
      ├─ MapView.tsx      react-leaflet 지도 (OpenStreetMap, flyTo, 강조 원)
      ├─ Search.tsx       자동완성 검색 ("해운" → 해운대)
      ├─ Detail.tsx       오른쪽 상세 패널
      ├─ Curve.tsx        5~12월 평년 출현율 (Recharts)
      ├─ SqlPanel.tsx     "이 화면에서 쓴 SQL 보기"
      └─ styles.css       바다 테마 · 카드 · 좁은 화면 대응
```

## 화면 → API → SQL 대응

백엔드는 시작할 때 아래 SQL 6개를 **한 번** 실행해 메모리에 두고, 이후 요청은 메모리에서 계산합니다.
`DB 다시 불러오기` 버튼(POST /api/reload)을 누르면 다시 읽습니다.

| 화면 | API | 쓰는 SQL (서비스로직.py의 `SQL`) |
|---|---|---|
| 검색 자동완성, 지도 점 위치 | `GET /api/beaches` | 해수욕장 (해수욕장 ⨝ 시군 ⨝ 관측소) |
| 지도 색 — 평년 출현율 | `GET /api/map?date=&mode=평년&k=` | 평년 (`v_해수욕장주간위험도`) |
| 지도 색 — 예측 위험 지수 | `GET /api/map?date=&mode=예측&k=1\|2\|4` | 예측 (`v_해수욕장예측위험도`) · 보고 (`v_학습데이터`) · 가중치 (`v_해수욕장가중치`) |
| 선택 전: 위험 지수 상위 10곳 | `GET /api/top?date=&k=` | 예측 · 보고 · 가중치 |
| 상세 ① 평년 출현율 (어종별) | `GET /api/beach/{id}?date=` | 평년 |
| 상세 ② 1·2·4주 뒤 + 배지 + 최근 주간보고 | 〃 | 예측 · 보고 · 가중치 |
| 상세 ③ 해수욕장 가중치 | 〃 | 가중치 |
| 상세 ④ 연결 관측소 (최근 수온) | 〃 | 해수욕장 · 관측 (`관측자료`) |
| 5~12월 평년 출현율 그래프 | 〃 (`곡선`) | 평년 |
| 이 화면에서 쓴 SQL 보기 | `GET /api/sql` | (SQL 목록 자체) |
| 출처 문구 · 등급 범례 | `GET /api/meta` | 보고 |
| DB 다시 불러오기 | `POST /api/reload` | 6개 모두 다시 실행 |

1·2·4주 뒤 값: 선택한 날짜 14일 안에 주간보고가 있으면 그 보고를 넣은 **모델 예측**("○○ 주간보고를 넣은 모델 예측" 배지),
없으면 같은 시기 주간보고 비율 × 해수욕장 가중치인 **평년 기준 전망**("평년 기준 전망" 배지)입니다.

## 숫자 확인

| 경우 | 1주 뒤 | 2주 뒤 | 4주 뒤 | 방식 |
|---|---|---|---|---|
| 2023-08-10 해운대 | 41.0% | 39.5% | 40.2% | 2023년 8월 4일 주간보고 모델 예측 |
| 2026-11-08 상주은모래비치 | 14.6% | 5.4% | 11.9% | 2026년 10월 30일 주간보고 모델 예측 |
| 2027-07-17 무창포 | 68.5% | 68.5% | 100% (상한) | 평년 기준 전망 |

로컬 실행, 클라우드 DB, 배포 사이트에서 모두 같은 값임을 확인. 캡처: `화면캡처\react\`, `화면캡처\배포\`

## 화면 기능
- 조건: 날짜(기본 오늘), 해수욕장 검색(이름 일부 자동완성, ↑↓·Enter), 지도 색 기준(평년 출현율 / 예측 위험 지수), 예측 기간(1·2·4주)
- 지도: 해수욕장 270곳을 등급 색 원으로 표시, 마우스를 올리면 이름·값, 클릭·검색하면 flyTo로 이동 + 강조 원, "전국 보기" 버튼
- 상세: 평년 출현율(어종별), 1·2·4주 뒤 위험 지수(모델 예측 / 평년 기준 전망 배지, ⓘ 계산 근거), 최근 주간보고, 가중치, 연결 관측소
- 그래프: 5~12월 평년 출현율 (통합·노무라·보름달·기타, 선택한 주 세로선)
- 이 화면에서 쓴 SQL 보기 (발표용)
- 주소창이 선택한 해수욕장·날짜로 자동 갱신 → 링크 공유 시 같은 화면
- 반응형: 3단(넓은 화면) → 2단 → 1단(휴대폰)

## AI 해파리 상담봇 (`backend/jellycast/`, `POST /api/chat`)
- RAG: 예보(서비스로직 자료, 화면과 같은 숫자) + 대비수칙 자료(`backend/jellycast/knowledge/*.md`) 검색 → Gemini 답변 + 서버가 출처 첨부
- 요청: `{ message, beach_id?: "B149", horizon_weeks?: 1|2|4, date?: "2023-08-10", history?: [{role, text}] }` (date = 화면에서 고른 날짜 → 화면과 같은 숫자)
- 답: 예보 + 시즌(평년 출현율 최고 주) + 위험 낮은 곳 추천(지역 없으면 전국), 답 아래 📍해수욕장 버튼 → 지도 이동 → 응답: `{ answer, emergency, forecast, sources }`
- `emergency: true`면 화면 맨 위에 119 배너 (ChatBot.tsx)
- 비밀값: `GEMINI_API_KEY`, `GEMINI_MODEL`(gemini-3.5-flash-lite)은 `02_웹_수집\.env`와 Render 환경변수에만
- `knowledge/` 6개 파일(답변원칙·응급처치·대처요령·예방수칙·출현정보·독성해파리) 포함. 없으면 `/api/chat`만 503
- 테스트: `cd backend && pytest -q` (DB·키 없이 7개)
