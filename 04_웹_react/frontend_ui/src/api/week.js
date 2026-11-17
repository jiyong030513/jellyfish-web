/* 날짜 ↔ 'N월 M주' 변환 (화면과 서버가 같은 규칙을 쓰도록 한 곳에 모아 둠)
   M주 = 그 달의 날짜를 7일씩 끊은 순번 (1~7일 1주, 8~14일 2주 …, 29일 이후는 4주로 묶음) */

export const toISO = (d) => {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
const parse = (iso) => {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
};
export const today = () => toISO(new Date());
export const addDays = (iso, n) => {
  const d = parse(iso);
  d.setDate(d.getDate() + n);
  return toISO(d);
};
const weekOfMonth = (day) => Math.min(4, Math.ceil(day / 7));

export function weekLabel(iso) {
  const d = parse(iso);
  return `${d.getMonth() + 1}월 ${weekOfMonth(d.getDate())}주`;
}

// 5월 1주 = 0 … 12월 4주 = 31, 범위 밖이면 null (그래프의 '선택한 주' 위치)
export function seasonIndex(iso) {
  const d = parse(iso);
  const m = d.getMonth() + 1;
  if (m < 5) return null;
  return (m - 5) * 4 + weekOfMonth(d.getDate()) - 1;
}

export const toDots = (iso) => iso.replaceAll('-', '.');
