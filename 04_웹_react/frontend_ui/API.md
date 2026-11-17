# 화면이 FastAPI에 요청하는 것 (백엔드 담당용)

화면은 아래 3개 주소만 부릅니다. 이 모양대로 JSON을 돌려주면 화면 코드는 고칠 게 없어요.
`/chat`은 이미 `jellycast-chat`에 있고, `/beaches` 2개를 FastAPI에 추가하면 됩니다.

- 퍼센트 값은 모두 **0~100** (예: 12.1 = 12.1%). DB의 risk_index가 0~1이면 ×100 해서 보내 주세요.
- 값이 없으면 `null` → 화면에 회색 "자료 없음"으로 나옵니다.
- 위험등급 색은 화면이 퍼센트로 정합니다: 매우 높음 ≥60, 높음 ≥40, 보통 ≥20, 낮음 <20 (챗봇 `forecast.py`의 `LEVELS`와 같은 기준).
- 'N월 M주'는 그 달 날짜를 7일씩 끊은 순번입니다 (1~7일 1주, 8~14일 2주, 15~21일 3주, 22일 이후 4주). 같은 규칙이 `src/api/week.js`에 있어요.
- 서버가 꺼져 있거나 이 주소가 아직 없으면 화면은 예시 데이터로 대신 보여 줍니다 (`src/api/mock.js`).

---

## 1. 해수욕장 목록 — 지도 마커

`GET /beaches?date=2026-11-11`

```json
{
  "date": "2026-11-11",
  "week_label": "11월 2주",
  "beaches": [
    {
      "id": 1,
      "name": "화진해수욕장",
      "region": "경상북도 포항시 · 경북권역",
      "lat": 36.258,
      "lng": 129.378,
      "average_percent": 10.4,
      "forecast_percent": { "1": 12.1, "2": 4.2, "4": 11.2 }
    }
  ]
}
```

| 필드 | 뜻 |
|---|---|
| `average_percent` | 조회 날짜 주의 평년 출현율 (지도색 기준 "평년 출현율"일 때 마커 색) |
| `forecast_percent` | 1·2·4주 뒤 예측 위험 지수 (지도색 기준 "예측 위험 지수" + 예측 기간 탭일 때 마커 색) |
| `id` | `/beaches/{id}`와 챗봇 `beach_id`에 그대로 쓰여요. DB의 beach_id를 넣어 주세요. |

## 2. 선택한 해수욕장 상세 — 카드·안내·그래프

`GET /beaches/1?date=2026-11-11`

```json
{
  "beach": {
    "id": 1,
    "name": "화진해수욕장",
    "region": "경상북도 포항시 · 경북권역",
    "size": "길이 750m · 너비 75m",
    "week_label": "11월 2주",
    "average_percent": 10.4,
    "species": [
      { "name": "노무라입깃(유해)", "value": 2.4 },
      { "name": "보름달물", "value": 3.6 },
      { "name": "기타", "value": 4.7 }
    ]
  },
  "forecast": {
    "items": [
      { "weeks": 1, "week": "11월 3주", "percent": 12.1 },
      { "weeks": 2, "week": "11월 4주", "percent": 4.2 },
      { "weeks": 4, "week": "12월 2주", "percent": 11.2 }
    ],
    "report_date": "2026.10.30"
  },
  "observation": {
    "report_date": "2026.10.30",
    "region_name": "경북",
    "region_rate": 4.2,
    "station": "포항 부이",
    "station_distance": "38.3km",
    "avg_temp": "19.6°C",
    "latest_label": "가장 최근 관측 (2026-11-09 주)",
    "latest_temp": "수온 20.4°C"
  },
  "notice": {
    "message": "2026-10-30 주간보고를 넣은 모델 예측입니다.",
    "model": "효섭 로지스틱 모델 · 권역예측 테이블"
  },
  "season": {
    "data": [
      { "label": "5월 1주", "total": 2.0, "nomura": 0.5, "moon": 2.1, "other": 1.0 }
    ],
    "selected_index": 25,
    "is_example": false
  }
}
```

| 필드 | 뜻 |
|---|---|
| `season.data` | 5월 1주 ~ 12월 4주, **32개**. total=통합, nomura=노무라, moon=보름달, other=기타 |
| `season.selected_index` | 조회 날짜 주의 위치 (5월 1주=0 … 11월 2주=25). 5월 전이면 `null` |
| `season.is_example` | 주차별 실제 데이터가 없어 예시로 채웠으면 `true` → 그래프 제목 옆에 "예시 데이터" 배지 |

## 3. 챗봇

`POST /chat` — `jellycast-chat` 서버 그대로입니다.

```json
// 요청
{ "message": "해파리에 쏘이면 어떻게 해?", "beach_id": 1, "horizon_weeks": 1,
  "history": [{ "role": "user", "text": "..." }, { "role": "model", "text": "..." }] }

// 응답
{ "answer": "...", "emergency": false, "forecast": [],
  "sources": [{ "기관": "보건복지부·중앙응급의료센터", "url": "https://www.e-gen.or.kr" }] }
```

`emergency`가 `true`면 대화창 답변 위에 빨간 "119" 버튼이 붙어요.

---

## FastAPI 예시 뼈대

```python
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/beaches")
def list_beaches(date: str):
    # DB에서 해수욕장 + 해당 주 평년 출현율 + 1·2·4주 예측을 읽어 위 모양으로
    return {"date": date, "week_label": week_label(date), "beaches": [...]}

@router.get("/beaches/{beach_id}")
def beach_detail(beach_id: int, date: str):
    row = ...  # 없으면 raise HTTPException(404)
    return {"beach": {...}, "forecast": {...}, "observation": {...}, "notice": {...}, "season": {...}}
```

`main.py`에서 `app.include_router(router)` 하면 `/chat`과 같은 서버에서 같이 돌아가요. CORS는 `CORS_ORIGINS`에 화면 주소(개발 중 `http://localhost:5173`)가 들어 있으면 됩니다.
