/**
 * 해수욕장 해파리 위험도 — Jellyfish 디자인 토큰 (JS)
 * 출처: Figma「해수욕장해파리위험도_공유본」> _데스크톱_수정본_수정 (2026-11-17 확인)
 *
 * tokens.css 와 같은 값. CSS 변수를 못 쓰는 곳(차트 라이브러리 색상, 지도 마커 옵션,
 * 인라인 style 계산)에서 import 해서 쓴다.
 *   import { color, type, riskLevel } from './tokens';
 */

export const font = {
  sans: '"Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif',
  chart: '"Inter", "Pretendard Variable", Pretendard, sans-serif',
};

export const color = {
  background: { page: '#050506', card: '#111115', raised: '#19191E' },
  glass: {
    top: { base: 'rgba(13, 14, 20, 0.62)', border: 'rgba(184, 206, 255, 0.20)' },
    bottom: { base: 'rgba(12, 13, 18, 0.68)', border: 'rgba(155, 178, 255, 0.14)' },
  },
  border: { subtle: '#25252A', default: '#303036', strong: '#404048' },
  foreground: { inverse: '#111115', primary: '#F5F5F7', secondary: '#B8B8C1' },
  action: { primary: { background: '#F5F5F7' } },
  text: { placeholder: '#8F8F99', muted: '#85858F', hint: '#707079', disabled: '#64646D' },
  risk: {
    veryHigh: '#EF4444',
    high: '#F97316',
    medium: '#EAB308',
    low: '#22C55E',
    noData: '#94A3B8',
    lowBackground: '#9FF3D0',
    lowText: '#092D25',
  },
  chart: {
    selectedLine: '#F97316',
    total: '#E2E8F0',
    nomura: '#F87171',
    moon: '#65C8D0',
    other: '#9CA3AF',
    axisFill: '#000000',
    grid: '#2D2D34',
    axis: '#777781',
    selectedLabel: '#FB923C',
  },
  map: {
    background: '#DCE8E9',
    fallback: '#DDDDDD',
    scaleBackground: 'rgba(255, 255, 255, 0.88)',
    foreground: '#24324B',
    attributionBackground: 'rgba(255, 255, 255, 0.80)',
    link: '#0078A8',
    controlBackground: '#FFFFFF',
    tooltipText: '#18243A',
    provider: { blue: '#4C7BE1', yellow: '#FFD500', ochre: '#E0BC00' },
  },
  utility: { transparent: 'rgba(0, 0, 0, 0)' },
  example: { background: '#2B2521', text: '#F0A56B' },
  loading: { base: '#303036', highlight: '#404048' },
};

export const gradient = {
  pageAmbient: 'radial-gradient(circle closest-side, rgba(54, 71, 104, 0.08) 0%, rgba(54, 71, 104, 0) 28%)',
  glassCool: 'linear-gradient(40deg, rgba(75, 127, 255, 0) 50.25%, rgba(75, 127, 255, 0.34) 67.29%, rgba(141, 91, 255, 0.40) 91.42%)',
  glassWarm: 'linear-gradient(136deg, rgba(255, 130, 54, 0.40) 20.7%, rgba(255, 130, 54, 0) 34.84%)',
  glassViolet: 'linear-gradient(156deg, rgba(137, 74, 255, 0) 53.88%, rgba(137, 74, 255, 0.28) 75.09%, rgba(255, 116, 44, 0.30) 91.76%)',
  glassBlue: 'linear-gradient(32deg, rgba(60, 111, 255, 0.35) 18.9%, rgba(60, 111, 255, 0) 42.12%)',
};

