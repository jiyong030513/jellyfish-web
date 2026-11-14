"""해수욕장 해파리 위험도 조회 (Streamlit + MySQL jellyfish DB)

실행: 이 파일을 그대로 실행하면 된다 (VS Code ▶ 버튼, 또는 python app.py)
      → 브라우저가 자동으로 열린다. 끌 때는 터미널에서 Ctrl + C
화면만 그린다. 데이터 조회·계산은 서비스로직.py (React용 서버와 같이 씀)
주소로 바로 열기: http://localhost:8501/?beach=B149&date=2023-08-10 (해수욕장ID, 날짜)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- python app.py 로 실행했을 때
if __name__ == "__main__":
    from streamlit import runtime
    if not runtime.exists():          # 아직 streamlit 밖이면 streamlit으로 다시 실행
        import threading
        import webbrowser
        threading.Timer(4, lambda: webbrowser.open("http://localhost:8501")).start()   # 4초 뒤 브라우저 열기
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__),
                                  "--server.port", "8501", "--server.headless", "true",
                                  "--browser.gatherUsageStats", "false"],
                                 cwd=HERE))   # .streamlit/config.toml(테마)을 읽도록 이 폴더에서 실행

import datetime as dt

import altair as alt
import folium
import pandas as pd
import streamlit as st
from branca.element import MacroElement
from jinja2 import Template
from streamlit_folium import st_folium

from 서비스로직 import SQL, 등급, 회색, 등급_구하기, 대상주, 월_주차, pct, 전체_불러오기, 위험도서비스, 한글날짜

st.set_page_config(page_title="해파리 위험도 조회", page_icon="🌊", layout="wide")
ss = st.session_state

# ---------------------------------------------------------------- 디자인 (CSS)
# 주의: 아래 문자열에 빈 줄을 넣으면 마크다운이 문단으로 끊어 CSS가 글자로 보인다
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root { --navy:#0B2545; --teal:#0E7C86; --line:#E3ECF2; --soft:#F3F8FB; --muted:#5B6B7C; }
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, h1, h2, h3, h4, h5, h6,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] {
  font-family: "Pretendard Variable", Pretendard, "Noto Sans KR", -apple-system, "Malgun Gothic", sans-serif !important;
}
.block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1500px; }
header[data-testid="stHeader"] { background: transparent; }
/* 상단 배너 */
.hero { background: linear-gradient(120deg, #0B2545 0%, #13456B 55%, #0E7C86 100%);
        color: #fff; border-radius: 18px; padding: 22px 28px; margin-bottom: 18px;
        box-shadow: 0 6px 20px rgba(11,37,69,.18); }
.hero h1 { color: #fff; font-size: 1.75rem; font-weight: 800; margin: 0; padding: 0; letter-spacing: -.5px; }
.hero .sub { margin-top: 6px; font-size: 1.02rem; opacity: .92; }
.hero .chip { display: inline-block; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.28);
              border-radius: 999px; padding: 2px 12px; margin-right: 6px; font-size: .9rem; }
/* 섹션 제목 */
.sec { font-size: 1.05rem; font-weight: 700; color: var(--navy); margin: 18px 0 8px;
       padding-left: 10px; border-left: 4px solid var(--teal); }
.beach { font-size: 1.6rem; font-weight: 800; color: var(--navy); margin: 0; }
.where { color: var(--muted); font-size: .92rem; margin: 2px 0 6px; }
/* 카드 */
.card { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 14px 18px;
        box-shadow: 0 2px 10px rgba(11,37,69,.06); }
.big { font-size: 2.3rem; font-weight: 800; line-height: 1.1; }
[data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); border-radius: 14px;
                           padding: 12px 14px; box-shadow: 0 2px 10px rgba(11,37,69,.06); }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { white-space: normal !important;
                           overflow: visible !important; text-overflow: clip !important; }
[data-testid="stMetricLabel"] p { font-size: .86rem; color: var(--muted); line-height: 1.3; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
.st-key-pred [data-testid="stMetric"] { min-height: 140px; }
[data-testid="stMetricValue"] * { word-break: keep-all; }
.st-key-pred [data-testid="stMetricLabel"] p { font-size: .8rem; word-break: keep-all; }
[data-testid="stMetricValue"] { font-size: 1.5rem; line-height: 1.25; font-weight: 800; color: var(--navy); }
/* 위험 등급 배지 */
.badge { display: inline-block; border-radius: 999px; padding: 3px 12px; font-size: .85rem;
         font-weight: 700; color: #fff; vertical-align: middle; }
.legend .badge { margin: 3px 4px 3px 0; }
.note { color: var(--muted); font-size: .84rem; margin-top: 4px; }
/* 사이드바·지도 */
section[data-testid="stSidebar"] { background: var(--soft); border-right: 1px solid var(--line); }
iframe[title="streamlit_folium.st_folium"] { border-radius: 16px; box-shadow: 0 4px 16px rgba(11,37,69,.10); }
</style>
""", unsafe_allow_html=True)


