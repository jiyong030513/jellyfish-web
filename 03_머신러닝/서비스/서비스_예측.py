"""05_서비스_로지스틱.ipynb와 같은 로직의 자동화용 스크립트 (노트북은 보고서용으로 그대로 둠)

설정 고정: SOURCE="db", SAVE_TO_DB=True, USE_SAVED_MODEL=True
  → DB의 v_학습데이터를 읽고, 저장된 모델(모델/logistic_v1.joblib)로 예측만 해서 권역예측 테이블에 저장

사용법 (어느 폴더에서 실행해도 됨):
    python 서비스_예측.py              예측 → 결과/권역예측_Logistic_v1.csv 저장 → DB 권역예측 저장
    python 서비스_예측.py --dry-run    예측만 하고 DB에 저장하지 않음
                                       (CSV도 결과/권역예측_Logistic_v1_dryrun.csv에 따로 저장 → 기존 결과를 덮어쓰지 않음)
    python 서비스_예측.py --학습       다시 학습한 뒤 예측 (1년에 한 번 재학습용)
                                       기존 모델은 모델/logistic_v1_백업_YYYYMMDD_HHMM.joblib으로 복사해 둠

DB 접속 정보는 02_웹_수집/db.py에서 가져옴 (비밀번호를 여기에 쓰지 않음)
"""
import argparse
import os
import shutil
import sys
from datetime import datetime
from decimal import Decimal

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PROJECT, "02_웹_수집"))
from db import DB as DB_INFO  # noqa: E402  (02_웹_수집/db.py: 비밀번호는 여기 한 곳에만)

pd.set_option("display.width", 200)

# ---------- 실행 방법 (자동화용 고정) ----------
SOURCE = "db"
SAVE_TO_DB = True
USE_SAVED_MODEL = True

# ---------- 고정 설정 (노트북과 동일) ----------
MODEL_NAME = "Logistic_v1"
MODEL_PATH = os.path.join(HERE, "모델", "logistic_v1.joblib")
PRED_PATH = os.path.join(HERE, "결과", f"권역예측_{MODEL_NAME}.csv")

FEATURES = [
    "통합", "통합_1주전", "통합_2주전", "통합_변화_1주",
    "연중주차",
    "수온_주평균", "수온_평년차", "수온_변화_1주",
    "기온_주평균", "풍속_주평균", "유의파고_주평균",
]
BEST_C = {1: 0.01, 2: 0.3, 4: 0.01}
TARGET = "타깃_급증_{k}주후"
THRESHOLD = 50.0
EXCLUDE_SPLIT = ["추가(2024)"]
FIT_ON = "train"
TRAIN_RATIO = 0.7
PREDICT_ALREADY_HIGH = False
SENSOR_CHECK = [{"관측소ID": 22106, "시작일": ["2018-11-30", "2018-12-07"]}]
TEMP_COLS = ["수온_주평균", "수온_평년차"]
COMPARE_PATH = os.path.join(os.path.dirname(HERE), "결과", "모델비교_결과표.csv")


# ---------- 설정 확인: 01_모델비교 결과와 고정값이 같은지 ----------
def 설정_확인():
    if os.path.exists(COMPARE_PATH):
        cmp = pd.read_csv(COMPARE_PATH)
        final = cmp.loc[cmp["최종"] == "★", "모델"].unique()
        chosen = (cmp[(cmp["모델"] == "Logistic") & (cmp["세트"] == "test")]
                  .set_index("예측기간")["하이퍼파라미터"].map(lambda t: eval(t)["C"]).to_dict())
        ok = list(final) == ["Logistic"] and all(abs(chosen[k] - BEST_C[k]) < 1e-12 for k in BEST_C)
        print(f"01 결과: 최종 모델 {list(final)}, C {chosen}")
        print("✅ 고정값이 01 결과와 같음" if ok else "⚠️ 고정값이 01 결과와 다름 → BEST_C를 01 결과로 고칠 것")
    else:
        print("01_모델비교 결과 파일이 없어 확인을 건너뜀")


# ---------- DB 접속 ----------
def connect():
    """트랜잭션을 직접 관리하도록 autocommit을 끈 연결을 돌려준다."""
    import pymysql
    return pymysql.connect(**DB_INFO, autocommit=False)


