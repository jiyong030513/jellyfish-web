/* 기본 조각: 브랜드, 버튼, 입력, 선택, 범례, 정보, 배지, 지도 조각, 로딩
   시트의 컴포넌트 이름을 주석으로 달아 두었습니다. */
import { useMemo, useRef, useState } from 'react';
import { SearchIcon, CalendarIcon, RefreshIcon, ExpandIcon, JellyfishIcon } from './icons.jsx';
import { riskLevel } from '../styles/tokens.js';

const cx = (...c) => c.filter(Boolean).join(' ');

/* ───────────── 브랜드/로고 · 헤더표시 · 푸터표시 ───────────── */
export function BrandLogo({ variant = 'tile', src, size }) {
  const icon = src ? <img src={src} alt="" width={size ?? 22} height={size ?? 22} /> : <JellyfishIcon size={size ?? 22} />;
  return <span className={cx('jc-logo', `jc-logo--${variant}`)}>{icon}</span>;
}

export function HeaderBrand({ name = 'JellyCast', logoSrc }) {
  return (
    <span className="jc-brand">
      <BrandLogo variant="tile" src={logoSrc} />
      <span className="text-brand">{name}</span>
    </span>
  );
}

export function FooterBrand({ name = '해수욕장 해파리 위험도', description = '해파리 출현 정보와 예측 지수를 한눈에', logoSrc }) {
  return (
    <span className="jc-brand jc-brand--footer">
      <BrandLogo variant="plain" src={logoSrc} size={24} />
      <span className="jc-brand__text">
        <span className="text-brand">{name}</span>
        <span className="text-body-small jc-c-muted">{description}</span>
      </span>
    </span>
  );
}

/* ───────────── 버튼/동작 ───────────── */
// variant: 'outline'(이용 안내) | 'primary'(검색) | 'update'(업데이트) | 'chip'(전국 보기)
export function Button({ variant = 'primary', icon, children, className, ...rest }) {
  return (
    <button type="button" className={cx('jc-btn', `jc-btn--${variant}`, className)} {...rest}>
      {icon}
      <span>{children}</span>
    </button>
  );
}
export const GuideButton = (p) => <Button variant="outline" {...p}>{p.children ?? '이용 안내'}</Button>;
export const SearchButton = (p) => <Button variant="primary" {...p}>{p.children ?? '검색'}</Button>;
export const UpdateButton = (p) => <Button variant="update" icon={<RefreshIcon size={20} />} {...p}>{p.children ?? '업데이트'}</Button>;
export const NationwideButton = (p) => <Button variant="chip" icon={<ExpandIcon size={16} />} {...p}>{p.children ?? '전국 보기'}</Button>;

/* 아이콘/새로고침 타일 (시트의 흰 정사각형 아이콘) */
export function RefreshTile(props) {
  return (
    <button type="button" className="jc-icon-tile" aria-label="새로고침" {...props}>
      <RefreshIcon size={18} />
    </button>
  );
}

/* ───────────── 탐색/메뉴항목 · 푸터링크 ───────────── */
export const NavItem = ({ href = '#', children, ...rest }) => (
  <a className="jc-nav__item text-navigation" href={href} {...rest}>{children}</a>
);
export const FooterLink = ({ href = '#', children, ...rest }) => (
  <a className="jc-footer__link text-body" href={href} {...rest}>{children}</a>
);

/* ───────────── 입력/날짜선택 ───────────── */
const toDots = (iso) => (iso ? iso.replaceAll('-', '.') : '');
export function DateInput({ value, onChange, label = '조회 날짜', ...rest }) {
  const ref = useRef(null);
  return (
    <label className="jc-date">
      <span className="text-button">{toDots(value)}</span>
      <CalendarIcon size={20} />
      <input
        ref={ref}
        type="date"
        aria-label={label}
        value={value ?? ''}
        onChange={(e) => onChange?.(e.target.value)}
        onClick={() => ref.current?.showPicker?.()}
        {...rest}
      />
    </label>
  );
}

/* 라벨 붙은 날짜선택 (최종 화면: 검색창 오른쪽 '조회 날짜') */
export function DateField({ label = '조회 날짜', value, onChange }) {
  return (
    <div className="jc-field">
      <span className="text-label jc-c-secondary">{label}</span>
      <DateInput value={value} onChange={onChange} label={label} />
    </div>
  );
}

/* ───────────── 입력/해수욕장검색 ───────────── */
const _norm = (s) => String(s ?? '').replace(/\s+/g, '').toLowerCase();

