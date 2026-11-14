import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Beach, MapCell } from "./api";

const 전국: [number, number] = [35.75, 127.7];
const 회색 = "#9AA0A6";

// 선택이 바뀌면 부드럽게 날아감 (휠 확대·축소는 Leaflet 기본 동작 그대로)
function Fly({ to }: { to?: Beach }) {
  const map = useMap();
  useEffect(() => {
    if (to) map.flyTo([to.위도, to.경도], 12, { duration: 1.5 });
    else map.flyTo(전국, 7, { duration: 1.2 });
  }, [to, map]);
  return null;
}

// 화면 폭이 바뀌면(좁은 화면 ↔ 넓은 화면) 지도 크기 다시 계산
function Resize() {
  const map = useMap();
  useEffect(() => {
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(map.getContainer());
    return () => ro.disconnect();
  }, [map]);
  return null;
}

type Props = { beaches: Beach[]; values: Record<string, MapCell>; selected?: Beach; onSelect: (id: string) => void };

export default function MapView({ beaches, values, selected, onSelect }: Props) {
  return (
    <MapContainer center={전국} zoom={7} zoomSnap={0.5} zoomDelta={0.5} wheelPxPerZoomLevel={120} className="map" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {beaches.map((b) => {
        const v = values[b.해수욕장ID];
        const color = v?.색 ?? 회색;
        return (
          <CircleMarker
            key={b.해수욕장ID}
            center={[b.위도, b.경도]}
            radius={7}
            pathOptions={{ color: "#ffffff", weight: 1, fillColor: color, fillOpacity: 0.9 }}
            eventHandlers={{ click: () => onSelect(b.해수욕장ID) }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              <b>{b.해수욕장명}</b> · {b.시군명}<br />
              <span style={{ color }}>●</span> {v ? `${v.등급} ${v.표시}` : "자료 없음"}
            </Tooltip>
          </CircleMarker>
        );
      })}
      {selected && (
        <CircleMarker center={[selected.위도, selected.경도]} radius={16} interactive={false}
          pathOptions={{ color: "#0B2545", weight: 3, fill: false }} />
      )}
      <Fly to={selected} />
      <Resize />
    </MapContainer>
  );
}
