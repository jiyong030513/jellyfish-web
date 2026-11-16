// 백엔드(FastAPI) 호출. 계산은 모두 백엔드(서비스로직.py)가 하고, 여기서는 받아서 그리기만 한다.
export const API = import.meta.env.VITE_API ?? "http://127.0.0.1:8000";

export type Beach = {
  해수욕장ID: string; 해수욕장명: string; 시도명: string; 시군명: string; 권역명: string;
  위도: number; 경도: number; 표시명: string;
};
export type Grade = { 이름: string; 하한: number | null; 색: string };
export type Meta = { 보고기간: string; 보고연도: string; 해수욕장수: number; 불러온시각: string; 등급: Grade[] };
export type MapCell = { 값: number | null; 표시: string; 등급: string; 색: string };
export type MapRes = { 날짜: string; 주차이름: string; 날짜한글: string; 시즌: boolean; 설명: string; 값: Record<string, MapCell> };
export type TopRow = { 해수욕장ID: string; 해수욕장명: string; 시군명: string; 권역명: string; 표시: string; 등급: string; 색: string };
export type TopRes = { 제목: string; 목록: TopRow[] };
export type PredCell = {
  예측기간: number; 라벨: string; 대상: string; 범위: string; 값: number | null; 상한전: number | null;
  표시: string; 등급: string; 색: string; 방식: string; 도움말: string;
};
export type CurvePoint = { 월: number; 주차: number; 주차명: string; 통합출현율: number | null; 노무라: number | null; 보름달: number | null; 기타: number | null };
export type Detail = {
  해수욕장ID: string; 이름: string; 권역명: string; 위치: string; 월: number; 주차: number; 주차이름: string;
  평년: null | { 통합: number; 등급: string; 색: string; 표시: Record<"통합" | "노무라" | "보름달" | "기타", string> };
  예측칸: PredCell[]; 예측방식: "모델" | "평년"; 예측제목: string; 예측안내: string; 같은칸안내: string[]; 배지: string;
  최근보고: null | { 문장: string; 대량출현중: boolean };
  가중치: null | { 문장: string };
  관측소: { 문장: string; 최근문장: string | null; 먼관측소: boolean };
  곡선: CurvePoint[];
};
export type SqlRes = { 설명: string; 목록: { 이름: string; sql: string }[] };

export async function get<T>(path: string, params: Record<string, string | number> = {}): Promise<T> {
  const q = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  const r = await fetch(`${API}${path}${q.size ? "?" + q : ""}`);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

// AI 해파리 상담봇 (POST /api/chat)
export type ChatTurn = { role: "user" | "model"; text: string };
export type ChatForecast = { beach_name: string; horizon_weeks: number; target_week: string; risk_text: string; risk_level: string; kind: string };
export type ChatRes = { answer: string; emergency: boolean; forecast: ChatForecast[]; sources: { 기관: string; url: string }[] };

export async function chat(body: { message: string; beach_id?: string | null; horizon_weeks?: number; history: ChatTurn[] }): Promise<ChatRes> {
  const r = await fetch(`${API}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) {
    const d = await r.json().catch(() => null);
    throw new Error(d?.detail && typeof d.detail === "string" ? d.detail : `상담봇 오류 (${r.status})`);
  }
  return r.json();
}

export async function reload(): Promise<Meta> {
  const r = await fetch(`${API}/api/reload`, { method: "POST" });
  if (!r.ok) throw new Error(`reload → ${r.status}`);
  return r.json();
}
