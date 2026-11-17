/* 최종 화면(메인 · 수정 카드 로딩 상태) 기준 영역·카드
   모든 카드는 loading prop 하나로 로딩 화면으로 바뀐다. */
import {
  HeaderBrand, FooterBrand, NavItem, FooterLink, GuideButton, NationwideButton, Button,
  MapBasisToggle, PeriodTabs, RiskLegend, ChartLegend, CHART_SERIES,
  SpeciesRateRow, InfoRow, MapGuide, RiskBadge, DataStatusBadge, PeriodForecast,
  ZoomControls, Skeleton, LoadingIndicator, formatPct, BrandLogo,
} from './basics.jsx';
import { RefreshIcon } from './icons.jsx';

const cx = (...c) => c.filter(Boolean).join(' ');

/* ───────────── 영역/서비스헤더 ───────────── */
export function ServiceHeader({ menus = ['위험정보', '예측 지수', '관측 정보', '지표 안내'], onGuide }) {
  return (
    <header className="jc-header">
      <HeaderBrand />
      <nav className="jc-nav surface-navigation" aria-label="주요 메뉴">
        {menus.map((m) => <NavItem key={m}>{m}</NavItem>)}
      </nav>
      <GuideButton onClick={onGuide} />
    </header>
  );
}

/* ───────────── 영역/서비스소개 ───────────── */
export function ServiceIntro({
  eyebrow = 'JELLYFISH RISK MONITOR',
  title = '해수욕장 해파리 위험도',
  description = '해수욕장별 출현 정보와 예측 위험 지수를 확인하세요.',
}) {
  return (
    <section className="jc-intro">
      <p className="text-eyebrow jc-c-secondary">{eyebrow}</p>
      <h1 className="text-display">{title}</h1>
      <p className="text-body-large jc-c-secondary">{description}</p>
    </section>
  );
}

/* 카드 공통 머리: 제목 + (오른쪽) 보조문구 또는 '불러오는 중' */
function CardHead({ title, titleClass = 'text-section-title', aside, loading }) {
  return (
    <div className="jc-card__head">
      <span className={titleClass}>{title}</span>
      {loading ? <LoadingIndicator /> : aside}
    </div>
  );
}

/* 해수욕장 카드 아래쪽: 지도색 기준 · 예측 기간 · 안내 */
function MapControls({ basis, onBasisChange, weeks, onWeeksChange, loading, guide }) {
  return (
    <div className="jc-summary__controls">
      <span className="text-label jc-c-secondary">지도색 기준</span>
      <MapBasisToggle value={basis} onChange={onBasisChange} disabled={loading} />
      <span className="jc-field__label jc-mt-16">
        <span className="text-label jc-c-secondary">예측 기간</span>
        <span className="text-caption-wide jc-c-hint">예측 위험 지수 선택 시 적용</span>
      </span>
      <PeriodTabs value={weeks} onChange={onWeeksChange} disabled={loading} />
      <div className="jc-mt-8"><MapGuide>{loading ? '정보를 불러오는 중이에요.' : guide}</MapGuide></div>
    </div>
  );
}

/* ───────────── 카드/해수욕장요약 (336×760) ─────────────
   beach: { name, region, size, weekLabel, averagePercent, species:[{name,value}] } */
