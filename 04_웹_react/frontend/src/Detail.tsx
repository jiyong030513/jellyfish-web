import type { Detail as D } from "./api";
import { Badge } from "./ui";

export default function Detail({ d }: { d: D }) {
  return (
    <>
      <div className="beach">{d.이름}</div>
      <div className="where">{d.위치}</div>

      {/* ① 평년 출현율 */}
      <div className="sec">{d.주차이름} 평년 출현율</div>
      {d.평년 === null ? (
        <p>해파리 시즌(5~12월)이 아니에요.</p>
      ) : (
        <>
          <div className="card">
            <span className="big" style={{ color: d.평년.색 }}>{d.평년.표시.통합}</span>
            <Badge name={d.평년.등급} color={d.평년.색} />
            <div className="note">세 어종 중 하나라도 나올 확률 (통합)</div>
          </div>
          <div className="grid3">
            <Metric label="노무라입깃(유해)" value={d.평년.표시.노무라} />
            <Metric label="보름달물" value={d.평년.표시.보름달} />
            <Metric label="기타" value={d.평년.표시.기타} />
          </div>
        </>
      )}

      {/* ② 1·2·4주 뒤 */}
      <div className="sec row">
        <span>{d.예측제목}</span>
        <span className={`kind ${d.예측방식 === "모델" ? "model" : "base"}`}>{d.배지}</span>
      </div>
      <div className="grid3">
        {d.예측칸.map((x) => (
          <div className="metric pred" key={x.예측기간}>
            <div className="mlabel">
              <span className="nowrap">{x.예측기간}주 뒤 ·</span> <span className="nowrap">{x.대상}</span>{" "}
              <span className="nowrap">({x.범위})</span>
            </div>
            <div className="mvalue" style={{ color: x.값 === null ? undefined : x.색 }}>{x.표시}</div>
            <div className="mfoot">
              {x.값 !== null && <Badge name={x.등급} color={x.색} />}
              <span className="help" tabIndex={0} aria-label="계산 근거">
                ⓘ<span className="tip">{x.도움말}</span>
              </span>
            </div>
          </div>
        ))}
      </div>
      {d.같은칸안내.map((t) => <div className="note" key={t}>ⓘ {t}</div>)}
      <div className={d.예측방식 === "모델" ? "alert success" : "note"}>{d.예측안내}</div>

      {d.최근보고 && (
        <>
          <p>{d.최근보고.문장}</p>
          {d.최근보고.대량출현중 && <div className="alert error">이미 대량출현 중이에요 (통합 출현율 50% 이상).</div>}
        </>
      )}

      {/* ③ 가중치 */}
      {d.가중치 && (
        <>
          <div className="sec">해수욕장 가중치</div>
          <p>{d.가중치.문장}</p>
        </>
      )}

      {/* ④ 연결 관측소 */}
      <div className="sec">연결 관측소</div>
      <p>{d.관측소.문장}</p>
      {d.관측소.최근문장 && <p>{d.관측소.최근문장}</p>}
      {d.관측소.먼관측소 && <div className="note">관측소가 100km 넘게 떨어져 있어 수온은 참고치예요.</div>}
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <div className="mlabel">{label}</div>
      <div className="mvalue">{value}</div>
    </div>
  );
}
