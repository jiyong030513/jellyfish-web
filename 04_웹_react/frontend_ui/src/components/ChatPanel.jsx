/* 해파리 AI 가이드 대화창
   ChatbotLauncher(오른쪽 아래 버튼)를 누르면 같은 자리에 열린다.
   서버: POST /chat → { answer, emergency, forecast, sources:[{기관, url}] } */
import { useEffect, useRef, useState } from 'react';
import { sendChat } from '../api/client.js';
import { BrandLogo, LoadingIndicator } from './basics.jsx';

const SUGGESTIONS = ['해파리에 쏘이면 어떻게 해?', '여기 지금 가도 괜찮아?', '해파리 예방 수칙 알려줘'];
const WELCOME = '안녕하세요! 해파리에 쏘였을 때 대처법, 예방 수칙, 해수욕장 위험도를 물어보세요.';

// 답에 쓰인 예보 해수욕장 (중복 제거) → 누르면 지도 이동
const uniquePlaces = (rows = []) => [...new Map(rows.filter((r) => r.beach_id).map((r) => [r.beach_id, { id: r.beach_id, name: r.beach_name }])).values()];

export function ChatPanel({ open, onClose, beach, horizonWeeks, date, onPick }) {
  const [messages, setMessages] = useState([{ role: 'model', text: WELCOME }]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, sending]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  async function send(text) {
    const message = text.trim();
    if (!message || sending) return;
    const history = messages.filter((m) => m.text !== WELCOME && !m.error);
    setMessages((m) => [...m, { role: 'user', text: message }]);
    setInput('');
    setSending(true);
    try {
      const res = await sendChat({ message, beachId: beach?.id, horizonWeeks, date, history });
      setMessages((m) => [...m, { role: 'model', text: res.answer, emergency: res.emergency, sources: res.sources ?? [], places: uniquePlaces(res.forecast) }]);
    } catch (err) {
      setMessages((m) => [...m, { role: 'model', error: true, text: '답변을 받지 못했어요. 잠시 후 다시 시도해 주세요. 응급 상황이면 바로 119에 신고하세요.' }]);
      console.error('[jellycast] chat', err);
    } finally {
      setSending(false);
    }
  }

  if (!open) return null;
  return (
    <section className="jc-chat" role="dialog" aria-label="해파리 AI 가이드">
      <header className="jc-chat__head">
        <span className="jc-chat__avatar"><BrandLogo variant="plain" size={24} /></span>
        <span className="jc-chat__title">
          <span className="text-brand">해파리 AI 가이드</span>
          <span className="text-body-small jc-c-muted">{beach ? `${beach.name} 기준으로 답해요` : '궁금한 점을 물어보세요'}</span>
        </span>
        <button type="button" className="jc-chat__close" onClick={onClose} aria-label="대화창 닫기">×</button>
      </header>

      <div className="jc-chat__list" ref={listRef} aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`jc-chat__msg jc-chat__msg--${m.role}`}>
            {m.emergency && (
              <a className="jc-chat__emergency" href="tel:119">
                <strong className="text-button">응급 상황이면 바로 119</strong>
                <span className="text-body-small">눌러서 전화하기</span>
              </a>
            )}
            <p className={`jc-chat__bubble text-body${m.error ? ' is-error' : ''}`}>{m.text}</p>
            {m.places?.length > 0 && onPick && (
              <div className="jc-chat__places">
                {m.places.map((p) => (
                  <button key={p.id} type="button" className="jc-chat__chip text-body-small" onClick={() => onPick(p.id)}
                    aria-label={`${p.name} 지도에서 보기`}>📍 {p.name}</button>
                ))}
              </div>
            )}
            {m.sources?.length > 0 && (
              <div className="jc-chat__sources text-body-small">
                출처{' '}
                {m.sources.map((s, j) => (s.url
                  ? <a key={j} href={s.url} target="_blank" rel="noreferrer">{s.기관}</a>
                  : <span key={j}>{s.기관}</span>))}
              </div>
            )}
          </div>
        ))}
        {sending && <div className="jc-chat__msg jc-chat__msg--model"><span className="jc-chat__bubble"><LoadingIndicator>답변을 만드는 중</LoadingIndicator></span></div>}
        {messages.length === 1 && !sending && (
          <div className="jc-chat__suggest">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="jc-chat__chip text-body-small" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
      </div>

      <form className="jc-chat__form" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        <input
          ref={inputRef}
          className="jc-chat__input text-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="질문을 입력하세요"
          maxLength={1000}
          aria-label="질문 입력"
        />
        <button type="submit" className="jc-btn jc-btn--primary jc-chat__send" disabled={!input.trim() || sending}>
          <span>보내기</span>
        </button>
      </form>
      <p className="jc-chat__note text-caption-wide jc-c-hint">AI 답변은 참고용이에요. 위급하면 119에 신고하세요.</p>
    </section>
  );
}
