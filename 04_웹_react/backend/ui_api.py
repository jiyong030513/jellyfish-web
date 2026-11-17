"""피그마 시안 화면(frontend_ui)용 API: GET /api/ui/beaches, GET /api/ui/beaches/{id}

응답 모양은 화면 담당이 정한 API.md 그대로 (퍼센트는 0~100, 값 없으면 null).
숫자는 기존 화면(/api/map, /api/beach)과 같은 서비스로직 자료에서 만든다 → 두 화면·상담봇 숫자가 같다.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException

from 서비스로직 import 없음, 월_주차, 한글날짜

router = APIRouter()
_p = {"svc": None, "예측표": None}


def 연결(svc, 예측표):
    _p.update(svc=svc, 예측표=예측표)


def _날짜(s: str) -> dt.date:
    if not s:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        raise HTTPException(400, "date는 YYYY-MM-DD 형식이어야 해요")


def _pct(v):
    """0~1 → 0~100 (소수 1자리), 없으면 None"""
    return None if 없음(v) else round(float(v) * 100, 1)


def _점(d) -> str:
    return "-" if d is None or 없음(d) else f"{d:%Y.%m.%d}"


def _지역(b) -> str:
    return f"{b.시도명} {b.시군명} · {b.권역명}권역"


@router.get("/beaches")
def list_beaches(date: str = ""):
    날짜 = _날짜(date)
    s = _p["svc"]()
    월, 주차 = 월_주차(날짜)
    평년 = s.지도색값(날짜, "평년 출현율", 1, None)
    p = _p["예측표"](날짜)
    예측 = {}
    for r in p.itertuples():
        예측.setdefault(r.해수욕장ID, {})[str(int(r.예측기간))] = _pct(r.예측위험지수)
    return {"date": 날짜.isoformat(), "week_label": f"{월}월 {주차}주",
            "beaches": [{"id": b.해수욕장ID, "name": b.해수욕장명, "region": _지역(b),
                         "lat": float(b.위도), "lng": float(b.경도),
                         "average_percent": _pct(평년.get(b.해수욕장ID)),
                         "forecast_percent": 예측.get(b.해수욕장ID, {})}
                        for b in s.해수욕장.itertuples()]}


@router.get("/beaches/{beach_id}")
def beach_detail(beach_id: str, date: str = ""):
    날짜 = _날짜(date)
    s = _p["svc"]()
    if beach_id not in s.B.index:
        raise HTTPException(404, f"해수욕장 {beach_id} 없음")
    예측 = _p["예측표"](날짜)
    d = s.상세(beach_id, 날짜, 예측)
    b = s.B.loc[beach_id]
    평 = d["평년"] or {}

    모델 = 예측[(예측["해수욕장ID"] == beach_id) & (예측["방식"] == "모델")]
    기준일 = None if 모델.empty else 모델["기준일"].iloc[0]

    rb, o = d["최근보고"], d["관측소"]
    곡선 = s.곡선(beach_id)
    data = [{"label": r.주차명, "total": _pct(r.통합출현율), "nomura": _pct(r.노무라),
             "moon": _pct(r.보름달), "other": _pct(r.기타)} for r in 곡선.itertuples()]
    idx = [i for i, r in enumerate(곡선.itertuples()) if r.월 == d["월"] and r.주차 == d["주차"]]

    return {
        "beach": {"id": beach_id, "name": d["이름"], "region": _지역(b),
                  "size": f"길이 {b.길이:,}m · 너비 {b.너비:,}m", "week_label": d["주차이름"],
                  "average_percent": _pct(평.get("통합")),
                  "species": [{"name": "노무라입깃(유해)", "value": _pct(평.get("노무라"))},
                              {"name": "보름달물", "value": _pct(평.get("보름달"))},
                              {"name": "기타", "value": _pct(평.get("기타"))}]},
        "forecast": {"items": [{"weeks": int(x["예측기간"]), "week": x["대상"], "percent": _pct(x["값"])}
                               for x in d["예측칸"]],
                     "report_date": _점(기준일) if 기준일 is not None else "평년 기준 전망"},
        "observation": {
            "report_date": _점(rb["시작일"]) if rb else "-",
            "region_name": d["권역명"],
            "region_rate": None if not rb or 없음(rb["통합"]) else round(float(rb["통합"]), 1),  # 주간보고 통합은 이미 %
            "station": f"{o['이름']} 부이",
            "station_distance": f"{o['거리km']:.1f}km",
            "avg_temp": "-" if 없음(o["평년수온"]) else f"{o['평년수온']:.1f}°C",
            "latest_label": "가장 최근 관측" if o["최근시작일"] is None else f"가장 최근 관측 ({o['최근시작일']:%Y-%m-%d} 주)",
            "latest_temp": "-" if 없음(o["최근수온"]) else f"수온 {o['최근수온']:.1f}°C"},
        "notice": {"message": (f"{한글날짜(기준일)} 주간보고를 넣은 모델 예측입니다." if 기준일 is not None
                               else "최근 2주 안에 주간보고가 없어 평년 기준 전망입니다."),
                   "model": ("로지스틱 회귀 모델 · 권역예측 테이블" if 기준일 is not None
                             else "같은 시기 주간보고의 대량출현 비율 × 해수욕장 가중치")},
        "season": {"data": data, "selected_index": idx[0] if idx else None, "is_example": False},
    }


@router.get("/top")
def top(date: str = "", k: int = 1):
    """k주 뒤 위험 지수 상위 10곳 (기존 화면 /api/top과 같은 계산)"""
    if k not in (1, 2, 4):
        raise HTTPException(400, "k는 1, 2, 4 중 하나예요")
    from 서비스로직 import 대상주
    날짜 = _날짜(date)
    s = _p["svc"]()
    t = s.상위(_p["예측표"](날짜), k)
    대상 = 대상주(날짜, k)
    return {"title": f"{k}주 뒤 위험 지수 상위 10곳", "week": f"{대상['이름']} ({대상['범위']})",
            "items": [] if t.empty else [
                {"id": r.해수욕장ID, "name": r.해수욕장명, "region": f"{r.시군명} · {r.권역명}권역",
                 "percent": _pct(r.예측위험지수), "label": r.표시,
                 "method": "모델 예측" if r.방식 == "모델" else "평년 기준 전망"} for r in t.itertuples()]}
