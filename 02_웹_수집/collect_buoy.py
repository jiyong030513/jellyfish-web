"""기상청 해양기상부이 시간자료를 받아 주간 관측자료로 집계하고 DB에 추가·갱신한다.

API: 기상청 API허브 kma_buoy2.php (텍스트, 쉼표 구분, #은 주석)
지점: 22101 덕적도, 22103 거문도, 22104 거제도, 22105 동해, 22106 포항, 22108 외연도, 22183 신안

사용법 (02_웹_수집 폴더에서):
    python collect_buoy.py --dry-run                         계산만 하고 DB에 쓰지 않음 (결과 미리보기)
    python collect_buoy.py --dry-run --start 2025-12-01 --end 2025-12-31   기존 주간값과 비교
    python collect_buoy.py                                   백업 → 수집 → DB에 INSERT/UPDATE

수집 기간: 지점별 DB 관측자료의 MAX(시작일) 주부터 오늘까지.
           단, 최초 구축 자료(2025-12-31까지)는 다시 계산하지 않음 → 지금은 2026-01-01부터.

주간 집계 규칙 (최초 구축 05_관측자료와 같음)
  - 정각(분=00) 자료만 사용 → 1시간 간격
  - 바람(풍향·풍속·최대돌풍)은 센서1(WD1·WS1·WS1_GST)만 사용. 센서2로 대체하지 않음 (학습 자료와 같은 기준)
  - 한 주 = 월~일. 1월 1일이 주 중간이면 1월 1일부터 새 주 (연도를 넘는 주를 자름)
  - 시작일 = 그 주 첫날, 연도 = 시작일 연도, 주차 = 1월 1일이 든 주를 1주로 하는 순번
  - 평균: 풍속·기압·습도·기온·수온·유의파고·평균파고·파주기 / 최댓값: 최대돌풍·최대파고
  - 풍향·파향: 각도 평균 (sin·cos 평균 → atan2, 0~360)
  - 이상값: 돌풍 60 m/s 초과 시간값 제외, 습도 10% 미만 시간값 제외(주간값이 10% 미만이어도 NULL)
  - 물리적 범위 밖 시간값 제외 (파고 0~25 m, 파주기 0~30 s, 기압 900~1080 hPa, 기온 -30~45, 수온 -3~35 ℃ 등)
  - 결측(-99): NULL. 소수점 3자리 반올림 (풍향·파향 2자리)

결과 파일 (추가수집/buoy 폴더):
    원본/지점_YYYYMM.csv      받은 시간자료 원본 (지점·월별, 10분/30분 간격 그대로)
    05_관측자료_추가.csv       이번에 계산한 주간값
    수집로그.csv               지점·월별 요청 결과
"""
import argparse
import datetime as dt
import io
import os
import sys
import time

import numpy as np
import pandas as pd
import pymysql
import requests

from db import DB, KMA_KEY, 백업

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "추가수집", "buoy")
RAW = os.path.join(OUT, "원본")
API = "https://apihub.kma.go.kr/api/typ01/url/kma_buoy2.php"

지점 = {22101: "덕적도", 22103: "거문도", 22104: "거제도", 22105: "동해",
        22106: "포항", 22108: "외연도", 22183: "신안"}
보호_종료 = dt.date(2025, 12, 31)        # 최초 구축 자료 범위. 이 날짜까지는 다시 계산하지 않음

열 = ["TM", "STN", "WD1", "WS1", "WS1_GST", "WD2", "WS2", "WS2_GST", "PA", "HM", "TA", "TW",
     "WH_MAX", "WH_SIG", "WH_AVE", "WP", "WO", "AQC", "MQC"]
숫자열 = 열[2:17]
평균열 = ["풍속", "기압", "습도", "기온", "수온", "유의파고", "평균파고", "파주기"]
최대열 = ["최대돌풍", "최대파고"]
각도열 = ["풍향", "파향"]
# 물리적 허용 범위: 밖이면 그 시간값은 결측 (정상 자료는 영향 없음. 2025-12 검증에서 최대파고 712 m 1건 걸러짐)
범위 = {"풍향": (0, 360), "파향": (0, 360), "풍속": (0, 60), "기압": (900, 1080), "기온": (-30, 45),
        "수온": (-3, 35), "최대파고": (0, 25), "유의파고": (0, 25), "평균파고": (0, 25), "파주기": (0, 30)}
