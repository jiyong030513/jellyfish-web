import { useEffect, useState } from "react";
import { get, type SqlRes } from "./api";

// 발표용 "이 화면에서 쓴 SQL 보기" (처음 펼칠 때 /api/sql 에서 받아 옴)
export default function SqlPanel({ ver }: { ver: number }) {
  const [open, setOpen] = useState(false);
  const [res, setRes] = useState<SqlRes | null>(null);

  useEffect(() => { setRes(null); }, [ver]);
  useEffect(() => {
    if (open && !res) get<SqlRes>("/api/sql").then(setRes).catch(() => {});
  }, [open, res]);

  return (
    <section className="panel sqlbox">
      <button className="sqlhead" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className={`arrow ${open ? "on" : ""}`}>▸</span> 이 화면에서 쓴 SQL 보기
      </button>
      {open && res && (
        <div className="sqlbody">
          <div className="note">{res.설명}</div>
          {res.목록.map((s) => (
            <div key={s.이름}>
              <div className="sqlname">-- {s.이름}</div>
              <pre>{s.sql}</pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
