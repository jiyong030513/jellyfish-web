"""2024년 6월 이후 해파리 주간보고(PDF)를 받아 권역별 출현율을 뽑고 DB에 추가한다.

배경: 국립수산과학원 OpenAPI는 2024년 5월까지만 출현율 숫자(jellyDetail2)를 주고,
      그 뒤로는 주간보고를 PDF 첨부파일로만 올린다. PDF의 "붙임 3. 각 지역별 해파리 출현율(%)" 표를 읽는다.

사용법 (web 폴더에서):
    pip install pdfplumber requests
    python collect_reports.py
    → PDF 받기·표 추출 → 결과 CSV 저장 → DB에 자동 추가 (인증키·비밀번호는 db.py)

결과 파일 (추가수집 폴더):
    pdf/                        받은 PDF 원본
    06_주간보고_추가.csv        추가된 주간보고
    08_출현기록_추가.csv        추가된 출현기록
    수집로그.csv                보고서별 처리 결과 (성공/실패 이유)

권역 처리: 2025년부터 보고서가 전남을 하나로(전남, 전남광주) 적는다.
           우리 DB는 전남(서해)·전남(남해)로 나뉘어 있으므로 같은 값을 두 권역에 모두 넣는다.
"""
import datetime as dt
import io
import json
import os
import re
import sys
import time

import pandas as pd
import pdfplumber
import pymysql
import requests

from db import DB, NIFS_KEY

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "추가수집")
PDF_DIR = os.path.join(OUT, "pdf")
API = "https://www.nifs.go.kr/OpenAPI_json"
시작 = dt.date(2024, 6, 1)                       # 이 날짜 이후 등록된 주간보고만 수집
UA = {"User-Agent": "Mozilla/5.0 (DB class project)"}

권역_변환 = {
    "인천": ["인천"], "경기": ["경기"], "충남": ["충남"], "전북": ["전북"],
    "전남": ["전남(서해)", "전남(남해)"], "전남광주": ["전남(서해)", "전남(남해)"],
    "전남(서해)": ["전남(서해)"], "전남(남해)": ["전남(남해)"],
    "경남": ["경남"], "부산": ["부산"], "울산": ["울산"], "경북": ["경북"],
    "강원": ["강원"], "강원도": ["강원"], "제주": ["제주"], "제주도": ["제주"],
}
어종 = ["노무라입깃해파리", "보름달물해파리", "기타해파리"]
행_패턴 = re.compile(r"^\s*(전남\(서해\)|전남\(남해\)|전남광주|강원도|제주도|인천|경기|충남|전북|전남|경남|부산|울산|경북|강원|제주)"
                   r"\s+(\S+)\s+(\S+)\s+(\S+)\s*$")
기간_패턴 = re.compile(r"(20\d\d)\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*[~∼]\s*(?:(20\d\d)\.\s*)?(\d{1,2})\.\s*(\d{1,2})")
인원_패턴 = re.compile(r"응답자\s*\(\s*([\d,]+)\s*명|([\d,]{2,6})\s*명\s*중")   # "응답자(294명) 중", "240명 중"