DB열 = ["풍속", "풍향", "최대돌풍", "기압", "습도", "기온", "수온", "최대파고", "유의파고", "평균파고", "파주기", "파향"]


# ---------------------------------------------------------------- 주 계산
def 주_시작(d):
    """d가 속한 주의 첫날: 그 주 월요일, 단 1월 1일보다 앞서면 1월 1일"""
    return max(d - dt.timedelta(days=d.weekday()), dt.date(d.year, 1, 1))


def 주차(시작일):
    jan1 = dt.date(시작일.year, 1, 1)
    월1 = jan1 - dt.timedelta(days=jan1.weekday())
    월 = 시작일 - dt.timedelta(days=시작일.weekday())
    return (월 - 월1).days // 7 + 1


# ---------------------------------------------------------------- API
def 월_목록(시작, 끝):
    m = dt.date(시작.year, 시작.month, 1)
    while m <= 끝:
        nxt = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        yield max(m, 시작), min(nxt - dt.timedelta(days=1), 끝)
        m = nxt


def 요청(stn, s, e):
    """s~e(날짜) 시간자료 원본 DataFrame. 실패하면 3번까지 다시 시도"""
    params = dict(tm1=f"{s:%Y%m%d}0000", tm2=f"{e:%Y%m%d}2359", stn=stn, help=0, authKey=KMA_KEY)
    err = None
    for k in range(3):
        try:
            r = requests.get(API, params=params, timeout=120)
            r.raise_for_status()
            text = r.content.decode("euc-kr", errors="replace")
            if "#START7777" not in text:
                raise ValueError(f"예상과 다른 응답: {text[:200]!r}")
            lines = [ln.rstrip(",=").rstrip(",") for ln in text.splitlines()
                     if ln.strip() and not ln.startswith("#")]
            rows = [[v.strip() for v in ln.split(",")][:len(열)] for ln in lines]
            return pd.DataFrame(rows, columns=열) if rows else pd.DataFrame(columns=열)
        except Exception as ex:
            err = ex
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"요청 실패 ({stn} {s}~{e}): {err}")


def 시간자료(stn, s, e, 로그):
    """지점의 s~e 원본을 월별로 받아(완료된 달은 저장 파일 재사용) 하나로 합친다"""
    os.makedirs(RAW, exist_ok=True)
    today = dt.date.today()
    parts = []
    for ms, me in 월_목록(s, e):
        path = os.path.join(RAW, f"{stn}_{ms:%Y%m}.csv")
        월말 = dt.date(ms.year + (ms.month == 12), ms.month % 12 + 1, 1) - dt.timedelta(days=1)
        완료된달 = 월말 < today - dt.timedelta(days=1)
        if 완료된달 and os.path.exists(path):
            df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            상태 = "저장 파일 사용"
        else:
            ms_full = dt.date(ms.year, ms.month, 1)          # 원본 파일은 늘 한 달 전체로 저장
            df = 요청(stn, ms_full, min(월말, today))
            df.to_csv(path, index=False, encoding="utf-8-sig")
            상태 = "받음"
            time.sleep(0.3)
        로그.append({"지점": stn, "월": f"{ms:%Y-%m}", "행수": len(df), "결과": 상태})
        print(f"    {stn} {지점[stn]} {ms:%Y-%m}: {len(df)}행 ({상태})")
        parts.append(df)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=열)


