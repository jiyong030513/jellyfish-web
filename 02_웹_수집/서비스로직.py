"""해파리 위험도 조회의 데이터 조회·계산 로직 (화면과 무관)

React 웹의 FastAPI 서버(04_웹_react/backend/main.py)가 import해서 쓴다.

사용 예:
    from 서비스로직 import 전체_불러오기, 위험도서비스
    svc = 위험도서비스(전체_불러오기())          # DB를 한 번 읽어 메모리에 둠
    예측 = svc.예측표(dt.date(2026, 11, 8))      # 해수욕장 270곳 × 1·2·4주 뒤
    상세 = svc.상세("B111", dt.date(2026, 11, 8), 예측)

반환값은 DataFrame 또는 dict(문자열·숫자). 화면 문구도 여기서 만들어 두 화면이 같은 말을 쓰게 한다.
"""
import calendar
import datetime as dt

import pandas as pd

from db import 조회

# ---------------------------------------------------------------- SQL (시작할 때 한 번만 조회)
SQL = {
    "해수욕장": """
SELECT h.해수욕장ID, h.해수욕장명, g.시도명, g.시군명, g.권역명, h.위도, h.경도,
       h.길이, h.너비, h.관측소ID, o.관측소명, h.관측소거리km
FROM 해수욕장 h
JOIN 시군 g   ON h.시군ID = g.시군ID
JOIN 관측소 o ON h.관측소ID = o.관측소ID
ORDER BY g.시도명, g.시군명, h.해수욕장명""",
    "평년": """
SELECT 해수욕장ID, 월, 주차, 주차명, 노무라, 보름달, 기타, 통합출현율, 평년수온
FROM v_해수욕장주간위험도""",
    "가중치": """
SELECT 해수욕장ID, 주변응답수, 주변목격수, 권역목격률, 보정주변목격률, 가중치
FROM v_해수욕장가중치""",
    "보고": """
SELECT 권역명, 시작일, 통합
FROM v_학습데이터""",
    "예측": """
SELECT 해수욕장ID, 권역명, 기준일, 예측기간, 권역급증확률, 가중치, 예측위험지수, 정렬지수
FROM v_해수욕장예측위험도""",
    "관측": """
SELECT 관측소ID, 시작일, 수온
FROM 관측자료
WHERE 수온 IS NOT NULL""",
}

예측기간들 = (1, 2, 4)
최근기간 = pd.Timedelta(days=14)          # 선택한 날짜 14일 안에 주간보고가 있으면 모델 예측
대량기준 = 50                             # 대량출현: 통합 출현율 50% 이상


def 전체_불러오기():
    """SQL을 모두 실행해 {이름: DataFrame}으로 돌려준다 (날짜 열은 Timestamp)."""
    d = {k: 조회(v) for k, v in SQL.items()}
    for k, col in [("보고", "시작일"), ("예측", "기준일"), ("관측", "시작일")]:
        if not d[k].empty:
            d[k][col] = pd.to_datetime(d[k][col])
    return d


# ---------------------------------------------------------------- 등급·날짜·표시
등급 = [(0.6, "매우 높음", "#D7263D"), (0.4, "높음", "#F08C00"), (0.2, "보통", "#E6B800"), (0.0, "낮음", "#2E9E5B")]
회색 = "#9AA0A6"


def 없음(v):
    return v is None or pd.isna(v)


def 등급_구하기(v):
    """값(0~1) → (등급 이름, 색)"""
    if 없음(v):
        return "자료 없음", 회색
    for lo, name, color in 등급:
        if v >= lo:
            return name, color
    return "낮음", 등급[-1][2]