# ---------------------------------------------------------------- API
def api(params):
    r = requests.get(API, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    for enc in ("utf-8", "cp949"):
        try:
            return json.loads(r.content.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
    raise ValueError(f"응답을 읽을 수 없어요: {r.text[:200]}")


def items(js):
    it = (js.get("body") or {}).get("item") or []
    return it if isinstance(it, list) else [it]


def 주간보고_목록(key):
    """jellyList를 1년 단위로 나눠 조회 (API 제한: 최대 1년)"""
    out, s, today = [], 시작, dt.date.today()
    while s <= today:
        e = min(today, s.replace(year=s.year + 1) - dt.timedelta(days=1))
        js = api({"id": "jellyList", "key": key, "sdate": s.strftime("%Y%m%d"), "edate": e.strftime("%Y%m%d")})
        code = (js.get("header") or {}).get("resultCode")
        if code not in (None, "00"):
            raise ValueError(f"API 오류: {js.get('header')}  (인증키를 확인하세요)")
        out += items(js)
        s = e + dt.timedelta(days=1)
        time.sleep(0.3)
    rows = []
    for it in out:
        제목 = str(it.get("board_subject", ""))
        if str(it.get("gbn", "0")) != "0" or "주간보고" not in 제목:
            continue
        code = str(it.get("srcode") or it.get("board_idx") or "").strip()
        rows.append({"보고코드": code, "제목": 제목.strip(), "등록일": str(it.get("inpt_date", ""))})
    if rows and all(len(r["보고코드"]) < 10 for r in rows):
        print("[중단] 목록에 보고서 코드(srcode)가 없어요. 아래 출력을 캡처해서 보내 주세요:")
        print(json.dumps(out[:3], ensure_ascii=False, indent=2))
        sys.exit(1)
    return pd.DataFrame(rows).drop_duplicates("보고코드")


def 첨부_주소(key, code):
    for api_id in ("jellyDetail", "jellyDetail2"):
        try:
            js = api({"id": api_id, "key": key, "srcode": code})
        except Exception:
            continue
        for it in items(js):
            files = it.get("item2") or []
            files = files if isinstance(files, list) else [files]
            for f in files:
                url = (f or {}).get("board_file")
                if url:
                    return url.strip()
    return None


def pdf_받기(url, path):
    if os.path.exists(path):
        return open(path, "rb").read()
    ids = re.findall(r"FILE_ID=([\w\-]+)", url)
    후보 = [url] + ([f"https://www.nifs.go.kr/cmmnFile/fileDownloadStat.do?FILE_ID={ids[0]}"] if ids else [])
    for u in 후보:
        r = requests.get(u, headers=UA, timeout=60)
        if r.ok and r.content[:4] == b"%PDF":
            open(path, "wb").write(r.content)
            return r.content
    return None


# ---------------------------------------------------------------- PDF 표 읽기
def 표_읽기(data):
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    m = 기간_패턴.search(text[:600])
    if not m:
        raise ValueError("조사기간을 찾지 못함")
    y1, m1, d1, y2, m2, d2 = m.groups()
    s = dt.date(int(y1), int(m1), int(d1))
    y2 = int(y2) if y2 else (s.year + 1 if int(m2) < s.month else s.year)
    e = dt.date(y2, int(m2), int(d2))
    n = 인원_패턴.search(text)
    응답 = int((n.group(1) or n.group(2)).replace(",", "")) if n else None

    i = text.find("붙임 3")
    if i < 0:
        i = text.find("지역별 해파리 출현율")
    if i < 0:
        raise ValueError("'각 지역별 해파리 출현율' 표가 없음")
    값 = {}
    for line in text[i:i + 3000].splitlines():
        mm = 행_패턴.match(line)
        if not mm:
            continue
        nums = []
        for v in mm.groups()[1:]:
            v = v.replace("%", "")
            if v in ("-", "–", "−", ""):
                nums.append(None)
            else:
                try:
                    x = float(v)
                    nums.append(x if 0 <= x <= 100 else None)
                except ValueError:
                    nums = None
                    break
        if nums:
            for 권역 in 권역_변환[mm.group(1)]:
                값.setdefault(권역, nums)
    if len(값) < 10:
        raise ValueError(f"표에서 권역을 {len(값)}개만 찾음")
    return s, e, 응답, 값


# ---------------------------------------------------------------- 실행
def main():
    os.makedirs(PDF_DIR, exist_ok=True)
    key = NIFS_KEY

    conn = pymysql.connect(**DB)
    with conn.cursor() as c:
        c.execute("SELECT 보고코드, 시작일 FROM 주간보고")
        기존 = c.fetchall()
    conn.close()
    기존코드 = {r[0] for r in 기존}
    기존시작일 = {r[1] for r in 기존}

    목록 = 주간보고_목록(key)
    print(f"[목록] {시작} 이후 주간보고 {len(목록)}건")

    보고행, 출현행, 로그 = [], [], []
    for k, r in enumerate(목록.sort_values("등록일").itertuples(), 1):
        상태 = "성공"
        try:
            if r.보고코드 in 기존코드:
                raise ValueError("이미 DB에 있음")
            url = 첨부_주소(key, r.보고코드)
            if not url:
                raise ValueError("첨부파일 없음")
            data = pdf_받기(url, os.path.join(PDF_DIR, f"{r.보고코드}.pdf"))
            if not data:
                raise ValueError("PDF가 아님 (hwp 등)")
            s, e, 응답, 값 = 표_읽기(data)
            if s in 기존시작일 or any(b["시작일"] == s for b in 보고행):
                raise ValueError(f"같은 조사기간({s}) 보고가 이미 있음")
            보고행.append({"보고코드": r.보고코드, "시작일": s, "종료일": e, "조사인원": None, "응답인원": 응답})
            for 권역, nums in 값.items():
                for 종, v in zip(어종, nums):
                    출현행.append({"보고코드": r.보고코드, "권역명": 권역, "어종명": 종, "출현율": v})
        except Exception as ex:
            상태 = f"건너뜀: {ex}"
        로그.append({"보고코드": r.보고코드, "제목": r.제목, "등록일": r.등록일, "결과": 상태})
        print(f"  ({k}/{len(목록)}) {r.제목} → {상태}")
        time.sleep(0.2)

    pd.DataFrame(로그).to_csv(os.path.join(OUT, "수집로그.csv"), index=False, encoding="utf-8-sig")
    B, O = pd.DataFrame(보고행), pd.DataFrame(출현행)
    if B.empty:
        print("추가할 보고가 없어요. 추가수집/수집로그.csv를 확인하세요.")
        return
    B.to_csv(os.path.join(OUT, "06_주간보고_추가.csv"), index=False, encoding="utf-8-sig")
    O.to_csv(os.path.join(OUT, "08_출현기록_추가.csv"), index=False, encoding="utf-8-sig")
    print(f"\n[추출] 주간보고 {len(B)}건 ({B['시작일'].min()} ~ {B['시작일'].max()}), 출현기록 {len(O)}행")

    nn = lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else v
    conn = pymysql.connect(**DB, autocommit=False)
    try:
        with conn.cursor() as c:
            c.executemany("INSERT INTO 주간보고 (보고코드, 시작일, 종료일, 조사인원, 응답인원) VALUES (%s, %s, %s, %s, %s)",
                          [(b.보고코드, b.시작일, b.종료일, None, nn(b.응답인원)) for b in B.itertuples()])
            c.executemany("INSERT INTO 출현기록 (보고코드, 권역명, 어종명, 출현율) VALUES (%s, %s, %s, %s)",
                          [(o.보고코드, o.권역명, o.어종명, nn(o.출현율)) for o in O.itertuples()])
        conn.commit()
        print(f"[DB] 주간보고 {len(B)}건, 출현기록 {len(O)}행 추가 완료")
        print("다음: 효섭 모델 다시 실행 (서비스_로지스틱.py 전체 --db --저장) → 웹에서 'DB 다시 불러오기'")
    except Exception:
        conn.rollback()
        print("[DB] 오류가 나서 전부 취소했어요.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
