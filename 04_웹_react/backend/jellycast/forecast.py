"""예보 조회: 질문에 나온 해수욕장·지역을 찾아 1·2·4주 뒤 위험 지수를 가져온다.

원본(jellycast-chat)은 SQL 3개로 따로 조회했지만, 여기서는 웹 화면과 같은 자료를 쓴다.
  - 서버(main.py)가 시작할 때 DB에서 읽어 둔 자료(서비스로직.위험도서비스)를 그대로 사용
  - 1·2·4주 뒤 값은 화면과 같은 규칙(최근 14일 안 주간보고 → 모델 예측, 없으면 평년 기준 전망)
  → 상담봇 숫자와 지도·상세 패널 숫자가 항상 같다
함수 이름과 반환 키(beach_id, beach_name, sido, horizon_weeks, risk_index ...)는 원본과 같아서 chat.py는 그대로 쓴다.
"""
from __future__ import annotations

import datetime as dt
import re

from 서비스로직 import 등급_구하기, 대상주, 지수_표시, 한글날짜

# main.py가 시작할 때 연결해 준다: svc() → 위험도서비스, 예측표(날짜) → 예측표(DataFrame)
_provider = {"svc": None, "예측표": None}


def 연결(svc, 예측표):
    _provider.update(svc=svc, 예측표=예측표)


def _svc():
    if _provider["svc"] is None:
        raise RuntimeError("예보 자료가 아직 연결되지 않았습니다 (main.py 시작 전)")
    return _provider["svc"]()


REGIONS = {  # 질문에 나올 수 있는 말 → 시도명에서 찾을 글자
    "부산": ["부산"], "울산": ["울산"], "인천": ["인천"], "제주": ["제주"],
    "강원": ["강원"], "경기": ["경기"],
    "경북": ["경상북", "경북"], "경상북도": ["경상북", "경북"],
    "경남": ["경상남", "경남"], "경상남도": ["경상남", "경남"],
    "전남": ["전라남", "전남"], "전라남도": ["전라남", "전남"],
    "전북": ["전라북", "전북"], "전라북도": ["전라북", "전북"],
    "충남": ["충청남", "충남"], "충청남도": ["충청남", "충남"],
}


def risk_level(x) -> str:
    """위험 등급: 화면과 같은 4단계 (낮음 <0.2 / 보통 / 높음 ≥0.4 / 매우 높음 ≥0.6, 값 없으면 '자료 없음')"""
    return 등급_구하기(x)[0]


def beaches() -> list[dict]:
    h = _svc().해수욕장
    return [{"beach_id": r.해수욕장ID, "beach_name": r.해수욕장명, "sido": r.시도명} for r in h.itertuples()]


def _short(name: str) -> str:
    return re.sub(r"\s*해수욕장$", "", name).strip()


def find_beaches(message: str) -> list[dict]:
    """질문 속에 이름이 나온 해수욕장 (예: '해운대 다음 주' → 해운대)."""
    hits = [b for b in beaches() if len(_short(b["beach_name"])) >= 2 and _short(b["beach_name"]) in message]
    return sorted(hits, key=lambda b: -len(b["beach_name"]))[:3]


def find_region(message: str) -> str | None:
    for word in sorted(REGIONS, key=len, reverse=True):
        if word in message:
            return word
    return None


def guess_horizon(message: str, default: int = 1) -> int:
    if re.search(r"4\s*주|한\s*달|다음\s*달", message):
        return 4
    if re.search(r"2\s*주|다다음\s*주", message):
        return 2
    if re.search(r"다음\s*주|이번\s*주말|1\s*주", message):
        return 1
    return default


def _rows(p, 오늘) -> list[dict]:
    """예측표 일부 → 상담봇이 쓰는 행(dict) 목록"""
    s = _svc()
    out = []
    for r in p.itertuples():
        b = s.B.loc[r.해수욕장ID]
        v = None if r.예측위험지수 != r.예측위험지수 else float(r.예측위험지수)      # NaN → None
        out.append({"beach_id": r.해수욕장ID, "beach_name": b.해수욕장명, "sido": b.시도명,
                    "horizon_weeks": int(r.예측기간),
                    "target_week": 대상주(오늘, int(r.예측기간))["라벨"],
                    "risk_index": v, "risk_level": risk_level(v),
                    "risk_text": 지수_표시(r.예측위험지수, r.정렬지수),          # 화면과 같은 표기 (예: 5.8%, 100% (상한))
                    "base_date": (f"{한글날짜(r.기준일)} 주간보고 기준 예측" if r.방식 == "모델" else "평년 기준 전망")})
    return out


def beach_forecast(beach_id: str) -> list[dict]:
    """선택한 해수욕장의 오늘 기준 1·2·4주 뒤 (화면 상세 패널과 같은 값)"""
    오늘 = dt.date.today()
    p = _provider["예측표"](오늘)
    return _rows(p[p["해수욕장ID"] == beach_id].sort_values("예측기간"), 오늘)


def safer_beaches(region: str | None, horizon: int, limit: int = 3) -> list[dict]:
    """같은 지역(region=None이면 전국)에서 k주 뒤 위험 지수가 낮은 해수욕장 (대안 추천용)"""
    오늘 = dt.date.today()
    s = _svc()
    p = _provider["예측표"](오늘)
    if region:
        patterns = REGIONS.get(region, [region])
        ids = set(s.해수욕장.loc[s.해수욕장["시도명"].str.contains("|".join(patterns)), "해수욕장ID"])
        p = p[p["해수욕장ID"].isin(ids)]
    p = p[(p["예측기간"] == horizon) & p["정렬지수"].notna()]
    return _rows(p.sort_values("정렬지수").head(limit), 오늘)
