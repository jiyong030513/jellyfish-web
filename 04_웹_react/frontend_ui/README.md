# 젤리캐스트 웹 화면 (React + Vite)

Figma 최종 시안(메인 화면 · 수정 카드 로딩 상태) 그대로의 화면에
실제 지도(Leaflet), FastAPI 연결, 검색·날짜·업데이트 동작, 챗봇 대화창까지 붙인 버전입니다.

## 바로 실행

```bash
npm install
npm run dev            # http://localhost:5173
```

서버가 없어도 예시 데이터로 전부 돌아갑니다. FastAPI에 붙일 때는:

```bash
cp .env.example .env   # VITE_API_BASE=http://localhost:8000 확인
npm run dev
```

배포용은 `npm run build` → `dist/` 폴더를 올리면 됩니다.

## 서버에 필요한 것

화면은 `GET /beaches`, `GET /beaches/{id}`, `POST /chat` 세 개만 부릅니다.
`/chat`은 jellycast-chat 서버에 이미 있고, `/beaches` 두 개만 추가하면 됩니다.
**응답 모양과 FastAPI 뼈대는 `API.md`에 있어요.**
아직 `/beaches`가 없으면 그 부분만 예시 데이터로 나오고 챗봇은 실제 서버로 갑니다.

## 동작

| 하는 것 | 결과 |
|---|---|
| 처음 열기 · 날짜 변경 · 업데이트 버튼 | 목록과 상세를 다시 불러옴, 그동안 시안의 로딩 화면 |
| 지도 마커 클릭 · 검색 | 그 해수욕장으로 지도 이동, 카드·그래프만 다시 불러옴 |
| 검색어 | 해수욕장 이름 → 지역 순으로 찾아 첫 번째 선택. 없으면 왼쪽 카드 안내 문구로 알림 |
| 지도색 기준 · 예측 기간 | 이미 받은 값으로 마커 색만 바뀜 (서버 요청 없음) |
| 전국 보기 · + / − | 지도 전국 범위 · 확대 · 축소 |
| 오른쪽 아래 "해파리 AI 가이드" | 대화창 열림. 선택한 해수욕장과 예측 기간을 같이 보냄. 응급이면 119 버튼, 답변마다 출처. Esc로 닫기 |

## 폴더

```
src/
  App.jsx               메인 화면 배치
  hooks/useJellyCast.js 화면 상태 + 불러오기 흐름 (날짜·선택·검색·업데이트)
  api/
    client.js           FastAPI 요청 + 응답 → 화면 데이터 변환 (서버 바뀌면 여기만 수정)
    mock.js             서버 없을 때 예시 응답 (17개 해수욕장)
    week.js             날짜 ↔ 'N월 M주' 변환
  components/
    BeachMap.jsx        Leaflet 지도 (마커 색칠·선택·이동)
    ChatPanel.jsx       챗봇 대화창
    basics.jsx, sections.jsx, icons.jsx, components.css   시안 컴포넌트
  styles/tokens.css, tokens.js   Figma 글꼴·색·간격
  page.css              1344px 화면 배치
  dev/Sheet.jsx         개발용 컴포넌트 모음 (주소 뒤 #sheet)
API.md                  서버 응답 형식
.env.example            서버 주소·지도 타일 설정
```

## 기존 프로젝트에 합칠 때

`src/` 폴더 전체를 복사하고 `npm install leaflet`만 추가하면 됩니다.
`main.jsx`처럼 `styles/tokens.css`와 `page.css`를 한 번 import 해 주세요.

## 참고

- 개발 중(`npm run dev`)에는 왼쪽 아래에 화면 / 컴포넌트 시트 / 로딩 화면 고정 버튼이 보입니다. 빌드 결과물에는 나오지 않아요.
- 지도 타일은 OpenStreetMap 무료 타일입니다. 시연에는 충분하지만 실제 서비스로 많이 쓰려면 VWorld 등 다른 타일로 바꾸는 게 좋아요 (`.env`의 `VITE_MAP_TILE_URL`).
- 예시 데이터의 숫자와 해수욕장 좌표는 화면 확인용이며 실제 관측·예측값이 아닙니다.
