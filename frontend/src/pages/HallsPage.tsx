import { useEffect, useState } from "react";
import { api } from "../api/client";

type Hall = {
  id: number;
  name: string;
  rows: number;
  cols: number;
  aisle_cols: number[];
  family_rows: number[];
};

export default function HallsPage() {
  const [halls, setHalls] = useState<Hall[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [savedId, setSavedId] = useState<number | null>(null);
  const [error, setError] = useState("");

  function load() {
    api<Hall[]>("/halls").then((rows) => {
      setHalls(rows);
      setDrafts(Object.fromEntries(rows.map((h) => [h.id, h.family_rows.join(", ")])));
    });
  }

  useEffect(load, []);

  async function save(h: Hall) {
    setError("");
    setSavedId(null);
    const parsed = (drafts[h.id] ?? "")
      .split(/[,，\s]+/)
      .map((s) => parseInt(s, 10))
      .filter((n) => Number.isInteger(n));
    try {
      const updated = await api<Hall>(`/halls/${h.id}/family-rows`, {
        method: "PUT",
        body: JSON.stringify({ family_rows: parsed }),
      });
      setHalls((prev) => prev.map((x) => (x.id === h.id ? updated : x)));
      setDrafts((prev) => ({ ...prev, [h.id]: updated.family_rows.join(", ") }));
      setSavedId(h.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <>
      <h2>影厅</h2>
      <p className="hint">在「家庭排」中填写整排排号（逗号分隔），带儿童的锁座只会安排到这些排。</p>
      <table className="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>行×列</th>
            <th>过道列</th>
            <th style={{ minWidth: 220 }}>家庭排</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {halls.map((h) => (
            <tr key={h.id}>
              <td>{h.name}</td>
              <td className="mono">
                {h.rows} × {h.cols}
              </td>
              <td className="mono">{h.aisle_cols.join(", ") || "—"}</td>
              <td>
                <input
                  aria-label={`${h.name} 家庭排`}
                  value={drafts[h.id] ?? ""}
                  placeholder="如 3, 4"
                  onChange={(e) =>
                    setDrafts((prev) => ({ ...prev, [h.id]: e.target.value }))
                  }
                  style={{ width: 120 }}
                />
                {savedId === h.id && <span className="ok inline">已保存</span>}
              </td>
              <td>
                <button onClick={() => save(h)}>保存家庭排</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <div className="err">{error}</div>}
    </>
  );
}
