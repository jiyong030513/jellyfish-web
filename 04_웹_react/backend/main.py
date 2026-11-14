"""해파리 위험도 조회 API (FastAPI)

계산은 02_웹_수집의 서비스로직.py · db.py를 그대로 불러 쓴다 (DB 조회·위험도 계산은 서비스로직.py 한 곳에만).
DB 접속 정보도 02_웹_수집/db.py에서만 읽는다.

실행 (보통은 04_웹_react/run.py가 대신 켬):
    python -m uvicorn main:app --port 8000      (backend 폴더에서)
"""
import datetime as dt
import math
import os
import sys
import threading

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

WEB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "02_웹_수집"))
sys.path.insert(0, WEB)

from 서비스로직 import (SQL, 등급, 회색, 등급_구하기, 대상주, 월_주차, pct,  # noqa: E402
                    전체_불러오기, 위험도서비스, 한글날짜)

FRONT = os.environ.get("FRONT_PORT", "5173")
# 허용할 화면 주소: 개발 서버 + 배포한 화면 주소(환경변수 ALLOWED_ORIGINS, 쉼표로 여러 개)
ORIGINS = [f"http://localhost:{FRONT}", f"http://127.0.0.1:{FRONT}"] + \
          [o.strip().rstrip("/") for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app = FastAPI(title="해파리 위험도 조회 API")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])

# ---------------------------------------------------------------- DB를 한 번 읽어 메모리에 둠
_lock = threading.Lock()
_state = {"svc": None, "예측": {}, "불러온시각": None}


def _load():
    svc = 위험도서비스(전체_불러오기())
    with _lock:
        _state.update(svc=svc, 예측={}, 불러온시각=dt.datetime.now())


@app.on_event("startup")
def _startup():
    _load()


def svc():
    return _state["svc"]


def 예측표(날짜):
    """날짜별 예측표는 한 번 계산하면 기억해 둠 (DB 다시 불러오기 때 비움)"""
    c = _state["예측"]
    if 날짜 not in c:
        if len(c) > 60:
            c.clear()
        c[날짜] = svc().예측표(날짜)
    return c[날짜]


# ---------------------------------------------------------------- JSON 변환 (NaN → null, 날짜 → 'YYYY-MM-DD')
def js(o):
    if isinstance(o, dict):
        return {str(k): js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [js(v) for v in o]
    if isinstance(o, pd.DataFrame):
        return [js(r) for r in o.to_dict("records")]
    if o is None or o is pd.NaT:
        return None
    if isinstance(o, (pd.Timestamp, dt.datetime)):
        return None if pd.isna(o) else o.strftime("%Y-%m-%d")
    if isinstance(o, dt.date):
        return o.isoformat()
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, float) and math.isnan(o):
        return None
    return o


def 날짜_읽기(s):
    if not s:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        raise HTTPException(400, "date는 YYYY-MM-DD 형식이어야 해요")


def 기간_확인(k):
    if k not in (1, 2, 4):
        raise HTTPException(400, "k는 1, 2, 4 중 하나예요")
    return k


# ---------------------------------------------------------------- API
@app.get("/api/meta")
def meta():
    s = svc()
    return {"보고기간": s.보고기간_표시, "보고연도": s.보고연도, "해수욕장수": len(s.해수욕장),
            "불러온시각": _state["불러온시각"].strftime("%Y-%m-%d %H:%M:%S"),
            "등급": [{"이름": n, "하한": lo, "색": c} for lo, n, c in 등급] + [{"이름": "자료 없음", "하한": None, "색": 회색}]}


@app.get("/api/beaches")
def beaches():
    h = svc().해수욕장
    return js(h[["해수욕장ID", "해수욕장명", "시도명", "시군명", "권역명", "위도", "경도", "표시명"]])


@app.get("/api/map")
def map_values(date: str = "", mode: str = Query("평년", pattern="^(평년|예측)$"), k: int = 4):
    날짜, k = 날짜_읽기(date), 기간_확인(k)
    색기준 = "평년 출현율" if mode == "평년" else "예측 위험 지수"
    색값 = svc().지도색값(날짜, 색기준, k, 예측표(날짜) if mode == "예측" else None)
    값들 = {}
    for i in svc().해수욕장["해수욕장ID"]:
        v = 색값.get(i)
        name, color = 등급_구하기(v)
        값들[i] = {"값": v, "표시": pct(v), "등급": name, "색": color}
    월, 주차 = 월_주차(날짜)
    t = 대상주(날짜, k)
    설명 = "지도 색: 평년 출현율" if mode == "평년" else f"지도 색: {k}주 뒤 {t['이름']} 위험 지수"
    return js({"날짜": 날짜, "주차이름": f"{월}월 {주차}주", "날짜한글": 한글날짜(날짜), "시즌": 5 <= 월 <= 12,
               "설명": 설명, "값": 값들})


