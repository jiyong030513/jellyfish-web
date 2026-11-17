/* 화면 상태와 데이터 흐름을 한 곳에서 관리
   - 날짜 변경 / 업데이트 버튼 → 목록 + 상세 다시 불러옴 (그동안 로딩 화면)
   - 해수욕장 선택(지도 클릭·검색) → 상세만 다시 불러옴
   - 지도색 기준 · 예측 기간 → 이미 받은 값으로 지도 색만 바뀜 (서버 요청 없음) */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchBeaches, fetchBeachDetail, fetchTop } from '../api/client.js';
import { today } from '../api/week.js';

const norm = (s) => s.replace(/\s+/g, '').replace(/해수욕장$/, '').toLowerCase();

export function useJellyCast({ initialDate = today(), initialBeachId = null } = {}) {
  const [date, setDate] = useState(initialDate);
  const [basis, setBasis] = useState('average'); // 'average' 평년 출현율 | 'forecast' 예측 위험 지수
  const [weeks, setWeeks] = useState(1);          // 1 | 2 | 4
  const [selectedId, setSelectedId] = useState(initialBeachId);
  const [query, setQuery] = useState('');
  const [guide, setGuide] = useState('지도에서 해수욕장을 선택해 정보를 확인하세요.');

  const [list, setList] = useState(null);       // { weekLabel, beaches }
  const [detail, setDetail] = useState(null);   // fetchBeachDetail 결과
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const reqId = useRef(0);

  // 목록: 날짜가 바뀌거나 업데이트를 누르면
  useEffect(() => {
    let alive = true;
    setListLoading(true);
    fetchBeaches({ date })
      .then((res) => {
        if (!alive) return;
        setList(res);
        setError(null);
        setSelectedId((cur) => cur ?? res.beaches[0]?.id ?? null);
      })
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setListLoading(false));
    return () => { alive = false; };
  }, [date, reloadKey]);

  // 상세: 선택한 해수욕장 · 날짜가 바뀌거나 업데이트를 누르면
  useEffect(() => {
    if (selectedId == null) return;
    const id = ++reqId.current;
    setDetailLoading(true);
    fetchBeachDetail(selectedId, { date })
      .then((res) => { if (id === reqId.current) { setDetail(res); setError(null); } })
      .catch((e) => id === reqId.current && setError(e.message))
      .finally(() => id === reqId.current && setDetailLoading(false));
  }, [selectedId, date, reloadKey]);

  // 위험 상위 10곳: 날짜 · 예측 기간 · 업데이트
  const [top, setTop] = useState(null);
  useEffect(() => {
    let alive = true;
    setTop(null);
    fetchTop({ date, weeks }).then((r) => alive && setTop(r)).catch(() => alive && setTop({ items: [] }));
    return () => { alive = false; };
  }, [date, weeks, reloadKey]);

  const refresh = useCallback(() => setReloadKey((k) => k + 1), []);

  const select = useCallback((id) => {
    setSelectedId(id);
    setGuide('지도에서 해수욕장을 선택해 정보를 확인하세요.');
  }, []);

  // 검색: 이름 → 지역 순으로 찾아 첫 번째를 선택
  const search = useCallback((q) => {
    const key = norm(q ?? '');
    if (!key || !list) return null;
    const hit = list.beaches.find((b) => norm(b.name).includes(key))
      ?? list.beaches.find((b) => norm(b.region).includes(key));
    if (hit) {
      setSelectedId(hit.id);
      setGuide('지도에서 해수욕장을 선택해 정보를 확인하세요.');
    } else {
      setGuide(`'${q}' 검색 결과가 없어요. 해수욕장명이나 지역명을 다시 확인해 주세요.`);
    }
    return hit ?? null;
  }, [list]);

  // 지도 마커 색에 쓸 값: 기준에 따라 평년 출현율 또는 n주 뒤 예측
  const percentOf = useCallback(
    (b) => (basis === 'average' ? b.averagePercent : b.forecastPercent?.[weeks] ?? b.forecastPercent?.[String(weeks)]),
    [basis, weeks],
  );

  const beaches = useMemo(() => list?.beaches ?? [], [list]);
  const selected = beaches.find((b) => b.id === selectedId) ?? null;

  return {
    // 조회 조건
    date, setDate, basis, setBasis, weeks, setWeeks, query, setQuery,
    // 데이터
    beaches, selected, selectedId, detail, top, weekLabel: list?.weekLabel, percentOf,
    // 상태
    listLoading, detailLoading, loading: listLoading || detailLoading || !detail, error, guide,
    // 동작
    select, search, refresh,
  };
}