/* 자동완성: 입력하면 이름(앞글자 일치 우선) → 지역 순으로 최대 8곳 목록, ↑↓·Enter·Esc 지원 */
export function BeachSearch({ value, onChange, onSubmit, onPick, items = [], placeholder = '해수욕장명 또는 지역명을 검색하세요' }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const key = _norm(value);
  const matches = useMemo(() => {
    if (!key) return [];
    const starts = [], inName = [], inRegion = [];
    for (const b of items) {
      const n = _norm(b.name);
      if (n.startsWith(key)) starts.push(b);
      else if (n.includes(key)) inName.push(b);
      else if (_norm(b.region).includes(key)) inRegion.push(b);
    }
    return [...starts, ...inName, ...inRegion].slice(0, 8);
  }, [items, key]);
  const show = open && matches.length > 0;

  const pick = (b) => { onChange?.(b.name); onPick?.(b.id); setOpen(false); setActive(-1); };
  const onKeyDown = (e) => {
    if (!show) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => (i + 1) % matches.length); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => (i <= 0 ? matches.length - 1 : i - 1)); }
    else if (e.key === 'Escape') setOpen(false);
    else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); pick(matches[active]); }
  };

  return (
    <form className="jc-search" role="search" onSubmit={(e) => { e.preventDefault(); setOpen(false); onSubmit?.(value); }}>
      <SearchIcon size={20} className="jc-search__icon" />
      <input
        className="jc-search__input text-input"
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(e) => { onChange?.(e.target.value); setOpen(true); setActive(-1); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        aria-label="해수욕장 검색"
        role="combobox"
        aria-expanded={show}
        aria-controls="jc-search-list"
        autoComplete="off"
      />
      <Button variant="primary" type="submit">검색</Button>
      {show && (
        <ul id="jc-search-list" className="jc-suggest" role="listbox">
          {matches.map((b, i) => (
            <li key={b.id} role="option" aria-selected={i === active}
                className={`jc-suggest__item${i === active ? ' is-active' : ''}`}
                onMouseDown={(e) => { e.preventDefault(); pick(b); }}
                onMouseEnter={() => setActive(i)}>
              <span className="text-body">{b.name}</span>
              <span className="text-body-small jc-c-muted">{b.region}</span>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}

/* ───────────── 선택/지도표시기준 ───────────── */
export function MapBasisToggle({ value = 'average', onChange, disabled = false, options = [
  { value: 'average', label: '평년 출현율' },
  { value: 'forecast', label: '예측 위험 지수' },
] }) {
  return (
    <div className={cx('jc-toggle', disabled && 'is-disabled')} role="radiogroup" aria-label="지도색 기준">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          disabled={disabled}
          className={cx('jc-toggle__item text-button', value === o.value && 'is-selected')}
          onClick={() => onChange?.(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ───────────── 선택/예측기간 ───────────── */
export function PeriodTabs({ value = 1, onChange, disabled = false, options = [1, 2, 4] }) {
  return (
    <div className={cx('jc-tabs', disabled && 'is-disabled')} role="radiogroup" aria-label="예측 기간">
      {options.map((w) => (
        <button
          key={w}
          type="button"
          role="radio"
          aria-checked={value === w}
          disabled={disabled}
          className={cx('jc-tabs__item text-button', value === w && 'is-selected')}
          onClick={() => onChange?.(w)}
        >
          {w}주 뒤
        </button>
      ))}
    </div>
  );
}

/* ───────────── 범례/위험등급 ───────────── */
export const RISK_LEVELS = [
  { key: 'veryHigh', label: '매우 높음', range: '60% 이상', color: 'var(--color-risk-very-high)' },
  { key: 'high', label: '높음', range: '40% 이상 60% 미만', color: 'var(--color-risk-high)' },
  { key: 'medium', label: '보통', range: '20% 이상 40% 미만', color: 'var(--color-risk-medium)' },
  { key: 'low', label: '낮음', range: '0% 이상 20% 미만', color: 'var(--color-risk-low)' },
  { key: 'noData', label: '자료 없음 / 시즌 아님', range: '유효한 자료가 없거나 시즌 아님', color: 'var(--color-risk-no-data)' },
];
// columns={2} 이면 지도 카드 아래처럼 2열 격자로 배치
export function RiskLegend({ title, columns }) {
  return (
    <div className={cx('jc-legend', columns === 2 && 'jc-legend--grid')}>
      {title && <span className="text-label jc-c-secondary jc-legend__title">{title}</span>}
      {RISK_LEVELS.map((l) => (
        <span key={l.key} className="jc-legend__item">
          <i className="jc-dot" style={{ background: l.color }} />
          <span className="text-label">{l.label}</span>
          <span className="text-body-small jc-c-muted">{l.range}</span>
        </span>
      ))}
    </div>
  );
}

/* ───────────── 범례/그래프 ───────────── */
export const CHART_SERIES = [
  { key: 'total', label: '통합', color: 'var(--color-chart-total)' },
  { key: 'nomura', label: '노무라', color: 'var(--color-chart-nomura)' },
  { key: 'moon', label: '보름달', color: 'var(--color-chart-moon)' },
  { key: 'other', label: '기타', color: 'var(--color-chart-other)' },
];
export function ChartLegend({ series = CHART_SERIES }) {
  return (
    <div className="jc-legend jc-legend--chart">
      {series.map((s) => (
        <span key={s.key} className="jc-legend__item">
          <i className="jc-dot" style={{ background: s.color }} />
          <span className="text-body-small jc-c-secondary">{s.label}</span>
        </span>
      ))}
    </div>
  );
}

/* ───────────── 정보/종별출현율항목 ───────────── */
export function SpeciesRateRow({ name, value }) {
  return (
    <div className="jc-species-row">
      <span className="text-body jc-c-secondary">{name}</span>
      <span className="text-button">{value}</span>
    </div>
  );
}

/* ───────────── 정보/항목 ───────────── */
export function InfoRow({ label, value, loadingWidth }) {
  return (
    <div className="jc-info-row">
      <span className="text-body-small jc-c-secondary">{label}</span>
      {loadingWidth ? <Skeleton width={loadingWidth} height={12} /> : value != null && <span className="text-label">{value}</span>}
    </div>
  );
}

/* ───────────── 정보/조회기준 ───────────── */
export function QueryBasis({ label = '조회 기준', value }) {
  return (
    <span className="jc-query-basis">
      <span className="text-label-medium jc-c-muted">{label}</span>
      <span className="text-button">{value}</span>
    </span>
  );
}

/* ───────────── 안내/지도선택 ───────────── */
export function MapGuide({ children = '지도에서 해수욕장을 선택해 정보를 확인하세요.', tall = false }) {
  return <div className={cx('jc-guide text-body-small', tall && 'jc-guide--tall')}>{children}</div>;
}

/* ───────────── 배지/위험등급 · 배지/데이터상태 ───────────── */
const BADGE_LABEL = { veryHigh: '매우 높음', high: '높음', medium: '보통', low: '낮음', noData: '자료 없음' };
// level 을 직접 주거나, percent(0~100)를 주면 riskLevel() 로 계산
export function RiskBadge({ level, percent }) {
  const key = level ?? riskLevel(percent).key;
  return <span className={cx('jc-badge text-badge', `jc-badge--${key}`)}>{BADGE_LABEL[key]}</span>;
}
export function DataStatusBadge({ children = '예시 데이터' }) {
  return <span className="jc-badge-example text-example-badge">{children}</span>;
}

/* ───────────── 정보/기간별예측 ───────────── */
// items: [{ weeks:1, week:'11월 3주', percent:12.1 }, ...]
export function PeriodForecast({ items = [], loading = false }) {
  const cols = loading ? [{ weeks: 1 }, { weeks: 2 }, { weeks: 4 }] : items;
  return (
    <div className={cx('jc-period', loading && 'jc-period--loading')}>
      {cols.map((it) => (
        <div key={it.weeks} className="jc-period__col">
          <span className="text-navigation jc-c-secondary">{it.weeks}주 뒤</span>
          {loading ? (
            <>
              <Skeleton width={48} height={8} className="jc-mt-8" />
              <Skeleton width={64} height={28} tone="highlight" radius={8} className="jc-mt-16" />
              <Skeleton width={48} height={28} radius={8} className="jc-mt-12" />
            </>
          ) : (
            <>
              <span className="text-body-small jc-c-muted jc-mt-4">{it.week}</span>
              <span className="text-forecast-metric jc-mt-12">{formatPct(it.percent)}</span>
              <span className="jc-mt-8"><RiskBadge percent={it.percent} /></span>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
export const formatPct = (v) => (v == null || Number.isNaN(v) ? '–' : `${Number(v).toFixed(1)}%`);

/* ───────────── 지도/선택마커 · 이름표 · 확대축소 ───────────── */
export const MapMarker = ({ style }) => <span className="jc-marker" style={style} aria-hidden />;
export const MapLabel = ({ children, style }) => <span className="jc-map-label text-button" style={style}>{children}</span>;
export function ZoomControls({ onZoomIn, onZoomOut, disabled = false }) {
  return (
    <div className="jc-zoom">
      <button type="button" className="jc-zoom__btn text-map-control" aria-label="확대" onClick={onZoomIn} disabled={disabled}>+</button>
      <button type="button" className="jc-zoom__btn text-map-control" aria-label="축소" onClick={onZoomOut} disabled={disabled}>−</button>
    </div>
  );
}

/* ───────────── 로딩/기본요소 ───────────── */
// tone: 'base'(#303036) | 'highlight'(#404048)
export function Skeleton({ width, height = 12, radius, tone = 'base', className, style }) {
  return (
    <span
      className={cx('jc-skeleton', tone === 'highlight' && 'jc-skeleton--highlight', className)}
      style={{ width, height, borderRadius: radius ?? Math.min(height / 2, 8), ...style }}
      aria-hidden
    />
  );
}
export function LoadingIndicator({ children = '불러오는 중' }) {
  return (
    <span className="jc-loading" role="status">
      <span className="jc-loading__dots" aria-hidden><i /><i /><i /></span>
      <span className="text-body-small jc-c-secondary">{children}</span>
    </span>
  );
}