# ---------- [코드 ②] DB에서 학습 데이터 꺼내기 ----------
SQL_SELECT = """
SELECT *
FROM v_학습데이터
WHERE 시작일 >= %s
ORDER BY 권역명, 시작일
"""


def 학습데이터_조회(conn, 시작일="1900-01-01"):
    with conn.cursor() as cur:
        cur.execute(SQL_SELECT, (시작일,))
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["시작일"] = pd.to_datetime(df["시작일"])
    return df


# ---------- [코드 ③] 예측 결과를 권역예측 테이블에 저장 ----------
PRED_COLS = ["권역명", "기준일", "예측기간", "모델명", "급증확률"]
SQL_DELETE = "DELETE FROM 권역예측 WHERE 모델명 = %s"
SQL_INSERT = "INSERT INTO 권역예측 (권역명, 기준일, 예측기간, 모델명, 급증확률) VALUES (%s, %s, %s, %s, %s)"


def 권역예측_저장(conn, pred):
    missing = [c for c in PRED_COLS if c not in pred.columns]
    if missing:
        raise ValueError(f"예측 결과에 다음 열이 없습니다: {missing}")
    if not pred["급증확률"].between(0, 1).all():
        raise ValueError("급증확률은 0~1 사이여야 합니다")
    if not pred["예측기간"].isin([1, 2, 4]).all():
        raise ValueError("예측기간은 1, 2, 4 중 하나여야 합니다")

    rows = [(str(r.권역명), str(r.기준일)[:10], int(r.예측기간), str(r.모델명), round(float(r.급증확률), 4))
            for r in pred[PRED_COLS].itertuples(index=False)]
    try:
        with conn.cursor() as cur:
            for m in sorted(pred["모델명"].unique()):
                cur.execute(SQL_DELETE, (m,))
            cur.executemany(SQL_INSERT, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return len(rows)


# ---------- 전처리 ----------
def preprocess(df):
    need = ["권역명", "시작일"] + [c for c in FEATURES if c != "수온_변화_1주"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"데이터에 다음 열이 없습니다: {missing}")
    df = df.sort_values(["권역명", "시작일"]).reset_index(drop=True)
    for e in SENSOR_CHECK:
        m = (df["관측소ID"] == e["관측소ID"]) & df["시작일"].isin(pd.to_datetime(e["시작일"]))
        left = df.loc[m, TEMP_COLS].notna().any(axis=1).sum()
        print(f"⚠️ 경고: 센서 고장 구간 수온 {left}행 남아 있음 → DB 전처리 확인 필요" if left
              else f"확인: 센서 고장 구간 수온 결측 처리됨 ({m.sum()}행)")
    g = df.groupby("권역명")
    gap = (df["시작일"] - g["시작일"].shift()).dt.days
    df["수온_변화_1주"] = np.where(gap.between(4, 10), df["수온_주평균"] - g["수온_주평균"].shift(), np.nan)
    return df


# ---------- 학습 ----------
def build(C):
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=C, class_weight="balanced", max_iter=2000),
    )


def train(df):
    data = df[~df["분할"].isin(EXCLUDE_SPLIT)] if "분할" in df.columns else df
    if FIT_ON == "train":
        counts = data["시작일"].value_counts().sort_index()
        cum = data["시작일"].map(counts.cumsum()) / len(data)
        data = data[cum <= TRAIN_RATIO]

    bundle = {"모델명": MODEL_NAME, "변수": FEATURES, "C": BEST_C, "학습범위": FIT_ON,
              "학습일시": datetime.now().strftime("%Y-%m-%d %H:%M"), "모델": {}, "학습정보": {}}
    for k, C in BEST_C.items():
        y_col = TARGET.format(k=k)
        d = data.dropna(subset=[y_col])
        model = build(C).fit(d[FEATURES], d[y_col].astype(int))
        bundle["모델"][k] = model
        bundle["학습정보"][k] = {"행수": len(d), "급증수": int(d[y_col].sum()),
                              "기간": f"{d['시작일'].min().date()} ~ {d['시작일'].max().date()}"}
        coef = pd.Series(model.named_steps["logisticregression"].coef_[0], index=FEATURES)
        bundle["학습정보"][k]["계수"] = coef.round(4).to_dict()

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if os.path.exists(MODEL_PATH):                       # 기존 모델은 지우지 않고 백업
        bak = MODEL_PATH.replace(".joblib", f"_백업_{datetime.now():%Y%m%d_%H%M}.joblib")
        shutil.copy2(MODEL_PATH, bak)
        print(f"[백업] 기존 모델 → {bak}")
    joblib.dump(bundle, MODEL_PATH)
    print(f"[학습] {MODEL_NAME} 저장 → {MODEL_PATH}  (학습범위: {FIT_ON})")
    for k, info in bundle["학습정보"].items():
        print(f"  {k}주 뒤: C={BEST_C[k]}, {info['행수']}행 (급증 {info['급증수']}건), {info['기간']}")
    return bundle