export function BeachSummaryCard({
  beach, loading = false,
  basis = 'average', onBasisChange, weeks = 1, onWeeksChange,
  guide = '지도에서 해수욕장을 선택해 정보를 확인하세요.',
}) {
  const controls = (
    <MapControls basis={basis} onBasisChange={onBasisChange} weeks={weeks} onWeeksChange={onWeeksChange} loading={loading} guide={guide} />
  );
  if (loading) {
    return (
      <article className="jc-card jc-summary" aria-busy="true">
        <CardHead title="선택한 해수욕장" titleClass="text-body jc-c-secondary" loading />
        <Skeleton width={176} height={32} radius={8} tone="highlight" className="jc-mt-12" />
        <Skeleton width={208} height={12} className="jc-mt-16" />
        <Skeleton width={144} height={12} className="jc-mt-16" />
        <hr className="jc-divider jc-mt-32" />
        <span className="text-label jc-c-secondary jc-mt-24">평년 출현율</span>
        <div className="jc-summary__metric jc-mt-16">
          <Skeleton width={176} height={56} radius={8} tone="highlight" />
          <Skeleton width={48} height={28} radius={8} />
        </div>
        <span className="text-label jc-mt-40">종별 출현율</span>
        <div className="jc-summary__species jc-summary__species--loading">
          {[144, 104, 64].map((w) => (
            <div key={w} className="jc-species-row jc-species-row--loading">
              <Skeleton width={w} height={12} />
              <Skeleton width={40} height={12} />
            </div>
          ))}
        </div>
        {controls}
      </article>
    );
  }
  return (
    <article className="jc-card jc-summary">
      <span className="text-eyebrow jc-c-secondary">선택한 해수욕장</span>
      <h2 className="text-beach-title jc-mt-8">{beach.name}</h2>
      <span className="text-body jc-c-secondary jc-mt-8">{beach.region}</span>
      <span className="text-body jc-c-muted jc-mt-8">{beach.size}</span>
      <hr className="jc-divider jc-mt-24" />
      <span className="text-eyebrow jc-c-secondary jc-mt-24">{beach.weekLabel} 평년 출현율</span>
      <div className="jc-summary__metric jc-mt-8">
        <span className="text-metric">{formatPct(beach.averagePercent)}</span>
        <RiskBadge percent={beach.averagePercent} />
      </div>
      <span className="text-brand jc-mt-32">종별 출현율</span>
      <div className="jc-summary__species">
        {beach.species.map((s) => <SpeciesRateRow key={s.name} name={s.name} value={formatPct(s.value)} />)}
      </div>
      {controls}
    </article>
  );
}

/* ───────────── 카드/해수욕장지도 (528×760, 지도 480×512 + 위험등급 범례) ─────────────
   children 자리에 Leaflet·카카오맵 등 실제 지도를 넣는다. */
export function BeachMapCard({ loading = false, onNationwide, onZoomIn, onZoomOut, children, attribution }) {
  return (
    <article className="jc-card jc-map-card" aria-busy={loading || undefined}>
      <div className="jc-card__head jc-card__head--start">
        <div className="jc-stack-4">
          <span className={loading ? 'text-body' : 'text-eyebrow jc-c-secondary'}>해수욕장 지도</span>
          <span className={cx('jc-c-secondary', loading ? 'text-body-small' : 'text-body')}>
            {loading ? '위치 정보를 불러오고 있어요.' : '선택한 해수욕장의 위치를 확인하세요.'}
          </span>
        </div>
        <NationwideButton onClick={onNationwide} disabled={loading} />
      </div>
      <div className={cx('jc-map', loading && 'jc-map--loading')}>
        {loading ? <LoadingIndicator /> : children}
        <div className="jc-map__zoom"><ZoomControls onZoomIn={onZoomIn} onZoomOut={onZoomOut} disabled={loading} /></div>
        {!loading && attribution && <div className="jc-map__attribution text-map-caption">{attribution}</div>}
      </div>
      {!loading && (
        <div className="jc-map-card__legend">
          <span className="text-label jc-c-secondary">위험등급</span>
          <RiskLegend columns={2} />
        </div>
      )}
    </article>
  );
}

/* ───────────── 카드/예측위험지수 (432×328, 로딩 292) ─────────────
   forecast: { items:[{weeks,week,percent}], reportDate } */
export function ForecastCard({ forecast, loading = false }) {
  return (
    <article className={cx('jc-card jc-forecast', loading && 'is-loading')} aria-busy={loading || undefined}>
      <CardHead
        title="예측 위험 지수"
        loading={loading}
        aside={<span className="text-body-small jc-c-muted">1·2·4주 뒤 예측 정보</span>}
      />
      <div className="jc-mt-24"><PeriodForecast items={forecast?.items} loading={loading} /></div>
      <div className={cx('jc-forecast__foot', !loading && 'jc-forecast__foot--line')}>
        <InfoRow label="예측 기준 보고서" value={forecast?.reportDate} loadingWidth={loading ? 80 : undefined} />
      </div>
    </article>
  );
}

