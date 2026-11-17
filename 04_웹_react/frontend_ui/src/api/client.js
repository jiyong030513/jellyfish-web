/* FastAPI 연결
   .env 에 VITE_API_BASE=http://localhost:8000 처럼 서버 주소를 넣으면 실제 서버를 쓴다.
   주소가 비어 있거나 서버가 응답하지 않으면 mock.js 의 예시 데이터로 돌아간다.
   서버 응답(snake_case) → 화면 컴포넌트 props(camelCase) 변환은 이 파일에서만 한다. */
import { mockBeaches, mockBeachDetail, mockChat } from './mock.js';

export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');
const FALLBACK = (import.meta.env.VITE_MOCK_FALLBACK ?? 'true') !== 'false';
export const isMock = () => !API_BASE;

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json();
}

// 서버가 있으면 서버, 없거나 실패하면 예시 데이터
async function withFallback(call, mock) {
  if (isMock()) return mock();
  try {
    return await call();
  } catch (err) {
    if (!FALLBACK) throw err;
    console.warn('[jellycast] 서버 요청 실패, 예시 데이터로 표시합니다:', err.message);
    return mock();
  }
}

/* ───── 해수욕장 목록 (지도 마커) ─────
   GET /beaches?date=2026-11-11 */
export async function fetchBeaches({ date }) {
  const raw = await withFallback(
    () => request(`/beaches?date=${encodeURIComponent(date)}`),
    () => mockBeaches({ date }),
  );
  return {
    weekLabel: raw.week_label,
    beaches: raw.beaches.map((b) => ({
      id: b.id, name: b.name, region: b.region, lat: b.lat, lng: b.lng,
      averagePercent: b.average_percent,
      forecastPercent: b.forecast_percent ?? {}, // { "1": 12.1, "2": 4.2, "4": 11.2 }
    })),
  };
}

/* ───── 선택한 해수욕장 상세 (카드 4개 + 안내 + 그래프) ─────
   GET /beaches/{id}?date=2026-11-11 */
export async function fetchBeachDetail(id, { date }) {
  const raw = await withFallback(
    () => request(`/beaches/${id}?date=${encodeURIComponent(date)}`),
    () => mockBeachDetail(id, { date }),
  );
  const { beach: b, forecast: f, observation: o, notice: n, season: s } = raw;
  return {
    beach: {
      id: b.id, name: b.name, region: b.region, size: b.size,
      weekLabel: b.week_label, averagePercent: b.average_percent, species: b.species ?? [],
    },
    forecast: { items: f.items, reportDate: f.report_date },
    obs: {
      reportDate: o.report_date, regionName: o.region_name, regionRate: o.region_rate,
      station: o.station, stationDistance: o.station_distance,
      weekLabel: b.week_label, avgTemp: o.avg_temp,
      latestLabel: o.latest_label, latestTemp: o.latest_temp,
    },
    notice: n,
    season: { data: s.data, selectedIndex: s.selected_index, isExample: !!s.is_example },
  };
}

/* ───── 챗봇 ─────
   POST /chat  (이지용님 jellycast-chat 서버와 같은 형식)
   history: [{ role: 'user' | 'model', text }] 최근 10개 */
export async function sendChat({ message, beachId, horizonWeeks, date, history = [] }) {
  const body = {
    message,
    date: date ?? null, // 화면에서 고른 날짜 → 챗봇 숫자 = 화면 숫자
    beach_id: beachId ?? null,
    horizon_weeks: horizonWeeks ?? null,
    history: history.slice(-10).map(({ role, text }) => ({ role, text })),
  };
  return withFallback(
    () => request('/chat', { method: 'POST', body: JSON.stringify(body) }),
    () => mockChat(body),
  );
}
