import { useEffect, useRef, useState } from "react";
import { chat, type ChatRes, type ChatTurn } from "./api";

type Msg = { role: "user" | "model"; text: string; res?: ChatRes; error?: boolean };
type Props = { beachId: string | null; beachName?: string; k: number };

const 예시 = ["해운대 다음 주 괜찮아?", "해파리에 쏘이면 어떻게 해요?", "해파리 예방하려면 뭘 입어야 해?"];

// 오른쪽 아래 AI 해파리 상담봇. 선택한 해수욕장·예측 기간을 같이 보내고, 응급이면 119 배너를 띄운다.
export default function ChatBot({ beachId, beachName, k }: Props) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const emergency = msgs.some((m) => m.res?.emergency);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy, open]);

  async function send(q: string) {
    q = q.trim();
    if (!q || busy) return;
    const history: ChatTurn[] = msgs.filter((m) => !m.error).slice(-10).map((m) => ({ role: m.role, text: m.text }));
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setText("");
    setBusy(true);
    try {
      const res = await chat({ message: q, beach_id: beachId, horizon_weeks: k, history });
      setMsgs((m) => [...m, { role: "model", text: res.answer, res }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "model", text: e instanceof Error ? e.message : "오류가 났어요", error: true }]);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return <button className="chat-fab" onClick={() => setOpen(true)} aria-label="AI 해파리 상담 열기">💬 AI 상담</button>;
  }

  return (
    <div className="chat-box" role="dialog" aria-label="AI 해파리 상담">
      <div className="chat-head">
        <div>
          <b>AI 해파리 상담</b>
          <div className="chat-sub">{beachName ? `${beachName} · ${k}주 뒤 기준` : "해수욕장을 고르면 그곳 예보로 답해요"}</div>
        </div>
        <button onClick={() => setOpen(false)} aria-label="닫기">✕</button>
      </div>

      {emergency && (
        <a className="chat-119" href="tel:119">🚨 증상이 심하면 지금 바로 <b>119</b>에 신고하세요</a>
      )}

      <div className="chat-body">
        {msgs.length === 0 && (
          <div className="chat-hello">
            <p>해파리 예보와 쏘였을 때 대처법을 물어보세요.</p>
            {예시.map((q) => <button key={q} className="chat-chip" onClick={() => send(q)}>{q}</button>)}
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}${m.error ? " err" : ""}`}>
            <div className="chat-text">{m.text}</div>
            {m.res && m.res.sources.length > 0 && (
              <div className="chat-src">
                출처: {m.res.sources.map((s, j) => (
                  <span key={j}>{j > 0 && " · "}{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.기관}</a> : s.기관}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="chat-msg model"><div className="chat-text chat-typing">답변을 만드는 중…</div></div>}
        <div ref={end} />
      </div>

      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} placeholder="질문을 입력하세요" disabled={busy} />
        <button type="submit" disabled={busy || !text.trim()}>보내기</button>
      </form>
      <div className="chat-note">AI 답변은 참고용이에요. 응급 상황은 119, 현장 안내를 따르세요.</div>
    </div>
  );
}