/* ───────────── 카드/관측산출정보 (432×328, 로딩 364) ─────────────
   obs: { reportDate, regionName, regionRate, station, stationDistance, weekLabel, avgTemp, latestLabel, latestTemp } */
export function ObservationCard({ obs, loading = false }) {
  const L = (w) => (loading ? w : undefined);
  return (
    <article className={cx('jc-card jc-obs', loading && 'is-loading')} aria-busy={loading || undefined}>
      <CardHead title="관측·산출 정보" loading={loading} />
      <section className="jc-obs__group">
        <h3 className="text-button">최근 주간보고</h3>
        <div className="jc-obs__rows">
          <InfoRow label="보고서 기준일" value={obs?.reportDate} loadingWidth={L(80)} />
          <InfoRow label={loading ? '권역 통합 출현율' : `${obs.regionName} 통합 출현율`} value={obs && formatPct(obs.regionRate)} loadingWidth={L(48)} />
        </div>
      </section>
      <hr className="jc-divider jc-obs__divider" />
      <section className="jc-obs__group jc-obs__group--station">
        <h3 className="text-button">연결 관측소</h3>
        <div className="jc-obs__rows jc-obs__rows--wide">
          <InfoRow label={loading ? '관측소·거리' : obs.station} value={obs?.stationDistance} loadingWidth={L(112)} />
          <InfoRow label={loading ? '평년 수온' : `${obs.weekLabel} 평년 수온`} value={obs?.avgTemp} loadingWidth={L(56)} />
          <InfoRow label={loading ? '최근 관측 수온' : obs.latestLabel} value={obs?.latestTemp} loadingWidth={L(64)} />
        </div>
      </section>
    </article>
  );
}

/* ───────────── 업데이트 버튼 (오른쪽 열 맨 아래, 432×56) ───────────── */
export function UpdateBar({ onClick, loading = false }) {
  return (
    <Button variant="update" className="jc-btn--block" icon={<RefreshIcon size={20} />} onClick={onClick} disabled={loading}>
      업데이트
    </Button>
  );
}

/* ───────────── 안내/예측산출기준 (1344×144) ───────────── */
export function ForecastNotice({ message, model, loading = false }) {
  if (loading) {
    return (
      <section className="jc-notice jc-notice--loading" aria-busy="true">
        <div className="jc-card__head">
          <span className="text-body jc-c-secondary">예측 정보 안내</span>
          <LoadingIndicator />
        </div>
        <Skeleton width={520} height={20} radius={10} tone="highlight" className="jc-mt-16" />
        <Skeleton width={288} height={12} className="jc-mt-12" />
      </section>
    );
  }
  return (
    <section className="jc-notice">
      <div className="jc-stack-8">
        <span className="text-label jc-c-secondary">예측 정보 안내</span>
        <p className="text-section-subtitle">{message}</p>
      </div>
      <span className="text-body jc-c-secondary">{model}</span>
    </section>
  );
}

/* ───────────── 차트/평년출현율 (1344×360) ─────────────
   data: [{ label:'5월 1주', total, nomura, moon, other }, ... 32주], selectedIndex: 선택한 주 */
export function SeasonChartCard({ title, data = [], selectedIndex, isExample = false, loading = false }) {
  return (
    <article className="jc-card jc-chart-card" aria-busy={loading || undefined}>
      <div className="jc-card__head jc-card__head--start">
        <div className="jc-stack-4">
          <span className="jc-chart-card__title">
            <span className="text-section-title">{loading ? '주차별 평년 출현율' : title}</span>
            {!loading && isExample && <DataStatusBadge />}
          </span>
          <span className={cx('text-body-small', loading ? 'jc-c-secondary' : 'jc-c-muted')}>
            {loading
              ? '주차별 출현율 정보를 불러오고 있어요.'
              : isExample
                ? '주차별 실제 데이터가 제공되지 않아 시안 확인용 예시 데이터로 표시합니다.'
                : '5~12월 주차별 평년 출현율입니다.'}
          </span>
        </div>
        <ChartLegend />
      </div>
      {loading ? <ChartSkeleton /> : <LineChart data={data} selectedIndex={selectedIndex} />}
    </article>
  );
}