@app.get("/api/beach/{beach_id}")
def beach(beach_id: str, date: str = ""):
    날짜 = 날짜_읽기(date)
    s = svc()
    if beach_id not in s.B.index:
        raise HTTPException(404, f"해수욕장 {beach_id} 없음")
    예측 = 예측표(날짜)
    d = s.상세(beach_id, 날짜, 예측)
    for x in d["예측칸"]:
        x["범위"] = 대상주(날짜, int(x["예측기간"]))["범위"]
    # 배지 문구 (모델 예측이면 기준 주간보고 날짜)
    모델 = 예측[(예측["해수욕장ID"] == beach_id) & (예측["방식"] == "모델")]
    기준일 = None if 모델.empty else 모델["기준일"].iloc[0]
    d["기준일"] = 기준일
    d["배지"] = f"{한글날짜(기준일)} 주간보고를 넣은 모델 예측" if 기준일 is not None else "평년 기준 전망"
    # 화면 문구 (반올림을 Python 한 곳에서만 하려고 문자열로 만들어 보냄)
    p = d["평년"]
    if p:
        p["표시"] = {k: pct(p[k]) for k in ("통합", "노무라", "보름달", "기타")}
    if d["최근보고"]:
        rb = d["최근보고"]
        rb["문장"] = f"최근 주간보고 {한글날짜(rb['시작일'])} · {d['권역명']} 통합 출현율 {rb['통합']:.1f}%"
    if d["가중치"]:
        w = d["가중치"]
        w["문장"] = (f"반경 30km 설문 응답 {w['주변응답수']}건 중 목격 {w['주변목격수']}건 → "
                   f"가중치 {w['가중치']:.2f} (권역 평균 목격률 {pct(w['권역목격률'])})")
        w["표시"] = f"{w['가중치']:.2f}"
    o = d["관측소"]
    o["문장"] = f"{o['이름']} 부이 ({o['거리km']:.1f}km)" + (
        f" · {d['주차이름']} 평년 수온 {o['평년수온']:.1f}℃" if o["평년수온"] is not None else "")
    o["최근문장"] = (None if o["최근시작일"] is None else
                  f"가장 최근 관측 ({o['최근시작일']:%Y-%m-%d} 주): 수온 {o['최근수온']:.1f}℃")
    d["곡선"] = s.곡선(beach_id)[["월", "주차", "주차명", "통합출현율", "노무라", "보름달", "기타", "평년수온"]]
    return js(d)


@app.get("/api/top")
def top(date: str = "", k: int = 4):
    날짜, k = 날짜_읽기(date), 기간_확인(k)
    t = svc().상위(예측표(날짜), k)
    대상 = 대상주(날짜, k)
    rows = [] if t.empty else [
        {"해수욕장ID": r.해수욕장ID, "해수욕장명": r.해수욕장명, "시군명": r.시군명, "권역명": r.권역명,
         "값": r.예측위험지수, "상한전": r.정렬지수, "표시": r.표시, "방식": r.방식,
         "등급": 등급_구하기(r.예측위험지수)[0], "색": 등급_구하기(r.예측위험지수)[1]} for r in t.itertuples()]
    return js({"제목": f"{k}주 뒤 · {대상['이름']} ({대상['범위']}) 위험 지수 상위 10곳", "목록": rows})


@app.get("/api/health")
def health():
    """서버가 살아 있는지 확인용 (배포 서비스의 상태 점검)"""
    return {"ok": True}


@app.post("/api/reload")
def reload():
    # 외부에 공개되므로 너무 자주 누르면 무시 (60초에 한 번)
    if (dt.datetime.now() - _state["불러온시각"]).total_seconds() >= 60:
        _load()
    return meta()


@app.get("/api/sql")
def sql():
    s = svc()
    return {"설명": "앱을 시작할 때 아래 SQL로 테이블·뷰를 한 번 읽어 오고, 이후 클릭·검색은 읽어 온 자료에서 바로 찾아요. "
                  "1·2·4주 뒤 값은 최근 2주 안에 주간보고가 있으면 그 보고를 넣은 예측(v_해수욕장예측위험도), "
                  f"없으면 v_학습데이터의 {s.보고연도} 주간보고로 계산한 권역 x 월 x 주차별 대량출현 비율에 "
                  "v_해수욕장가중치의 가중치를 곱한 평년 기준 전망이에요.",
            "목록": [{"이름": k, "sql": v.strip() + ";"} for k, v in SQL.items()]}
