import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurvePoint } from "./api";

const 선 = [
  { key: "통합출현율", name: "통합", color: "#0B2545", width: 3 },
  { key: "노무라", name: "노무라", color: "#D7263D", width: 2 },
  { key: "보름달", name: "보름달", color: "#0E7C86", width: 2 },
  { key: "기타", name: "기타", color: "#9AA0A6", width: 2 },
] as const;

const p1 = (v: unknown) => (typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "-");

export default function Curve({ data, now }: { data: CurvePoint[]; now: string | null }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="#E3ECF2" vertical={false} />
          <XAxis dataKey="주차명" interval={1} angle={-40} textAnchor="end" height={56} tick={{ fontSize: 12, fill: "#5B6B7C" }} />
          <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 12, fill: "#5B6B7C" }} width={48} />
          <Tooltip formatter={(v, name) => [p1(v), name]} contentStyle={{ borderRadius: 10, border: "1px solid #E3ECF2" }} />
          <Legend verticalAlign="top" height={28} iconType="plainline" />
          {now && <ReferenceLine x={now} stroke="#F08C00" strokeDasharray="4 4" strokeWidth={2}
            label={{ value: "선택한 주", position: "insideTopRight", fill: "#F08C00", fontSize: 12 }} />}
          {선.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={s.width}
              dot={{ r: 2.5 }} activeDot={{ r: 5 }} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