function ChartSkeleton() {
  return (
    <div className="jc-chart-skeleton">
      {[0, 1, 2, 3].map((i) => <span key={i} className="jc-chart-skeleton__grid" style={{ top: 48 + i * 48 }} />)}
      <LoadingIndicator />
      <div className="jc-chart-skeleton__axis">
        {Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} width={32} height={8} />)}
      </div>
    </div>
  );
}

/* 의존성 없는 SVG 꺾은선 그래프 (시안 치수: 1296×220) */
export function LineChart({ data, selectedIndex, width = 1296, height = 220, series = CHART_SERIES }) {
  const L = 48, R = 1280, T = 8, B = 180;
  const n = Math.max(data.length, 2);
  const x = (i) => L + ((R - L) * i) / (n - 1);
  const y = (v) => B - ((B - T) * Math.max(0, Math.min(100, v ?? 0))) / 100;
  const ticks = data.map((d, i) => ({ i, label: d.label })).filter((t) => t.label?.endsWith(' 1주') || t.i === data.length - 1);
  return (
    <svg className="jc-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="주차별 평년 출현율 그래프">
      {[0, 25, 50, 75, 100].map((v) => (
        <g key={v}>
          <line x1={L} x2={R} y1={y(v)} y2={y(v)} stroke="var(--color-chart-grid)" strokeWidth="1" />
          <text x={L - 8} y={y(v) + 4} textAnchor="end" className="jc-chart__axis">{v}%</text>
        </g>
      ))}
      {ticks.map((t) => (
        <text key={t.i} x={x(t.i)} y={B + 24} textAnchor="middle" className="jc-chart__axis">{t.label}</text>
      ))}
      {selectedIndex != null && (
        <g>
          <line x1={x(selectedIndex)} x2={x(selectedIndex)} y1={T - 4} y2={B} stroke="var(--color-chart-selected-line)" strokeDasharray="3 3" strokeWidth="1.5" />
          <text x={x(selectedIndex) + 8} y={T + 8} className="jc-chart__axis jc-chart__axis--selected">선택한 주</text>
        </g>
      )}
      {[...series].reverse().map((s) => {
        const pts = data.map((d, i) => [x(i), y(d[s.key])]);
        const isTotal = s.key === 'total';
        return (
          <g key={s.key}>
            <polyline points={pts.map((p) => p.join(',')).join(' ')} fill="none" stroke={s.color} strokeWidth={isTotal ? 2 : 1.5} strokeLinejoin="round" />
            {pts.map(([px, py], i) => (
              <circle key={i} cx={px} cy={py} r={isTotal ? 3.5 : 2.5} fill={isTotal ? 'var(--color-foreground-primary)' : s.color} stroke="var(--color-background-card)" strokeWidth="1.5" />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

/* ───────────── 영역/서비스푸터 ───────────── */
export function ServiceFooter({ links = ['데이터 출처', '모델 안내', '이용 안내'] }) {
  return (
    <footer className="jc-footer">
      <FooterBrand />
      <nav className="jc-footer__links" aria-label="푸터 링크">
        {links.map((l) => <FooterLink key={l}>{l}</FooterLink>)}
      </nav>
    </footer>
  );
}

/* ───────────── 해파리 AI 가이드 (챗봇 열기 버튼, 오른쪽 아래) ───────────── */
export function ChatbotLauncher({ onOpen, imageSrc }) {
  return (
    <button type="button" className="jc-chatbot" onClick={onOpen} aria-label="해파리 AI 가이드 열기">
      <span className="jc-chatbot__bubble">
        <span className="text-brand jc-c-inverse">해파리 AI 가이드</span>
        <span className="text-body jc-c-tooltip">궁금한 점을 물어보세요</span>
      </span>
      <span className="jc-chatbot__avatar">
        {imageSrc ? <img src={imageSrc} alt="" /> : <span className="jc-chatbot__fallback"><BrandLogo variant="plain" size={44} /></span>}
        <span className="jc-chatbot__label text-label">AI 챗봇</span>
      </span>
    </button>
  );
}

/* 페이지 배경 유리 곡면 2개 */
export function GlassBackdrop() {
  return (
    <div className="jc-glass-layer" aria-hidden>
      <div className="glass-top jc-glass-layer__top" />
      <div className="glass-bottom jc-glass-layer__bottom" />
    </div>
  );
}
