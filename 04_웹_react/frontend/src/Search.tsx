import { useEffect, useMemo, useRef, useState } from "react";
import type { Beach } from "./api";

type Props = { beaches: Beach[]; selected?: Beach; onSelect: (id: string) => void };

// 이름 일부만 입력해도 자동완성 (예: "해운" → 해운대). ↑↓ 이동, Enter 선택, Esc 닫기
export default function Search({ beaches, selected, onSelect }: Props) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => { setText(selected ? selected.표시명 : ""); }, [selected]);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const hits = useMemo(() => {
    const t = text.trim().replace(/\s+/g, "");
    if (!t || (selected && text === selected.표시명)) return [];
    const 이름 = beaches.filter((b) => b.해수욕장명.includes(t));
    const 지역 = beaches.filter((b) => !b.해수욕장명.includes(t) && b.표시명.replace(/\s+/g, "").includes(t));
    // 이름이 입력으로 시작하는 곳을 먼저
    이름.sort((a, b) => Number(!a.해수욕장명.startsWith(t)) - Number(!b.해수욕장명.startsWith(t)));
    return [...이름, ...지역].slice(0, 10);
  }, [text, beaches, selected]);

  function pick(b: Beach) {
    onSelect(b.해수욕장ID);
    setText(b.표시명);
    setOpen(false);
  }

  return (
    <div className="search" ref={box}>
      <input
        value={text}
        placeholder="이름을 입력하세요 (예: 해운대)"
        onChange={(e) => { setText(e.target.value); setOpen(true); setHi(0); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, hits.length - 1)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
          else if (e.key === "Enter" && hits[hi]) pick(hits[hi]);
          else if (e.key === "Escape") setOpen(false);
        }}
      />
      {open && hits.length > 0 && (
        <ul className="hits">
          {hits.map((b, i) => (
            <li key={b.해수욕장ID} className={i === hi ? "on" : ""} onMouseEnter={() => setHi(i)} onMouseDown={() => pick(b)}>
              <b>{b.해수욕장명}</b> <span>{b.시도명} {b.시군명}</span>
            </li>
          ))}
        </ul>
      )}
      {open && text.trim() && hits.length === 0 && !(selected && text === selected.표시명) && (
        <ul className="hits"><li className="none">찾는 해수욕장이 없어요</li></ul>
      )}
    </div>
  );
}
