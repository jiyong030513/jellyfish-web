import { useEffect, useMemo, useState } from "react";
import { get, reload, type Beach, type Detail as DetailT, type MapRes, type Meta, type TopRes } from "./api";
import MapView from "./MapView";
import Search from "./Search";
import Detail from "./Detail";
import Curve from "./Curve";
import SqlPanel from "./SqlPanel";
import ChatBot from "./ChatBot";
import { Badge } from "./ui";

const 오늘 = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

// 주소로 바로 열기: ?beach=B149&date=2023-08-10
const q = new URLSearchParams(location.search);
const 처음날짜 = /^\d{4}-\d{2}-\d{2}$/.test(q.get("date") ?? "") ? q.get("date")! : 오늘();

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [beaches, setBeaches] = useState<Beach[]>([]);
  const [date, setDate] = useState(처음날짜);
  const [mode, setMode] = useState<"평년" | "예측">("평년");
  const [k, setK] = useState(4);
  const [sel, setSel] = useState<string | null>(q.get("beach"));
  const [mapRes, setMapRes] = useState<MapRes | null>(null);
  const [detail, setDetail] = useState<DetailT | null>(null);
  const [top, setTop] = useState<TopRes | null>(null);
  const [ver, setVer] = useState(0);          // "DB 다시 불러오기" 뒤 모든 자료를 새로 받기 위한 번호
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const fail = (e: unknown) => setErr(`서버에 연결할 수 없어요 (${e instanceof Error ? e.message : e}). 잠시 뒤 새로고침해 주세요.`);

  useEffect(() => {
    Promise.all([get<Meta>("/api/meta"), get<Beach[]>("/api/beaches")])
      .then(([m, b]) => { setMeta(m); setBeaches(b); setErr(null); }).catch(fail);
  }, [ver]);

  useEffect(() => {
    if (!date) return;
    get<MapRes>("/api/map", { date, mode, k }).then(setMapRes).catch(fail);
  }, [date, mode, k, ver]);

  useEffect(() => {
    if (!date) return;
    if (!sel) { setDetail(null); get<TopRes>("/api/top", { date, k }).then(setTop).catch(fail); return; }
    get<DetailT>(`/api/beach/${sel}`, { date }).then(setDetail).catch(fail);
  }, [sel, date, k, ver]);

  // 주소창도 현재 선택에 맞춰 바꿔 둠 (새로고침·공유용)
  useEffect(() => {
    const p = new URLSearchParams({ date });
    if (sel) p.set("beach", sel);
    history.replaceState(null, "", `?${p}`);
  }, [sel, date]);

  const byId = useMemo(() => Object.fromEntries(beaches.map((b) => [b.해수욕장ID, b])), [beaches]);
  const selBeach = sel ? byId[sel] : undefined;

  async function onReload() {
    setBusy(true);
    try { setMeta(await reload()); setVer((v) => v + 1); } catch (e) { fail(e); } finally { setBusy(false); }
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>🌊 해수욕장 해파리 위험도</h1>
        <div className="sub">
          <b>{mapRes?.날짜한글 ?? date}</b>
          {mapRes && <><span className="chip">{mapRes.주차이름}</span><span className="chip">{mapRes.설명}</span></>}
        </div>
        {mapRes && !mapRes.시즌 && <div className="sub">해파리 시즌(5~12월)이 아니어서 평년 출현율이 없어요</div>}
      </header>

      {err && <div className="alert error">{err}</div>}
      {!meta && !err && <div className="alert success">서버를 준비하는 중이에요. 한동안 접속이 없었다면 처음 한 번은 최대 1분쯤 걸려요.</div>}

      <div className="layout">
        <aside className="panel side">
          <h2>조회 조건</h2>
          <label className="field">
            <span>날짜</span>
            <input type="date" value={date} min="2014-09-01" max="2030-12-31" onChange={(e) => setDate(e.target.value)} />
          </label>
          <div className="field">
            <span>해수욕장 검색</span>
            <Search beaches={beaches} selected={selBeach} onSelect={setSel} />
          </div>
          <div className="field">
            <span>지도 색 기준</span>
            <div className="seg">
              {(["평년", "예측"] as const).map((m) => (
                <button key={m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>
                  {m === "평년" ? "평년 출현율" : "예측 위험 지수"}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <span>예측 기간</span>
            <div className="seg">
              {[1, 2, 4].map((x) => (
                <button key={x} className={k === x ? "on" : ""} onClick={() => setK(x)}>{x}주 뒤</button>
              ))}
            </div>
          </div>
          <hr />
          <div className="caption">위험 등급 (출현율·지수 기준)</div>
          <div className="legend">
            {meta?.등급.map((g) => (
              <Badge key={g.이름} name={g.하한 === null ? "자료 없음 / 시즌 아님" : `${g.이름} ${Math.round(g.하한 * 100)}%↑`} color={g.색} />
            ))}
          </div>
          <button className="btn" onClick={onReload} disabled={busy}>{busy ? "불러오는 중…" : "DB 다시 불러오기"}</button>
          <div className="caption">
            자료: 국립수산과학원 해파리 주간보고({meta?.보고기간 ?? "-"}), 기상청 해양기상부이,
            국립수산과학원 해파리 모니터링 설문(2024 – 2025)
          </div>
        </aside>

        <section className="panel mapbox">
          <MapView beaches={beaches} values={mapRes?.값 ?? {}} selected={selBeach} onSelect={setSel} />
          {sel && <button className="btn ghost reset" onClick={() => setSel(null)}>전국 보기</button>}
        </section>

        <section className="panel detail">
          {sel && detail
            ? <Detail d={detail} />
            : <Top top={top} onSelect={setSel} />}
        </section>
      </div>

      {sel && detail && (
        <section className="panel">
          <div className="sec">{detail.이름} 5~12월 평년 출현율</div>
          <Curve data={detail.곡선} now={mapRes?.시즌 ? `${detail.월}월 ${detail.주차}주` : null} />
        </section>
      )}

      <SqlPanel ver={ver} />
      <ChatBot beachId={sel} beachName={selBeach?.해수욕장명} k={k} date={date} onPick={setSel} />
    </div>
  );
}

function Top({ top, onSelect }: { top: TopRes | null; onSelect: (id: string) => void }) {
  return (
    <>
      <div className="beach">해수욕장을 선택하세요</div>
      <div className="where">지도에서 점을 누르거나 왼쪽 검색칸에 이름을 입력하면 위험도를 보여줘요.</div>
      {top && top.목록.length > 0 && (
        <>
          <div className="sec">{top.제목}</div>
          <table className="tbl">
            <thead><tr><th>#</th><th>해수욕장</th><th>시군</th><th>권역</th><th>위험 지수</th></tr></thead>
            <tbody>
              {top.목록.map((r, i) => (
                <tr key={r.해수욕장ID} onClick={() => onSelect(r.해수욕장ID)}>
                  <td>{i + 1}</td><td className="strong">{r.해수욕장명}</td><td>{r.시군명}</td><td>{r.권역명}</td>
                  <td><span className="dot" style={{ background: r.색 }} />{r.표시}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