def 월_주차(d):
    """날짜 → (월, 주차). 1~7일=1주, 8~14일=2주, 15~21일=3주, 22일~말일=4주"""
    return d.month, min(4, (d.day - 1) // 7 + 1)


def 주차_범위(연, 월, 주차):
    """그 월·주차 칸의 (첫날, 마지막 날)"""
    s = dt.date(연, 월, (주차 - 1) * 7 + 1)
    e = dt.date(연, 월, calendar.monthrange(연, 월)[1]) if 주차 == 4 else s + dt.timedelta(days=6)
    return s, e


def 짧은날짜(d):
    return f"{d.month}/{d.day}"


def 한글날짜(d):
    return f"{d.year}년 {d.month}월 {d.day}일"


def pct(v):
    return "-" if 없음(v) else f"{v * 100:.1f}%"


def 지수_표시(지수, 상한전):
    """위험 지수 표시 문자열. 상한 1에서 잘렸으면 '100% (상한)'"""
    if 없음(지수):
        return "-"
    if not 없음(상한전) and 상한전 > 1:
        return "100% (상한)"
    return pct(지수)


def 대상주(날짜, k):
    """날짜에서 k주 뒤가 속한 월·주차 칸 정보"""
    t = 날짜 + dt.timedelta(weeks=k)
    m, w = 월_주차(t)
    s, e = 주차_범위(t.year, m, w)
    return {"월": m, "주차": w, "이름": f"{m}월 {w}주", "시작": s, "끝": e,
            "범위": f"{짧은날짜(s)}~{짧은날짜(e)}", "라벨": f"{k}주 뒤 · {m}월 {w}주 ({짧은날짜(s)}~{짧은날짜(e)})"}


# ---------------------------------------------------------------- 계산
def 시기확률표(보고):
    """권역 x 월 x 주차마다 '그 주에 대량출현(통합 50% 이상)이었던 비율'을 DB의 주간보고 전체로 계산.
    보고가 2건 미만인 칸은 같은 권역·같은 월 비율로 대신한다 (v_권역기준곡선과 같은 규칙)."""
    r = 보고.dropna(subset=["통합"]).copy()
    mid = r["시작일"] + pd.Timedelta(days=3)                       # 보고 주의 가운데 날짜
    r["월"], r["주차"] = mid.dt.month, ((mid.dt.day - 1) // 7 + 1).clip(upper=4)
    r["대량"] = (r["통합"] >= 대량기준).astype(int)
    칸 = r.groupby(["권역명", "월", "주차"])["대량"].agg(n="size", m="sum").reset_index()
    월 = r.groupby(["권역명", "월"])["대량"].agg(월n="size", 월m="sum").reset_index()
    return 칸.set_index(["권역명", "월", "주차"]), 월.set_index(["권역명", "월"])


class 위험도서비스:
    """DB에서 읽은 자료(전체_불러오기 결과)를 들고 화면에 필요한 값을 계산한다."""

    def __init__(self, D):
        self.D = D
        h = D["해수욕장"].copy()
        h["표시명"] = h["해수욕장명"] + " (" + h["시도명"] + " " + h["시군명"] + ")"
        self.해수욕장 = h
        self.B = h.set_index("해수욕장ID")
        self.칸표, self.월표 = 시기확률표(D["보고"])
        self.가중치표 = D["가중치"].set_index("해수욕장ID")["가중치"]
        b = D["보고"].dropna(subset=["통합"])["시작일"]
        self.보고시작, self.보고끝 = (b.min(), b.max()) if not b.empty else (None, None)

    # ---- 보고 기간 (설명 문구용)
    @property
    def 보고연도(self):
        """예: '2014~2026년'"""
        if self.보고시작 is None:
            return "주간보고"
        a, b = self.보고시작.year, self.보고끝.year
        return f"{a}년" if a == b else f"{a}~{b}년"

    @property
    def 보고기간_표시(self):
        """예: '2014.9 – 2026.10'"""
        if self.보고시작 is None:
            return "-"
        return f"{self.보고시작.year}.{self.보고시작.month} – {self.보고끝.year}.{self.보고끝.month}"

    # ---- 시기별 확률
    def 권역확률(self, 권역, 월, 주차):
        """(확률, 근거 문장)"""
        if not 5 <= 월 <= 12:
            return None, "해파리 시즌(5~12월)이 아님"
        if (권역, 월, 주차) in self.칸표.index:
            c = self.칸표.loc[(권역, 월, 주차)]
            if c.n >= 2:
                return c.m / c.n, f"{self.보고연도} {월}월 {주차}주 보고 {int(c.n)}건 중 대량출현 {int(c.m)}건"
        if (권역, 월) in self.월표.index:
            c = self.월표.loc[(권역, 월)]
            return c.월m / c.월n, f"{월}월 {주차}주 자료가 적어 {self.보고연도} {월}월 전체 보고 {int(c.월n)}건 중 대량출현 {int(c.월m)}건으로 계산"
        return None, "이 시기 보고가 없음"

    # ---- 1·2·4주 뒤 (해수욕장 전체)
    def 예측표(self, 날짜):
        """해수욕장 × 예측기간(1·2·4) 표.
        열: 해수욕장ID, 권역명, 예측기간, 대상, 라벨, 권역급증확률, 근거, 가중치, 정렬지수(상한 전), 예측위험지수(상한 1), 방식, 기준일
        방식 '모델' = 최근 14일 안 주간보고를 넣은 모델 예측, '평년' = 같은 시기 주간보고 비율로 계산한 평년 기준 전망"""
        rows = []
        for k in 예측기간들:
            t = 대상주(날짜, k)
            for r in self.해수욕장.itertuples():
                p, 근거 = self.권역확률(r.권역명, t["월"], t["주차"])
                w = float(self.가중치표.get(r.해수욕장ID, 1.0))
                rows.append(dict(해수욕장ID=r.해수욕장ID, 권역명=r.권역명, 예측기간=k, 대상=t["이름"], 라벨=t["라벨"],
                                 권역급증확률=p, 근거=근거, 가중치=w, 정렬지수=None if p is None else p * w,
                                 예측위험지수=None if p is None else min(1.0, p * w)))
        예측 = pd.DataFrame(rows)
        예측["방식"] = "평년"
        예측["기준일"] = pd.NaT

        기준시각 = pd.Timestamp(날짜)
        P = self.D["예측"]
        최근모델 = P[(P["기준일"] <= 기준시각) & (P["기준일"] > 기준시각 - 최근기간)]
        if not 최근모델.empty:
            mm = 최근모델.loc[최근모델.groupby(["해수욕장ID", "예측기간"])["기준일"].idxmax()].set_index(["해수욕장ID", "예측기간"])
            idx = pd.MultiIndex.from_arrays([예측["해수욕장ID"], 예측["예측기간"]])
            hit = idx.isin(mm.index)
            sub = mm.loc[idx[hit]]
            for col in ["권역급증확률", "예측위험지수", "정렬지수"]:
                예측.loc[hit, col] = sub[col].values
            예측.loc[hit, "근거"] = [f"{한글날짜(d)} 주간보고 기준 예측" for d in sub["기준일"]]
            예측.loc[hit, "기준일"] = sub["기준일"].values
            예측.loc[hit, "방식"] = "모델"
        return 예측

    def 최근보고(self, 날짜):
        기준시각 = pd.Timestamp(날짜)
        R = self.D["보고"]
        return R[(R["시작일"] <= 기준시각) & (R["시작일"] > 기준시각 - 최근기간)]

    # ---- 지도·목록
    def 지도색값(self, 날짜, 색기준, 예측기간, 예측=None):
        """{해수욕장ID: 값}. 색기준 '평년 출현율' 또는 '예측 위험 지수'"""
        if 색기준 == "평년 출현율":
            월, 주차 = 월_주차(날짜)
            p = self.D["평년"][(self.D["평년"]["월"] == 월) & (self.D["평년"]["주차"] == 주차)]
            return dict(zip(p["해수욕장ID"], p["통합출현율"]))
        예측 = self.예측표(날짜) if 예측 is None else 예측
        p = 예측[(예측["예측기간"] == 예측기간) & 예측["예측위험지수"].notna()]
        return dict(zip(p["해수욕장ID"], p["예측위험지수"]))

    def 상위(self, 예측, 예측기간, n=10):
        """k주 뒤 위험 지수 상위 n곳 (정렬은 상한 전 값)"""
        p = 예측[(예측["예측기간"] == 예측기간) & 예측["정렬지수"].notna()]
        if p.empty:
            return p
        top = (p.merge(self.해수욕장[["해수욕장ID", "해수욕장명", "시군명"]], on="해수욕장ID")
               .sort_values("정렬지수", ascending=False).head(n))
        top["표시"] = [지수_표시(a, b) for a, b in zip(top["예측위험지수"], top["정렬지수"])]
        return top

    def 곡선(self, 해수욕장ID):
        """5~12월 평년 출현율 (월·주차 순)"""
        P = self.D["평년"]
        return P[P["해수욕장ID"] == 해수욕장ID].sort_values(["월", "주차"])

    # ---- 해수욕장 상세
    def 상세(self, 해수욕장ID, 날짜, 예측=None):
        """오른쪽 상세 패널에 필요한 값 전부 (dict)"""
        예측 = self.예측표(날짜) if 예측 is None else 예측
        b = self.B.loc[해수욕장ID]
        월, 주차 = 월_주차(날짜)
        out = {"해수욕장ID": 해수욕장ID, "이름": b.해수욕장명, "시도명": b.시도명, "시군명": b.시군명,
               "권역명": b.권역명, "길이": b.길이, "너비": b.너비, "월": 월, "주차": 주차,
               "주차이름": f"{월}월 {주차}주",
               "위치": f"{b.시도명} {b.시군명} · {b.권역명} 권역 · 길이 {b.길이:,}m · 너비 {b.너비:,}m"}

        # ① 평년 출현율
        곡선 = self.곡선(해수욕장ID)
        이번주 = 곡선[(곡선["월"] == 월) & (곡선["주차"] == 주차)]
        if 이번주.empty:
            out["평년"] = None
        else:
            r = 이번주.iloc[0]
            name, color = 등급_구하기(r.통합출현율)
            out["평년"] = {"통합": r.통합출현율, "노무라": r.노무라, "보름달": r.보름달, "기타": r.기타,
                         "평년수온": r.평년수온, "등급": name, "색": color}

        # ② 1·2·4주 뒤
        pp = 예측[예측["해수욕장ID"] == 해수욕장ID].sort_values("예측기간")
        칸들 = []
        for x in pp.itertuples():
            name, color = 등급_구하기(x.예측위험지수)
            if 없음(x.예측위험지수):
                도움말 = x.근거
            else:
                도움말 = f"{b.권역명} 대량출현 확률 {pct(x.권역급증확률)} × 해수욕장 가중치 {x.가중치:.2f}"
                if not 없음(x.정렬지수) and x.정렬지수 > 1:
                    도움말 += f" = {pct(x.정렬지수)} → 상한 100%로 표시"
                도움말 += f"\n\n근거: {x.근거}"
            칸들.append({"예측기간": x.예측기간, "라벨": x.라벨, "대상": x.대상, "값": x.예측위험지수,
                       "상한전": x.정렬지수, "표시": 지수_표시(x.예측위험지수, x.정렬지수),
                       "등급": name, "색": color, "방식": x.방식, "도움말": 도움말})
        out["예측칸"] = 칸들
        모델 = pp[pp["방식"] == "모델"]
        if not 모델.empty:
            out["예측방식"] = "모델"
            out["예측제목"] = "1·2·4주 뒤 예측 위험 지수"
            out["예측안내"] = f"{한글날짜(모델['기준일'].iloc[0])} 주간보고 기준 예측이에요."
        else:
            out["예측방식"] = "평년"
            out["예측제목"] = "1·2·4주 뒤 평년 기준 전망"
            out["예측안내"] = (f"최근 2주 안에 주간보고가 없어 {self.보고연도} 같은 시기 주간보고로 계산한 평년 기준 전망이에요. "
                           f"{b.권역명} 권역이 그 주에 대량출현(통합 50% 이상)이었던 비율 × 해수욕장 가중치이며, "
                           "새 주간보고가 들어오면 예측으로 바뀌어요.")
        # 같은 주차 칸에 해당하는 기간 안내 (예: 1주 뒤와 2주 뒤가 모두 7월 4주)
        같은칸 = []
        for i in range(len(칸들) - 1):
            a, c = 칸들[i], 칸들[i + 1]
            if a["대상"] == c["대상"]:
                뒤 = " 평년 기준 값이 같아요." if out["예측방식"] == "평년" else ""
                같은칸.append(f"{a['예측기간']}주 뒤와 {c['예측기간']}주 뒤가 모두 {a['대상']}"
                           f"({대상주(날짜, a['예측기간'])['범위']}) 칸에 해당해요.{뒤}")
        out["같은칸안내"] = 같은칸

        # 최근 주간보고
        rb = self.최근보고(날짜)
        rb = rb[rb["권역명"] == b.권역명]
        if rb.empty:
            out["최근보고"] = None
        else:
            rb = rb.loc[rb["시작일"].idxmax()]
            out["최근보고"] = {"시작일": rb.시작일, "통합": rb.통합,
                           "대량출현중": (not 없음(rb.통합)) and rb.통합 >= 대량기준}

        # ③ 가중치
        w = self.D["가중치"][self.D["가중치"]["해수욕장ID"] == 해수욕장ID]
        out["가중치"] = None if w.empty else {
            "주변응답수": int(w.iloc[0].주변응답수), "주변목격수": int(w.iloc[0].주변목격수),
            "가중치": w.iloc[0].가중치, "권역목격률": w.iloc[0].권역목격률}

        # ④ 연결 관측소
        o = self.D["관측"]
        o = o[(o["관측소ID"] == b.관측소ID) & (o["시작일"] <= pd.Timestamp(날짜))]
        o = None if o.empty else o.loc[o["시작일"].idxmax()]
        out["관측소"] = {"이름": b.관측소명, "거리km": b.관측소거리km,
                      "평년수온": None if out["평년"] is None or 없음(out["평년"]["평년수온"]) else out["평년"]["평년수온"],
                      "최근시작일": None if o is None else o.시작일, "최근수온": None if o is None else o.수온,
                      "먼관측소": b.관측소거리km > 100}
        return out
