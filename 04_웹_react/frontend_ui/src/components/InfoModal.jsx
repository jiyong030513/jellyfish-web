/* 위쪽 메뉴(데이터 출처 · 모델 안내 · 관측소 정보)를 누르면 뜨는 설명 팝업
   바깥을 누르거나 Esc · × 로 닫힌다. */
import { useEffect } from 'react';

const Row = ({ title, children }) => (
  <div className="jc-info__row">
    <span className="text-button">{title}</span>
    <span className="text-body jc-c-secondary">{children}</span>
  </div>
);

function Content({ topic, obs, beachName }) {
  if (topic === '데이터 출처') {
    return (
      <>
        <Row title="해파리 출현">국립수산과학원 「해파리 주간보고」의 권역별 출현율 (2014년 9월부터 매주)</Row>
        <Row title="해양 관측">기상청 해양기상부이의 수온 · 기온 · 풍속 · 유의파고 (주 평균)</Row>
        <Row title="해수욕장별 가중치">국립수산과학원 해파리 모니터링 설문 (어업인 목격 응답, 해수욕장 반경 30km)</Row>
        <Row title="AI 가이드 대비 수칙">보건복지부 · 중앙응급의료센터, 행정안전부, 국립수산과학원 등 공공기관 자료</Row>
        <Row title="지도">OpenStreetMap</Row>
        <p className="text-body-small jc-c-muted jc-info__note">새 주간보고가 발표되면 DB에 추가하고 예측을 다시 계산합니다.</p>
      </>
    );
  }
  if (topic === '이용 안내') {
    return (
      <>
        <Row title="1. 해수욕장 찾기">검색창에 해수욕장 이름이나 지역명을 입력하거나, 지도의 점을 누르세요.</Row>
        <Row title="2. 날짜 고르기">조회 날짜를 바꾸면 그 날짜를 기준으로 출현율과 1·2·4주 뒤 예측을 보여 줍니다.</Row>
        <Row title="3. 지도 색 바꾸기">지도색 기준에서 '평년 출현율' 또는 '예측 위험 지수'를 고르고, 예측 기간(1·2·4주 뒤)을 선택하세요.</Row>
        <Row title="4. 정보 읽기">왼쪽은 그 주 평년 출현율과 종류별 출현율, 오른쪽은 예측 위험 지수와 최근 주간보고 · 연결 관측소, 아래 그래프는 5~12월 시기별 출현율입니다.</Row>
        <Row title="5. 위험 상위 10곳">위험 지수가 높은 해수욕장 순서입니다. 줄을 누르면 그 해수욕장으로 이동합니다.</Row>
        <Row title="6. AI 가이드">오른쪽 아래 해파리를 누르면 예보 · 쏘임 대처 · 예방 수칙을 물어볼 수 있습니다. 답에 나온 📍 해수욕장을 누르면 지도가 이동하고, 응급 증상이면 119 안내가 나옵니다.</Row>
        <Row title="7. 업데이트">가장 최근 자료로 화면을 다시 불러옵니다.</Row>
        <p className="text-body-small jc-c-muted jc-info__note">위험 지수는 해수욕장끼리 비교하는 참고용 지수입니다. 입수 여부는 현장 안전요원과 해수욕장 안내를 따르세요.</p>
      </>
    );
  }
  if (topic === '모델 안내') {
    return (
      <>
        <Row title="무엇을 예측하나요">권역별로 1·2·4주 뒤 대량출현(통합 출현율 50% 이상)이 새로 시작될 가능성</Row>
        <Row title="예측 모델">로지스틱 회귀. 최근 출현율과 변화, 연중 주차, 수온 · 평년 대비 수온, 기온, 풍속, 파고 등 11개 값을 사용합니다.</Row>
        <Row title="위험 지수">권역 대량출현 확률 × 해수욕장 가중치(주변 목격 비율을 권역 평균과 비교한 값). 해수욕장끼리 비교하는 상대 지수이며 실제 확률은 아닙니다. 최대 100%로 표시합니다.</Row>
        <Row title="평년 기준 전망">최근 2주 안에 주간보고가 없거나 이미 대량출현 중이면, 과거 같은 시기에 대량출현이었던 비율 × 해수욕장 가중치로 안내합니다.</Row>
        <Row title="위험 등급">낮음 20% 미만 · 보통 20~40% · 높음 40~60% · 매우 높음 60% 이상</Row>
      </>
    );
  }
  return (
    <>
      <Row title="관측소">기상청 해양기상부이 7곳 (덕적도 · 외연도 · 신안 · 거문도 · 거제도 · 포항 · 동해)</Row>
      <Row title="연결 방식">해수욕장마다 가장 가까운 부이 1곳에 연결합니다. 거리는 7.4km ~ 179.6km입니다.</Row>
      <Row title="보여 주는 값">그 주의 평년 수온과 가장 최근 관측 주의 수온</Row>
      <Row title="주의">부이가 100km 넘게 떨어진 해수욕장은 실제 바닷물 온도와 차이가 있을 수 있습니다.</Row>
      {obs && beachName && (
        <Row title="선택한 해수욕장">{beachName} → {obs.station} ({obs.stationDistance})</Row>
      )}
    </>
  );
}

export function InfoModal({ topic, onClose, obs, beachName }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="jc-info-backdrop" onClick={onClose}>
      <section className="jc-info jc-card" role="dialog" aria-modal="true" aria-label={topic} onClick={(e) => e.stopPropagation()}>
        <header className="jc-card__head">
          <span className="text-section-title">{topic}</span>
          <button type="button" className="jc-chat__close" onClick={onClose} aria-label="닫기">×</button>
        </header>
        <div className="jc-info__body"><Content topic={topic} obs={obs} beachName={beachName} /></div>
      </section>
    </div>
  );
}
