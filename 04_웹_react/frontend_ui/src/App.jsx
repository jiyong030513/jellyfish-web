/* 젤리캐스트 메인 화면 — Figma 최종 시안(메인 화면 · 수정 카드 로딩 상태) 배치
   데이터 흐름은 hooks/useJellyCast.js, 서버 연결은 api/client.js 에 있다. */
import { lazy, Suspense, useRef, useState } from 'react';
import {
  ServiceHeader, ServiceIntro, BeachSearch, DateField, QueryBasis, UpdateBar,
  BeachSummaryCard, BeachMapCard, ForecastCard, ObservationCard, ForecastNotice, SeasonChartCard, TopRiskCard,
  ServiceFooter, ChatbotLauncher, ChatPanel, GlassBackdrop, BeachMap,
} from './components';
import { useJellyCast } from './hooks/useJellyCast.js';
import { InfoModal } from './components/InfoModal.jsx';
import { toDots, weekLabel } from './api/week.js';

const Sheet = lazy(() => import('./dev/Sheet.jsx'));

const ATTRIBUTION = (
  <>
    <a href="https://leafletjs.com" target="_blank" rel="noreferrer">Leaflet</a>
    {' | © '}
    <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>
  </>
);

function JellyCastPage({ forceLoading = false }) {
  const j = useJellyCast();
  const mapRef = useRef(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [info, setInfo] = useState(null); // 위쪽 메뉴 팝업: '데이터 출처' | '모델 안내' | '관측소 정보'

  const cardsLoading = forceLoading || j.loading;
  const mapLoading = forceLoading || j.listLoading;
  const d = j.detail;
  const guide = j.error && !d ? '정보를 불러오지 못했어요. 업데이트를 눌러 다시 시도해 주세요.' : j.guide;

  return (
    <div className="demo-page surface-page">
      <GlassBackdrop />
      <div className="demo-container">
        <ServiceHeader onMenu={setInfo} onGuide={() => setInfo('이용 안내')} />
        <ServiceIntro eyebrow={null} />

        <div className="demo-search-row">
          <div className="demo-search-row__inputs">
            <BeachSearch value={j.query} onChange={j.setQuery} onSubmit={j.search} />
            <DateField value={j.date} onChange={(v) => v && j.setDate(v)} />
          </div>
          <QueryBasis value={`${toDots(j.date)} · ${weekLabel(j.date)}`} />
        </div>

        <div className="demo-grid">
          <BeachSummaryCard
            beach={d?.beach}
            loading={cardsLoading}
            basis={j.basis} onBasisChange={j.setBasis}
            weeks={j.weeks} onWeeksChange={j.setWeeks}
            guide={guide}
          />
          <BeachMapCard
            loading={mapLoading}
            attribution={ATTRIBUTION}
            onNationwide={() => mapRef.current?.showAll()}
            onZoomIn={() => mapRef.current?.zoomIn()}
            onZoomOut={() => mapRef.current?.zoomOut()}
          >
            <BeachMap
              ref={mapRef}
              beaches={j.beaches}
              selectedId={j.selectedId}
              percentOf={j.percentOf}
              onSelect={j.select}
            />
          </BeachMapCard>
          <div className="demo-col">
            <ForecastCard forecast={d?.forecast} loading={cardsLoading} />
            <ObservationCard obs={d?.obs} loading={cardsLoading} />
            <UpdateBar loading={cardsLoading || mapLoading} onClick={j.refresh} />
          </div>
        </div>

        <div className="jc-mt-24"><TopRiskCard top={j.top} selectedId={j.selectedId} onSelect={j.select} /></div>
        <div className="jc-mt-24"><ForecastNotice {...d?.notice} loading={cardsLoading} /></div>
        <div className="jc-mt-24">
          <SeasonChartCard
            title={d ? `${d.beach.name} 5~12월 평년 출현율` : ''}
            data={d?.season.data}
            selectedIndex={d?.season.selectedIndex}
            isExample={d?.season.isExample}
            loading={cardsLoading}
          />
        </div>
        <div className="jc-mt-72"><ServiceFooter /></div>
      </div>

      {chatOpen
        ? <ChatPanel open onClose={() => setChatOpen(false)} beach={j.selected} horizonWeeks={j.weeks} date={j.date}
            onPick={(id) => { j.select(id); if (window.innerWidth < 720) setChatOpen(false); }} />
        : <ChatbotLauncher onOpen={() => setChatOpen(true)} imageSrc="/jellyfish.png" />}
      {info && <InfoModal topic={info} onClose={() => setInfo(null)} obs={d?.obs} beachName={d?.beach.name} />}
    </div>
  );
}

/* 개발 중에만 보이는 전환 버튼 (npm run build 결과물에는 나오지 않음) */
function DevToolbar({ view, setView, forceLoading, setForceLoading }) {
  return (
    <div className="demo-toolbar">
      <button type="button" className={view === 'page' ? 'is-on' : ''} onClick={() => setView('page')}>화면</button>
      <button type="button" className={view === 'sheet' ? 'is-on' : ''} onClick={() => setView('sheet')}>컴포넌트 시트</button>
      {view === 'page' && (
        <button type="button" className={forceLoading ? 'is-on' : ''} onClick={() => setForceLoading((v) => !v)}>
          로딩 화면 {forceLoading ? '끄기' : '고정'}
        </button>
      )}
    </div>
  );
}

export default function App() {
  const [view, setView] = useState(() => (location.hash === '#sheet' ? 'sheet' : 'page'));
  const [forceLoading, setForceLoading] = useState(() => location.hash === '#loading');
  const showDev = import.meta.env.DEV || location.hash === '#dev';
  return (
    <>
      {showDev && <DevToolbar view={view} setView={setView} forceLoading={forceLoading} setForceLoading={setForceLoading} />}
      {view === 'sheet'
        ? <Suspense fallback={null}><Sheet /></Suspense>
        : <JellyCastPage forceLoading={forceLoading} />}
    </>
  );
}