# ---------------------------------------------------------------- 집계
def 정리(raw):
    """원본 → 정각 1시간 자료 (열 이름은 DB 기준)"""
    df = raw.copy()
    df["TM"] = pd.to_datetime(df["TM"], format="%Y%m%d%H%M", errors="coerce")
    df = df.dropna(subset=["TM"])
    df = df[df["TM"].dt.minute == 0].drop_duplicates("TM").sort_values("TM")
    for c in 숫자열:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df.loc[df[c] <= -99, c] = np.nan                 # -99, -99.0 → 결측
    h = pd.DataFrame({"TM": df["TM"].values})
    # 바람은 센서1만 사용 (최초 구축 자료·모델 학습 자료와 같은 기준). 센서1이 비면 그 시간은 결측
    h["풍향"] = df["WD1"].values
    h["풍속"] = df["WS1"].values
    h["최대돌풍"] = df["WS1_GST"].values
    for a, b in [("기압", "PA"), ("습도", "HM"), ("기온", "TA"), ("수온", "TW"), ("최대파고", "WH_MAX"),
                 ("유의파고", "WH_SIG"), ("평균파고", "WH_AVE"), ("파주기", "WP"), ("파향", "WO")]:
        h[a] = df[b].values
    h.loc[h["최대돌풍"] > 60, "최대돌풍"] = np.nan          # 돌풍 60 m/s 초과는 측정 오류
    h.loc[h["습도"] < 10, "습도"] = np.nan                  # 습도 10% 미만은 측정 오류
    for c, (lo, hi) in 범위.items():                       # 물리적으로 불가능한 값 (예: 최대파고 712 m)
        h.loc[(h[c] < lo) | (h[c] > hi), c] = np.nan
    return h


def 각도평균(x):
    x = x.dropna()
    if x.empty:
        return np.nan
    r = np.deg2rad(x)
    return round(float(np.rad2deg(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) % 360), 2)


def 주간집계(h, stn, 주들):
    """주들(시작일 목록)마다 한 행. 자료가 없는 주는 모든 값 NULL"""
    h = h.copy()
    h["시작일"] = h["TM"].dt.date.map(주_시작)
    rows = []
    for s in 주들:
        g = h[h["시작일"] == s]
        r = {"관측소ID": stn, "연도": s.year, "주차": 주차(s), "시작일": s, "시간자료수": len(g)}
        for c in 평균열:
            r[c] = round(float(g[c].mean()), 3) if g[c].notna().any() else np.nan
        for c in 최대열:
            r[c] = round(float(g[c].max()), 3) if g[c].notna().any() else np.nan
        for c in 각도열:
            r[c] = 각도평균(g[c])
        if pd.notna(r["습도"]) and r["습도"] < 10:
            r["습도"] = np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def 주_목록(s, e):
    out, d = [], 주_시작(s)
    while d <= e:
        out.append(d)
        nxt = d - dt.timedelta(days=d.weekday()) + dt.timedelta(days=7)
        if nxt.year != d.year:                            # 연도를 넘으면 1월 1일부터 새 주
            nxt = dt.date(d.year + 1, 1, 1)
        d = nxt
    return out


# ---------------------------------------------------------------- 실행
def 기존_관측():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as c:
            c.execute("SELECT 관측소ID, MAX(시작일) FROM 관측자료 GROUP BY 관측소ID")
            최종 = dict(c.fetchall())
            c.execute("SELECT MAX(CAST(SUBSTRING(관측ID, 2) AS UNSIGNED)) FROM 관측자료")
            최대번호 = c.fetchone()[0] or 0
            c.execute("SELECT 관측소ID, 시작일, 관측ID FROM 관측자료 WHERE 시작일 > %s", (보호_종료 - dt.timedelta(days=14),))
            기존ID = {(r[0], r[1]): r[2] for r in c.fetchall()}
    finally:
        conn.close()
    return 최종, 최대번호, 기존ID


def 적재(W, 최대번호, 기존ID):
    """한 트랜잭션으로 INSERT ... ON DUPLICATE KEY UPDATE. 관측ID는 기존 것을 유지"""
    nn = lambda v: None if pd.isna(v) else float(v)
    값, 새로, 갱신 = [], 0, 0
    for r in W.itertuples():
        key = (r.관측소ID, r.시작일)
        if key in 기존ID:
            oid = 기존ID[key]
            갱신 += 1
        else:
            최대번호 += 1
            oid = f"W{최대번호:05d}"
            새로 += 1
        값.append((oid, r.관측소ID, r.연도, r.주차, r.시작일, *[nn(getattr(r, c)) for c in DB열]))
    cols = ["관측ID", "관측소ID", "연도", "주차", "시작일"] + DB열
    sql = (f"INSERT INTO 관측자료 ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
           f"ON DUPLICATE KEY UPDATE {', '.join(f'{c} = VALUES({c})' for c in DB열)}")
    conn = pymysql.connect(**DB, autocommit=False)
    try:
        with conn.cursor() as c:
            c.executemany(sql, 값)
        conn.commit()
    except Exception:
        conn.rollback()
        print("[DB] 오류가 나서 전부 취소했어요 (rollback).")
        raise
    finally:
        conn.close()
    return 새로, 갱신


