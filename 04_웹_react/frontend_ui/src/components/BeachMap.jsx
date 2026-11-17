/* Leaflet 지도 — BeachMapCard 안에 넣어서 쓴다.
   - 해수욕장 마커를 위험등급 색으로 칠함 (percentOf 로 값 계산)
   - 마커 클릭 → onSelect(id), 선택한 곳은 흰 마커 + 이름표
   - ref 로 zoomIn / zoomOut / showAll(전국 보기) 호출 */
import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { riskLevel } from '../styles/tokens.js';
import { formatPct } from './basics.jsx';

// 지도 타일: 기본은 OpenStreetMap. 운영 시 VWorld·카카오 등으로 바꿀 수 있음.
const TILE_URL = import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const KOREA_BOUNDS = L.latLngBounds([33.0, 124.6], [38.7, 131.0]);

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const selectedIcon = (name) => L.divIcon({
  className: 'jc-leaflet-selected',
  html: `<span class="jc-map-label text-button">${escapeHtml(name)}</span><span class="jc-marker"></span>`,
  iconSize: [0, 0],
  iconAnchor: [0, 0],
});

export const BeachMap = forwardRef(function BeachMap({ beaches, selectedId, percentOf, onSelect }, ref) {
  const boxRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const lastSelected = useRef(null);

  // 지도 만들기 (한 번)
  useEffect(() => {
    const map = L.map(boxRef.current, {
      zoomControl: false,           // 확대·축소는 시안의 ZoomControls 사용
      attributionControl: false,    // 출처는 카드의 attribution 문구로 표시
      minZoom: 6, maxZoom: 16,
      maxBounds: KOREA_BOUNDS.pad(0.5),
    });
    L.tileLayer(TILE_URL, { maxZoom: 19 }).addTo(map);
    map.fitBounds(KOREA_BOUNDS);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useImperativeHandle(ref, () => ({
    zoomIn: () => mapRef.current?.zoomIn(),
    zoomOut: () => mapRef.current?.zoomOut(),
    showAll: () => mapRef.current?.flyToBounds(KOREA_BOUNDS, { duration: 0.6 }),
  }), []);

  // 마커 다시 그리기 (목록·색 기준·선택이 바뀔 때)
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.clearLayers();
    beaches.forEach((b) => {
      if (b.lat == null || b.lng == null) return;
      const pct = percentOf(b);
      const lv = riskLevel(pct);
      const tip = `<strong>${escapeHtml(b.name)}</strong> · ${lv.label}${pct != null ? ` ${formatPct(pct)}` : ''}`;
      if (b.id === selectedId) {
        L.marker([b.lat, b.lng], { icon: selectedIcon(b.name), zIndexOffset: 1000, keyboard: false })
          .bindTooltip(tip, { direction: 'top', offset: [0, -24], className: 'jc-leaflet-tip' })
          .addTo(layer);
      } else {
        L.circleMarker([b.lat, b.lng], {
          radius: 8, weight: 2, color: '#FFFFFF', fillColor: lv.color, fillOpacity: 1,
        })
          .bindTooltip(tip, { direction: 'top', offset: [0, -8], className: 'jc-leaflet-tip' })
          .on('click', () => onSelect?.(b.id))
          .addTo(layer);
      }
    });
  }, [beaches, selectedId, percentOf, onSelect]);

  // 선택이 바뀌면 그 해수욕장으로 이동
  useEffect(() => {
    const map = mapRef.current;
    const b = beaches.find((x) => x.id === selectedId);
    if (!map || !b || lastSelected.current === selectedId) return;
    const first = lastSelected.current == null;
    lastSelected.current = selectedId;
    if (first) map.setView([b.lat, b.lng], 10);
    else map.flyTo([b.lat, b.lng], Math.max(map.getZoom(), 10), { duration: 0.6 });
  }, [beaches, selectedId]);

  return <div ref={boxRef} className="jc-leaflet" />;
});
