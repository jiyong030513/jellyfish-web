export function Badge({ name, color }: { name: string; color: string }) {
  // 노랑 배지는 어두운 글자 (대비)
  return <span className="badge" style={{ background: color, color: color === "#E6B800" ? "#3A2F00" : "#fff" }}>{name}</span>;
}