def 배지(name, color):
    글자 = "#3A2F00" if color == "#E6B800" else "#fff"          # 노랑 배지는 어두운 글자
    return f"<span class='badge' style='background:{color};color:{글자}'>{name}</span>"


def 섹션(t):
    st.markdown(f"<div class='sec'>{t}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- 데이터 (시작할 때 한 번만 조회)
@st.cache_resource(show_spinner="DB에서 자료를 불러오는 중이에요 (처음 한 번만)…")
def 서비스():
    return 위험도서비스(전체_불러오기())


svc = 서비스()
D, 해수욕장, B = svc.D, svc.해수욕장, svc.B
ID_표시명 = dict(zip(해수욕장["해수욕장ID"], 해수욕장["표시명"]))
표시명_ID = {v: k for k, v in ID_표시명.items()}

# 주소 매개변수(?beach=ID&date=YYYY-MM-DD)는 처음 열 때 한 번만 반영
if "초기화" not in ss:
    ss.초기화 = True
    q = st.query_params
    try:
        ss["날짜"] = dt.date.fromisoformat(q.get("date", ""))
    except ValueError:
        ss["날짜"] = dt.date.today()
    if q.get("beach") in ID_표시명:
        ss["sel"] = q["beach"]
        ss["검색"] = ID_표시명[q["beach"]]

ss.setdefault("sel", None)
ss.setdefault("last_click", None)

# 지도 클릭 처리 (위젯을 그리기 전에 해야 검색칸에도 반영됨)
clicked = (ss.get("map") or {}).get("last_object_clicked")
if clicked and clicked != ss.last_click:
    ss.last_click = clicked
    d2 = (해수욕장["위도"] - clicked["lat"]) ** 2 + (해수욕장["경도"] - clicked["lng"]) ** 2
    ss.sel = 해수욕장.loc[d2.idxmin(), "해수욕장ID"]
    ss["검색"] = ID_표시명[ss.sel]


def 검색_변경():
    ss.sel = 표시명_ID.get(ss["검색"])


# ---------------------------------------------------------------- 검색·클릭 시 부드럽게 이동 (flyTo)
class 날아가기(MacroElement):
    """st_folium이 중심을 바꿀 때(인자 2개로 setView 호출)만 flyTo로 바꾼다.
    마우스 휠·+/- 버튼 확대는 Leaflet 기본 동작 그대로 둔다."""
    _template = Template("""
{% macro script(this, kwargs) %}
(function (m) {
  var orig = m.setView.bind(m);
  m.setView = function (c, z, o) {
    if (arguments.length !== 2 || !m._loaded) { return orig(c, z, o); }
    if (m._ring) { m.removeLayer(m._ring); m._ring = null; }
    if (z >= 10) {
      m._ring = L.circleMarker(c, {radius: 16, color: '#0B2545', weight: 3, fill: false, interactive: false}).addTo(m);
    }
    return m.flyTo(c, z, {duration: 1.5});
  };
})({{ this._parent.get_name() }});
{% endmacro %}""")


# ---------------------------------------------------------------- 사이드바
with st.sidebar:
    st.header("조회 조건")
    날짜 = st.date_input("날짜", key="날짜", min_value=dt.date(2014, 9, 1), max_value=dt.date(2030, 12, 31))
    st.selectbox("해수욕장 검색", options=list(ID_표시명.values()), index=None,
                 placeholder="이름을 입력하세요 (예: 해운대)", key="검색", on_change=검색_변경)
    색기준 = st.radio("지도 색 기준", ["평년 출현율", "예측 위험 지수"], horizontal=True)
    예측기간 = st.radio("예측 기간", [1, 2, 4], index=2, format_func=lambda k: f"{k}주 뒤", horizontal=True)
    st.divider()
    st.caption("위험 등급 (출현율·지수 기준)")
    st.markdown("<div class='legend'>" + "".join(배지(f"{name} {int(lo * 100)}%↑", color) for lo, name, color in 등급)
                + 배지("자료 없음 / 시즌 아님", 회색) + "</div>", unsafe_allow_html=True)
    st.write("")
    if st.button("DB 다시 불러오기", help="DB 내용을 바꾼 뒤 누르세요", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    st.caption(f"자료: 국립수산과학원 해파리 주간보고({svc.보고기간_표시}), 기상청 해양기상부이, "
               "국립수산과학원 해파리 모니터링 설문(2024 – 2025)")

월, 주차 = 월_주차(날짜)
시즌 = 5 <= 월 <= 12
예측 = svc.예측표(날짜)
색값 = svc.지도색값(날짜, 색기준, 예측기간, 예측)


@st.cache_resource(show_spinner=False, max_entries=30)
def 지도_만들기(색값_tuple):
    색값 = dict(색값_tuple)
    m = folium.Map(location=(35.75, 127.7), zoom_start=7, control_scale=True,
                   zoom_snap=0.5, zoom_delta=0.5, wheel_px_per_zoom_level=120)
    for r in 해수욕장.itertuples():
        v = 색값.get(r.해수욕장ID)
        name, color = 등급_구하기(v)
        folium.CircleMarker(location=(r.위도, r.경도), radius=7, weight=1, color="#ffffff",
                            fill=True, fill_color=color, fill_opacity=0.9,
                            tooltip=f"{r.해수욕장명} · {r.시군명}  |  {name} {pct(v)}").add_to(m)
    날아가기().add_to(m)
    return m


지도 = 지도_만들기(tuple(sorted(색값.items())))
if ss.sel:
    center, zoom = (float(B.loc[ss.sel, "위도"]), float(B.loc[ss.sel, "경도"])), 12
else:
    center, zoom = (35.75, 127.7), 7

# ---------------------------------------------------------------- 상단 배너
칩 = [f"<span class='chip'>{월}월 {주차}주</span>"]
if 색기준 == "예측 위험 지수":
    칩.append(f"<span class='chip'>지도 색: {예측기간}주 뒤 {대상주(날짜, 예측기간)['이름']} 위험 지수</span>")
else:
    칩.append("<span class='chip'>지도 색: 평년 출현율</span>")
안내 = "" if 시즌 else "<div class='sub'>해파리 시즌(5~12월)이 아니어서 평년 출현율이 없어요</div>"
st.markdown(f"<div class='hero'><h1>🌊 해수욕장 해파리 위험도</h1>"
            f"<div class='sub'><b>{한글날짜(날짜)}</b> &nbsp; {''.join(칩)}</div>{안내}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- 지도 + 상세
왼쪽, 오른쪽 = st.columns([1.2, 1], gap="large")
with 왼쪽:
    st_folium(지도, key="map", height=640, use_container_width=True,
              center=center, zoom=zoom, returned_objects=["last_object_clicked"])

with 오른쪽:
    if not ss.sel:
        st.markdown("<div class='beach'>해수욕장을 선택하세요</div>", unsafe_allow_html=True)
        st.markdown("<div class='where'>지도에서 점을 누르거나 왼쪽 검색칸에 이름을 입력하면 위험도를 보여줘요.</div>",
                    unsafe_allow_html=True)
        top = svc.상위(예측, 예측기간)
        if not top.empty:
            t = 대상주(날짜, 예측기간)
            섹션(f"{예측기간}주 뒤 · {t['이름']} ({t['범위']}) 위험 지수 상위 10곳")
            st.dataframe(pd.DataFrame({"해수욕장": top["해수욕장명"], "시군": top["시군명"],
                                       "권역": top["권역명"], "위험 지수": top["표시"]}),
                         hide_index=True, width="stretch")
    else:
        s = svc.상세(ss.sel, 날짜, 예측)
        st.markdown(f"<div class='beach'>{s['이름']}</div><div class='where'>{s['위치']}</div>", unsafe_allow_html=True)

        # ① 평년 출현율
        섹션(f"{s['주차이름']} 평년 출현율")
        if s["평년"] is None:
            st.write("해파리 시즌(5~12월)이 아니에요.")
        else:
            r = s["평년"]
            st.markdown(f"<div class='card'><span class='big' style='color:{r['색']}'>{pct(r['통합'])}</span> "
                        f"&nbsp;{배지(r['등급'], r['색'])}<div class='note'>세 어종 중 하나라도 나올 확률 (통합)</div></div>",
                        unsafe_allow_html=True)
            st.write("")
            c1, c2, c3 = st.columns(3)
            c1.metric("노무라입깃(유해)", pct(r["노무라"]))
            c2.metric("보름달물", pct(r["보름달"]))
            c3.metric("기타", pct(r["기타"]))

        # ② 1·2·4주 뒤
        섹션(s["예측제목"])
        cols = st.container(key="pred").columns(3)
        for col, x in zip(cols, s["예측칸"]):
            # 줄바꿈은 "1주 뒤 ·" / "7월 4주" / "(7/22~7/31)" 단위로만 (CSS keep-all + 묶음 안은 줄바꿈 없는 공백)
            nb = " "
            라벨 = f"{x['예측기간']}주{nb}뒤{nb}· {x['대상'].replace(' ', nb)} ({대상주(날짜, x['예측기간'])['범위']})"
            col.metric(라벨, x["표시"], help=x["도움말"])
            if x["값"] is not None and not pd.isna(x["값"]):
                col.markdown(배지(x["등급"], x["색"]), unsafe_allow_html=True)
        for t in s["같은칸안내"]:
            st.caption(f"ⓘ {t}")
        if s["예측방식"] == "모델":
            st.success(s["예측안내"])
        else:
            st.caption(s["예측안내"])

        if s["최근보고"]:
            rb = s["최근보고"]
            st.write(f"최근 주간보고 **{한글날짜(rb['시작일'])}** · {s['권역명']} 통합 출현율 **{rb['통합']:.1f}%**")
            if rb["대량출현중"]:
                st.error("이미 대량출현 중이에요 (통합 출현율 50% 이상).")

        # ③ 가중치
        if s["가중치"]:
            w = s["가중치"]
            섹션("해수욕장 가중치")
            st.write(f"반경 30km 설문 응답 {w['주변응답수']}건 중 목격 {w['주변목격수']}건 → "
                     f"가중치 **{w['가중치']:.2f}** (권역 평균 목격률 {pct(w['권역목격률'])})")

        # ④ 연결 관측소
        섹션("연결 관측소")
        o = s["관측소"]
        txt = f"{o['이름']} 부이 ({o['거리km']:.1f}km)"
        if o["평년수온"] is not None:
            txt += f" · {s['주차이름']} 평년 수온 {o['평년수온']:.1f}℃"
        st.write(txt)
        if o["최근시작일"] is not None:
            st.write(f"가장 최근 관측 ({o['최근시작일']:%Y-%m-%d} 주): 수온 {o['최근수온']:.1f}℃")
        if o["먼관측소"]:
            st.caption("관측소가 100km 넘게 떨어져 있어 수온은 참고치예요.")

# ---------------------------------------------------------------- 32주 그래프
if ss.sel:
    st.divider()
    섹션(f"{B.loc[ss.sel, '해수욕장명']} 5~12월 평년 출현율")
    곡선 = svc.곡선(ss.sel)
    순서 = list(곡선["주차명"])
    long = 곡선.melt(id_vars=["주차명"], value_vars=["통합출현율", "노무라", "보름달", "기타"],
                   var_name="구분", value_name="출현율")
    선 = alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("주차명:N", sort=순서, title=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("출현율:Q", axis=alt.Axis(format="%"), title="출현율"),
        color=alt.Color("구분:N", sort=["통합출현율", "노무라", "보름달", "기타"],
                        scale=alt.Scale(range=["#0B2545", "#D7263D", "#0E7C86", "#9AA0A6"])),
        tooltip=["주차명", "구분", alt.Tooltip("출현율:Q", format=".1%")])
    layers = [선]
    if 시즌:
        layers.append(alt.Chart(pd.DataFrame({"주차명": [f"{월}월 {주차}주"]}))
                      .mark_rule(color="#F08C00", strokeDash=[4, 4], size=2)
                      .encode(x=alt.X("주차명:N", sort=순서)))
    st.altair_chart(alt.layer(*layers).properties(height=300), width="stretch")

with st.expander("이 화면에서 쓴 SQL 보기"):
    st.caption("앱을 시작할 때 아래 SQL로 테이블·뷰를 한 번 읽어 오고, 이후 클릭·검색은 읽어 온 자료에서 바로 찾아요. "
               f"1·2·4주 뒤 값은 최근 2주 안에 주간보고가 있으면 그 보고를 넣은 예측(v_해수욕장예측위험도), "
               f"없으면 v_학습데이터의 {svc.보고연도} 주간보고로 계산한 권역 x 월 x 주차별 대량출현 비율에 "
               "v_해수욕장가중치의 가중치를 곱한 평년 기준 전망이에요.")
    st.code("\n\n".join(f"-- {k}{v};" for k, v in SQL.items()), language="sql")
