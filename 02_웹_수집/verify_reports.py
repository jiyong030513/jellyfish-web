"""collect_reports.py로 DB에 넣은 출현율이 PDF와 같은지 검증한다.

방법 1 (자동 대조): PDF 표를 수집 때와 다른 방법(글자 위치로 열 찾기)으로 다시 읽어 DB 값과 한 칸씩 비교
방법 2 (눈으로 확인): 보고서마다 PDF 표 페이지 사진과 DB 값을 나란히 놓은 검증.html 생성

사용법 (web 폴더에서): python verify_reports.py
결과: 추가수집/검증결과.csv, 추가수집/검증.html (브라우저로 열림)
"""
import base64
import io
import os
import webbrowser

import pandas as pd
import pdfplumber
import pymysql

from db import DB

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "추가수집")
PDF_DIR = os.path.join(OUT, "pdf")
권역들 = ["인천", "경기", "충남", "전북", "전남(서해)", "전남(남해)", "경남", "부산", "울산", "경북", "강원", "제주"]
PDF_권역 = {"전남광주": "전남", "강원도": "강원", "제주도": "제주"}
어종 = ["노무라입깃해파리", "보름달물해파리", "기타해파리"]


def 위치로_읽기(pdf):
    """표 페이지에서 글자 위치(x, y)로 행·열을 찾아 값을 읽는다 (수집 때의 '줄 단위 읽기'와 다른 방법)."""
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "지역별 해파리 출현율" not in text:
            continue
        words = page.extract_words(keep_blank_chars=False)
        머리 = [w for w in words if w["text"].startswith(("노무라", "보름달", "기타"))]
        머리 = sorted({w["text"][:3]: w for w in 머리}.values(), key=lambda w: w["x0"])[:3]
        if len(머리) < 3:
            continue
        열x = [(w["x0"] + w["x1"]) / 2 for w in 머리]
        값 = {}
        for w in words:
            name = PDF_권역.get(w["text"], w["text"])
            if name not in ("인천", "경기", "충남", "전북", "전남", "전남(서해)", "전남(남해)",
                            "경남", "부산", "울산", "경북", "강원", "제주") or w["top"] < 머리[0]["top"]:
                continue
            같은줄 = [v for v in words if abs(v["top"] - w["top"]) < 4 and v["x0"] > w["x1"]]
            row = [None, None, None]
            for v in 같은줄:
                cx = (v["x0"] + v["x1"]) / 2
                j = min(range(3), key=lambda i: abs(열x[i] - cx))
                t = v["text"].replace("%", "")
                try:
                    row[j] = float(t)
                except ValueError:
                    pass                      # "-" 등은 빈칸
            for 권역 in (["전남(서해)", "전남(남해)"] if name == "전남" else [name]):
                값.setdefault(권역, row)
        return page, 값
    return None, {}


def main():
    conn = pymysql.connect(**DB)
    db = pd.read_sql("""SELECT b.보고코드, b.시작일, b.종료일, b.응답인원, o.권역명, o.어종명, o.출현율
                        FROM 주간보고 b JOIN 출현기록 o ON b.보고코드 = o.보고코드
                        WHERE b.시작일 >= '2024-06-01'""", conn)
    conn.close()
    db["출현율"] = db["출현율"].astype(float)
    보고 = db.drop_duplicates("보고코드").sort_values("시작일")
    print(f"[DB] 2024-06 이후 주간보고 {len(보고)}건, 출현기록 {len(db)}행")

    결과, html = [], []
    for r in 보고.itertuples():
        path = os.path.join(PDF_DIR, f"{r.보고코드}.pdf")
        if not os.path.exists(path):
            결과.append({"보고코드": r.보고코드, "시작일": r.시작일, "결과": "PDF 없음", "다른칸": ""})
            continue
        d = db[db["보고코드"] == r.보고코드].set_index(["권역명", "어종명"])["출현율"]
        with pdfplumber.open(path) as pdf:
            page, 값 = 위치로_읽기(pdf)
            다른 = []
            for 권역 in 권역들:
                for j, 종 in enumerate(어종):
                    a = 값.get(권역, [None] * 3)[j]
                    b = d.get((권역, 종))
                    b = None if b is None or pd.isna(b) else float(b)
                    if (a is None) != (b is None) or (a is not None and abs(a - b) > 0.05):
                        다른.append(f"{권역} {종[:3]} PDF={a} DB={b}")
            img = ""
            if page is not None:
                buf = io.BytesIO()
                page.to_image(resolution=110).original.save(buf, format="PNG")
                img = base64.b64encode(buf.getvalue()).decode()
        상태 = "일치" if not 다른 and 값 else ("표 못 찾음" if not 값 else f"불일치 {len(다른)}칸")
        결과.append({"보고코드": r.보고코드, "시작일": r.시작일, "결과": 상태, "다른칸": " / ".join(다른)})

        표 = d.unstack("어종명").reindex(index=권역들, columns=어종)
        표.columns = ["노무라", "보름달", "기타"]
        표.index.name = None
        색 = "#2E9E5B" if 상태 == "일치" else "#D7263D"
        html.append(f"<section><h3>{r.시작일} ~ {r.종료일} · 보고코드 {r.보고코드} · 응답 {r.응답인원 or '-'}명 · "
                    f"<span style='color:{색}'>{상태}</span></h3><div class='row'>"
                    f"<img src='data:image/png;base64,{img}'>"
                    f"<div><b>DB에 들어간 값</b>{표.to_html(na_rep='-', float_format=lambda x: f'{x:.1f}')}"
                    f"<p class='diff'>{'<br>'.join(다른)}</p></div></div></section>")

    R = pd.DataFrame(결과)
    R.to_csv(os.path.join(OUT, "검증결과.csv"), index=False, encoding="utf-8-sig")
    print(R["결과"].value_counts().to_string())
    if (R["결과"] != "일치").any():
        print("\n[확인 필요]")
        print(R[R["결과"] != "일치"].to_string(index=False))

    page = ("<!doctype html><meta charset='utf-8'><title>주간보고 검증</title><style>"
            "body{font-family:'Malgun Gothic',sans-serif;margin:24px;background:#fff;color:#222}"
            "section{border-bottom:1px solid #ddd;padding:12px 0}.row{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}"
            "img{max-width:520px;border:1px solid #ccc}table{border-collapse:collapse;margin-top:6px}"
            "td,th{border:1px solid #bbb;padding:3px 10px;text-align:right}.diff{color:#D7263D}</style>"
            f"<h1>주간보고 PDF ↔ DB 검증</h1><p>{R['결과'].value_counts().to_dict()}</p>" + "".join(html))
    out = os.path.join(OUT, "검증.html")
    open(out, "w", encoding="utf-8").write(page)
    print(f"\n검증 페이지: {out}")
    webbrowser.open("file:///" + out.replace("\\", "/"))


if __name__ == "__main__":
    main()
