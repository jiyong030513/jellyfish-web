# 04_웹_react — 해파리 위험도 조회 (React + FastAPI)

02_웹_수집의 Streamlit 화면과 **같은 내용**을 React로 만든 버전입니다.
계산은 새로 만들지 않고 `02_웹_수집\서비스로직.py`를 그대로 불러 쓰므로 **두 웹의 숫자는 항상 같습니다.**
DB 접속 정보는 `02_웹_수집\db.py`에서만 읽습니다 (이 폴더에는 비밀번호가 없음).

## 실행

```
cd 04_웹_react
python run.py
```

- 백엔드(FastAPI, 8000번)와 프론트엔드(Vite, 5173번)가 같이 켜지고 브라우저가 자동으로 열립니다 → http://localhost:5173
- 끌 때는 **Ctrl + C 한 번** → 둘 다 꺼집니다.
- 처음 실행할 때는 `npm install`을 자동으로 합니다 (1~2분). Node.js(LTS)와 MySQL 서비스가 켜져 있어야 합니다.
- 주소로 바로 열기: `http://localhost:5173/?beach=B149&date=2023-08-10` (해수욕장ID, 날짜)
- API 문서(자동 생성): http://127.0.0.1:8000/docs
- 필요한 파이썬 패키지: `pip install -r backend\requirements.txt` (FastAPI, uvicorn, pandas, numpy, pymysql)

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

## 숫자 확인 (Streamlit과 비교)

| 경우 | 1주 뒤 | 2주 뒤 | 4주 뒤 | 방식 |
|---|---|---|---|---|
| 2023-08-10 해운대 | 41.0% | 39.5% | 40.2% | 2023년 8월 4일 주간보고 모델 예측 |
| 2026-11-08 상주은모래비치 | 14.6% | 5.4% | 11.9% | 2026년 10월 30일 주간보고 모델 예측 |
| 2027-07-17 무창포 | 68.5% | 68.5% | 100% (상한) | 평년 기준 전망 |

세 경우 모두 1·2·4주 카드 값과 계산 근거(도움말), 평년 출현율(통합·노무라·보름달·기타)이 Streamlit 화면과 같습니다.
캡처: `화면캡처\react\` (넓은 화면 1440px, 좁은 화면 390px, 자동완성)

## Streamlit 버전과의 차이

| | Streamlit (02_웹_수집\app.py) | React (04_웹_react) |
|---|---|---|
| 실행 | `python app.py` (8501) | `python run.py` (5173 + API 8000) |
| 구조 | 화면과 서버가 한 프로그램 | 화면(React)과 API(FastAPI) 분리 — 다른 앱에서도 API 재사용 가능 |
| 계산 | 서비스로직.py | 같은 서비스로직.py (그대로 import) |
| 클릭·조건 변경 | 바뀔 때마다 스크립트 전체 다시 실행 | 필요한 API만 호출 → 지도가 다시 그려지지 않고 바로 반응 |
| 지도 | folium (iframe), flyTo는 setView를 가로채서 구현 | react-leaflet, `map.flyTo` 직접 사용 |
| 검색 | 선택 상자 (목록에서 고르기) | 이름 일부 자동완성, ↑↓·Enter |
| 그래프 | Altair | Recharts |
| 화면 문구·숫자 형식 | app.py에서 만듦 | 백엔드가 같은 형식의 문자열을 만들어 보냄 (반올림을 Python 한 곳에서만) |
| 좁은 화면 | Streamlit 기본 | 3단 → 2단 → 1단으로 바뀜 |
| 추가 | — | 주소창이 선택한 해수욕장·날짜로 자동 갱신, "전국 보기" 버튼 |