export const shadow = {
  glassTop: '0 28px 90px 0 rgba(0, 0, 0, 0.70), -26px 22px 54px 0 rgba(255, 104, 40, 0.12), 20px -16px 44px 0 rgba(68, 105, 255, 0.16)',
  glassBottom: '0 -26px 80px 0 rgba(0, 0, 0, 0.72), -20px 20px 52px 0 rgba(106, 68, 255, 0.18)',
  cardOutline: '0 0 0 1px #303036',
  mapMarker: '0 3px 12px 0 rgba(21, 56, 112, 0.40)',
  mapTooltip: '0 4px 12px 0 rgba(26, 42, 62, 0.22)',
  mapControl: '0 4px 16px 0 rgba(24, 39, 58, 0.18)',
};

export const spacing = { 0: 0, 8: 8, 12: 12, 16: 16, 24: 24, 32: 32 };
export const radius = { 0: 0, 8: 8, 12: 12, 16: 16, 20: 20 };
export const size = {
  pageWidth: 1440,
  contentWidth: 1344,
  mapControl: 44,
  glassTop: { width: 510, height: 350 },
  glassBottom: { width: 650, height: 330 },
};

/** 텍스트 스타일: [weight, size(px), lineHeight(px | 'normal'), tracking(px), family] */
const t = (weight, sizePx, lineHeight, tracking, family = 'sans') => ({
  fontFamily: font[family],
  fontWeight: weight,
  fontSize: `${sizePx}px`,
  lineHeight: lineHeight === 'normal' ? 'normal' : `${lineHeight}px`,
  letterSpacing: `${tracking}px`,
});

export const type = {
  display: t(700, 56, 72, -2),
  metric: t(700, 64, 72, -3),
  beachTitle: t(700, 32, 40, -1),
  forecastMetric: t(800, 24, 32, -1),
  sectionTitle: t(700, 20, 28, 0),
  sectionSubtitle: t(600, 20, 28, 0),
  brand: t(700, 16, 24, 0),
  bodyLarge: t(400, 16, 24, 0),
  input: t(400, 16, 'normal', 0),
  navigation: t(600, 14, 20, 0),
  button: t(700, 14, 20, 0),
  buttonStrong: t(800, 14, 20, 0),
  labelMedium: t(500, 14, 20, 0),
  body: t(400, 14, 20, 0),
  eyebrow: { ...t(700, 12, 20, 1), textTransform: 'uppercase' },
  label: t(700, 12, 20, 0),
  badge: t(800, 12, 20, 0),
  bodySmall: t(400, 12, 20, 0),
  chartAxis: t(400, 11, 14, 0, 'chart'),
  captionWide: t(400, 10, 20, 0),
  exampleBadge: t(700, 10, 16, 0),
  mapCaption: t(400, 10, 14, 0),
  mapAttribution: t(400, 10, 11, 0),
  mapControl: t(500, 24, 24, 0),
};

/**
 * 위험 등급 (Figma 지도 범례 기준)
 *   매우 높음 60% 이상 / 높음 40~60% / 보통 20~40% / 낮음 0~20% / 자료 없음·시즌 아님
 * @param {number|null|undefined} percent 출현율·예측 위험 지수 (0~100, %)
 */
export function riskLevel(percent) {
  if (percent === null || percent === undefined || Number.isNaN(percent)) {
    return { key: 'noData', label: '자료 없음', color: color.risk.noData };
  }
  if (percent >= 60) return { key: 'veryHigh', label: '매우 높음', color: color.risk.veryHigh };
  if (percent >= 40) return { key: 'high', label: '높음', color: color.risk.high };
  if (percent >= 20) return { key: 'medium', label: '보통', color: color.risk.medium };
  return { key: 'low', label: '낮음', color: color.risk.low };
}

/** 차트 계열 색 (통합 / 노무라 / 보름달 / 기타) */
export const chartSeries = [
  { key: 'total', label: '통합', color: color.chart.total },
  { key: 'nomura', label: '노무라', color: color.chart.nomura },
  { key: 'moon', label: '보름달', color: color.chart.moon },
  { key: 'other', label: '기타', color: color.chart.other },
];

export default { font, color, gradient, shadow, spacing, radius, size, type, riskLevel, chartSeries };