def run(dry_run=False, start=None, end=None, stations=None, backup=True):
    """수집·집계·적재. 결과 요약 dict를 돌려준다 (update_all.py에서 사용)"""
    os.makedirs(OUT, exist_ok=True)
    today = dt.date.today()
    end = end or today
    stations = stations or list(지점)
    최종, 최대번호, 기존ID = 기존_관측()

    로그, 결과 = [], []
    for stn in stations:
        if start:
            s = start
        else:
            s = max(최종.get(stn, 보호_종료), 보호_종료 + dt.timedelta(days=1))
            s = max(주_시작(s), 보호_종료 + dt.timedelta(days=1))
        if s > end:
            print(f"  {stn} {지점[stn]}: 새로 수집할 기간 없음")
            continue
        print(f"  {stn} {지점[stn]}: {s} ~ {end}")
        try:
            h = 정리(시간자료(stn, s, end, 로그))
        except Exception as ex:
            로그.append({"지점": stn, "월": "", "행수": 0, "결과": f"실패: {ex}"})
            print(f"    [실패] {ex} → 이 지점은 건너뜀")
            continue
        h = h[(h["TM"].dt.date >= s) & (h["TM"].dt.date <= end)]
        결과.append(주간집계(h, stn, 주_목록(s, end)))

    pd.DataFrame(로그).to_csv(os.path.join(OUT, "수집로그.csv"), index=False, encoding="utf-8-sig")
    if not 결과:
        print("계산된 주가 없어요.")
        return {"새로": 0, "갱신": 0, "주": 0, "실패지점": sum("실패" in l["결과"] for l in 로그)}
    W = pd.concat(결과, ignore_index=True)
    W.to_csv(os.path.join(OUT, "05_관측자료_추가.csv"), index=False, encoding="utf-8-sig")
    실패 = sum("실패" in l["결과"] for l in 로그)
    print(f"\n[계산] {len(W)}주 ({W['시작일'].min()} ~ {W['시작일'].max()}), 실패 지점 {실패}곳")

    if dry_run:
        with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 200):
            print(W[["관측소ID", "연도", "주차", "시작일", "시간자료수"] + DB열].to_string(index=False))
        print("\n[dry-run] DB에는 쓰지 않았어요.")
        return {"새로": 0, "갱신": 0, "주": len(W), "실패지점": 실패}

    if backup:
        print(f"[백업] {백업()}")
    새로, 갱신 = 적재(W, 최대번호, 기존ID)
    print(f"[DB] 관측자료 새로 추가 {새로}주, 다시 계산해 갱신 {갱신}주")
    return {"새로": 새로, "갱신": 갱신, "주": len(W), "실패지점": 실패}


def main():
    p = argparse.ArgumentParser(description="기상청 부이 시간자료 → 주간 관측자료")
    p.add_argument("--dry-run", action="store_true", help="계산만 하고 DB에 쓰지 않음")
    p.add_argument("--start", type=dt.date.fromisoformat, help="시작 날짜 (기본: 지점별 DB 마지막 주)")
    p.add_argument("--end", type=dt.date.fromisoformat, help="끝 날짜 (기본: 오늘)")
    p.add_argument("--stn", type=int, nargs="*", help="지점번호 (기본: 7곳 전부)")
    p.add_argument("--no-backup", action="store_true", help="mysqldump 백업 생략 (update_all.py가 이미 백업한 경우)")
    a = p.parse_args()
    if not a.dry_run and a.start and a.start <= 보호_종료:
        sys.exit(f"{보호_종료} 이전 주는 최초 구축 자료라 적재할 수 없어요 (--dry-run으로 비교만 가능)")
    run(a.dry_run, a.start, a.end, a.stn, backup=not a.no_backup)


if __name__ == "__main__":
    main()