# ---------- 실행 ----------
def main():
    global USE_SAVED_MODEL, SAVE_TO_DB
    p = argparse.ArgumentParser(description="권역별 해파리 급증 예측 (로지스틱, 05 노트북과 같은 로직)")
    p.add_argument("--학습", action="store_true", help="저장된 모델 대신 다시 학습 (1년에 한 번)")
    p.add_argument("--dry-run", action="store_true", help="DB에 저장하지 않고 결과만 출력")
    a = p.parse_args()
    if a.학습:
        USE_SAVED_MODEL = False
    if a.dry_run:
        SAVE_TO_DB = False
    pred_path = PRED_PATH.replace(".csv", "_dryrun.csv") if a.dry_run else PRED_PATH

    설정_확인()

    # 데이터 읽기 (SOURCE = "db", 코드 ②)
    conn = connect()
    try:
        raw = 학습데이터_조회(conn)
    finally:
        conn.close()
    print(f"[데이터] {len(raw)}행, {raw['시작일'].min().date()} ~ {raw['시작일'].max().date()} (출처: {SOURCE})")

    df = preprocess(raw)

    if USE_SAVED_MODEL:
        bundle = joblib.load(MODEL_PATH)
        print(f"[불러오기] {MODEL_PATH} (학습일시 {bundle['학습일시']}, 학습범위 {bundle['학습범위']})")
    else:
        bundle = train(df)

    # 예측 → CSV 저장
    if bundle["변수"] != FEATURES:
        raise ValueError("저장된 모델의 입력 변수가 현재 설정과 다릅니다. 다시 학습하세요.")
    target = df if PREDICT_ALREADY_HIGH else df[df["통합"] < THRESHOLD]

    out = []
    for k, model in bundle["모델"].items():
        out.append(pd.DataFrame({
            "권역명": target["권역명"].values,
            "기준일": target["시작일"].dt.strftime("%Y-%m-%d").values,
            "예측기간": k,
            "모델명": bundle["모델명"],
            "급증확률": model.predict_proba(target[FEATURES])[:, 1].round(4),
        }))
    pred = pd.concat(out).sort_values(["예측기간", "기준일", "권역명"]).reset_index(drop=True)

    os.makedirs(os.path.dirname(pred_path), exist_ok=True)
    pred.to_csv(pred_path, index=False, encoding="utf-8-sig")
    print(f"[예측] {len(target)}개 권역·주 × {len(bundle['모델'])}기간 = {len(pred)}행 → {pred_path}")
    print(f"  (현재 통합 {THRESHOLD:.0f}% 이상이라 급증 예측 대상이 아닌 {len(df) - len(target)}개 권역·주는 제외)")
    latest = pred[pred["기준일"] == pred["기준일"].max()]
    print(f"가장 최근 기준일 {latest['기준일'].iloc[0]} 예측:")
    print(latest.pivot(index="권역명", columns="예측기간", values="급증확률").to_string())

    # DB 저장 (코드 ③)
    if SAVE_TO_DB:
        conn = connect()
        try:
            n = 권역예측_저장(conn, pred)
        finally:
            conn.close()
        print(f"[저장] 권역예측 테이블에 {n}행 저장 (모델명 {MODEL_NAME})")
    else:
        print("[dry-run] DB 저장은 건너뜀")


if __name__ == "__main__":
    main()
