/* 개발용: Figma 컴포넌트 시트와 같은 순서로 모든 컴포넌트를 모아 보는 화면 (주소 뒤 #sheet) */
import { useState } from 'react';
import {
  ServiceHeader, ServiceIntro, BeachSearch, DateField, QueryBasis, UpdateBar,
  BeachSummaryCard, BeachMapCard, ForecastCard, ObservationCard, ForecastNotice, SeasonChartCard,
  ServiceFooter, ChatbotLauncher, GlassBackdrop, MapMarker, MapLabel,
  // 시트 보기용 기본 조각
  SearchIcon, CalendarIcon, RefreshTile, ExpandIcon, BrandLogo, HeaderBrand, FooterBrand, NavItem, FooterLink,
  GuideButton, SearchButton, UpdateButton, NationwideButton, DateInput, MapBasisToggle, PeriodTabs,
  RiskLegend, ChartLegend, SpeciesRateRow, InfoRow, PeriodForecast, MapGuide, ZoomControls,
  RiskBadge, DataStatusBadge, Skeleton, LoadingIndicator,
} from '../components';
import {
  sampleBeach, sampleForecast, sampleObservation, sampleNotice, sampleSeason, sampleSelectedIndex,
} from '../data/sample.js';

/* 실제 지도 대신 쓰는 자리표시 (Leaflet 등으로 교체) */
function MapPlaceholder() {
  return (
    <div className="demo-map">
      <MapLabel style={{ position: 'absolute', left: 150, top: 286 }}>화진해수욕장</MapLabel>
      <MapMarker style={{ position: 'absolute', left: 183, top: 330 }} />
      <span className="demo-map__note text-body-small">지도 영역 · BeachMapCard 안에 Leaflet/카카오맵을 넣으세요</span>
    </div>
  );
}

/* Figma 컴포넌트 시트와 같은 순서로 모아 보기 */
export default function Sheet() {
  const [date, setDate] = useState('2026-11-11');
  const [basis, setBasis] = useState('average');
  const [weeks, setWeeks] = useState(1);
  const S = ({ name, children, row }) => (
    <section className="demo-sheet__item">
      <h2 className="demo-sheet__name">{name}</h2>
      <div className={row ? 'demo-sheet__row' : undefined}>{children}</div>
    </section>
  );
  return (
    <div className="demo-sheet">
      <S name="아이콘/검색"><SearchIcon /></S>
      <S name="탐색/메뉴항목"><NavItem>위험정보</NavItem></S>
      <S name="아이콘/달력"><CalendarIcon /></S>
      <S name="아이콘/새로고침"><RefreshTile /></S>
      <S name="아이콘/전국보기"><ExpandIcon size={20} /></S>
      <S name="브랜드/로고" row><BrandLogo variant="tile" /><BrandLogo variant="plain" /></S>
      <S name="탐색/푸터링크"><FooterLink>데이터 출처</FooterLink></S>
      <S name="버튼/동작" row><GuideButton /><SearchButton /><UpdateButton /><NationwideButton /></S>
      <S name="입력/날짜선택"><DateField value={date} onChange={setDate} /></S>
      <S name="선택/지도표시기준"><MapBasisToggle value={basis} onChange={setBasis} /></S>
      <S name="선택/예측기간"><PeriodTabs value={weeks} onChange={setWeeks} /></S>
      <S name="범례/위험등급"><RiskLegend /></S>
      <S name="정보/종별출현율항목"><div style={{ width: 288 }}><SpeciesRateRow name="노무라입깃(유해)" value="2.4%" /></div></S>
      <S name="정보/항목"><div style={{ width: 384 }}><InfoRow label="보고서 기준일" value="2026.10.30" /></div></S>
      <S name="지도/선택마커"><MapMarker /></S>
      <S name="지도/이름표"><MapLabel>화진해수욕장</MapLabel></S>
      <S name="배지/데이터상태"><DataStatusBadge /></S>
      <S name="범례/그래프"><ChartLegend /></S>
      <S name="브랜드/헤더표시"><HeaderBrand /></S>
      <S name="브랜드/푸터표시"><FooterBrand /></S>
      <S name="입력/해수욕장검색"><BeachSearch /></S>
      <S name="정보/기간별예측"><div style={{ width: 384 }}><PeriodForecast items={sampleForecast.items} /></div></S>
      <S name="안내/지도선택"><div style={{ width: 288 }}><MapGuide /></div></S>
      <S name="정보/조회기준"><QueryBasis value="2026.11.11 · 11월 2주" /></S>
      <S name="지도/확대축소"><ZoomControls /></S>
      <S name="배지/위험등급" row>
        <div className="demo-dark-box">
          {['veryHigh', 'high', 'medium', 'low', 'noData'].map((l) => <RiskBadge key={l} level={l} />)}
        </div>
      </S>
      <S name="로딩/기본요소" row>
        <Skeleton width={120} height={16} /><Skeleton width={120} height={16} tone="highlight" />
        <div className="demo-dark-box"><LoadingIndicator /></div>
      </S>
      <S name="카드/해수욕장요약 (기본 · 로딩)" row>
        <div style={{ width: 336, height: 760, display: 'flex' }}><BeachSummaryCard beach={sampleBeach} /></div>
        <div style={{ width: 336, height: 760, display: 'flex' }}><BeachSummaryCard loading /></div>
      </S>
      <S name="카드/예측위험지수 (기본 · 로딩)" row>
        <div style={{ width: 432 }}><ForecastCard forecast={sampleForecast} /></div>
        <div style={{ width: 432 }}><ForecastCard loading /></div>
      </S>
      <S name="카드/관측산출정보 (기본 · 로딩)" row>
        <div style={{ width: 432 }}><ObservationCard obs={sampleObservation} /></div>
        <div style={{ width: 432 }}><ObservationCard loading /></div>
      </S>
      <S name="안내/예측산출기준 (기본 · 로딩)">
        <div className="demo-stack"><ForecastNotice {...sampleNotice} /><ForecastNotice loading /></div>
      </S>
      <S name="차트/평년출현율 (로딩)"><SeasonChartCard loading /></S>
      <S name="카드/해수욕장지도 (기본 · 로딩)" row>
        <div style={{ width: 528 }}><BeachMapCard attribution="Leaflet | © OpenStreetMap"><MapPlaceholder /></BeachMapCard></div>
        <div style={{ width: 528 }}><BeachMapCard loading /></div>
      </S>
      <S name="버튼/업데이트 (기본 · 로딩)" row>
        <div style={{ width: 432 }}><UpdateBar /></div>
        <div style={{ width: 432 }}><UpdateBar loading /></div>
      </S>
    </div>
  );
}

