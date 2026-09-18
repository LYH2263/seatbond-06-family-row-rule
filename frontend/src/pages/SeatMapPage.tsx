import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

type Show = { id: number; film_title: string; hall_name?: string };
type Cell = {
  row: number;
  col: number;
  is_aisle: boolean;
  is_family: boolean;
  occupied: boolean;
  heat: number;
};
type MapOut = {
  showtime_id: number;
  hall_name: string;
  rows: number;
  cols: number;
  family_rows: number[];
  cells: Cell[];
};

export default function SeatMapPage() {
  const [shows, setShows] = useState<Show[]>([]);
  const [sid, setSid] = useState<number | "">("");
  const [map, setMap] = useState<MapOut | null>(null);

  useEffect(() => {
    api<Show[]>("/showtimes").then((s) => {
      setShows(s);
      if (s[0]) setSid(s[0].id);
    });
  }, []);

  useEffect(() => {
    if (sid === "") return;
    api<MapOut>(`/seatmap/${sid}`).then(setMap);
  }, [sid]);

  const gridStyle = useMemo(
    () => ({ gridTemplateColumns: map ? `repeat(${map.cols}, 28px)` : undefined }),
    [map]
  );

  return (
    <>
      <div className="toolbar">
        <label>
          场次{" "}
          <select value={sid} onChange={(e) => setSid(Number(e.target.value))}>
            {shows.map((s) => (
              <option key={s.id} value={s.id}>
                {s.film_title} · {s.hall_name}
              </option>
            ))}
          </select>
        </label>
        {map && (
          <span className="mono">
            {map.hall_name} · {map.rows}×{map.cols} · 热力座图
          </span>
        )}
        {map && map.family_rows.length > 0 && (
          <span className="legend">
            <span className="legend-chip family" />
            家庭排（第 {map.family_rows.join("、")} 排）· 带儿童锁座专用
          </span>
        )}
      </div>
      <div className="screen">银 幕</div>
      {map && (
        <div className="seat-grid" style={gridStyle}>
          {map.cells.map((c) => {
            const cls = c.is_aisle
              ? "aisle"
              : c.occupied
                ? c.is_family
                  ? "occ family"
                  : "occ"
                : c.is_family
                  ? "free family"
                  : "free";
            return (
              <div
                key={`${c.row}-${c.col}`}
                className={`seat ${cls}`}
                title={
                  c.is_aisle
                    ? `R${c.row}C${c.col} 过道`
                    : `R${c.row}C${c.col}${c.is_family ? " 家庭排" : ""}`
                }
                style={
                  !c.is_aisle && c.heat
                    ? { boxShadow: `inset 0 0 0 1px rgba(255,180,80,${Math.min(0.9, c.heat / 10)})` }
                    : undefined
                }
              >
                {c.is_aisle ? "" : c.col}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
