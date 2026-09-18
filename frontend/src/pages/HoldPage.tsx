import { useEffect, useState } from "react";
import { api } from "../api/client";

type Show = { id: number; film_title: string; hall_name?: string };
type Hold = {
  id: number;
  order_code: string;
  row: number;
  start_col: number;
  end_col: number;
  party_size: number;
  is_child: boolean;
};

export default function HoldPage() {
  const [shows, setShows] = useState<Show[]>([]);
  const [sid, setSid] = useState<number | "">("");
  const [party, setParty] = useState(3);
  const [prefRow, setPrefRow] = useState("");
  const [isChild, setIsChild] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [last, setLast] = useState<Hold | null>(null);

  useEffect(() => {
    api<Show[]>("/showtimes").then((s) => {
      setShows(s);
      if (s[0]) setSid(s[0].id);
    });
  }, []);

  async function submit() {
    setMsg("");
    setErr("");
    try {
      const body: Record<string, unknown> = {
        showtime_id: sid,
        party_size: party,
        is_child: isChild,
      };
      if (prefRow) body.preferred_row = Number(prefRow);
      const hold = await api<Hold>("/holds", { method: "POST", body: JSON.stringify(body) });
      setLast(hold);
      setMsg(
        `已锁座 ${hold.order_code}：第${hold.row}排 ${hold.start_col}-${hold.end_col}` +
          (hold.is_child ? "（家庭排）" : "")
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <>
      <h2>锁座</h2>
      <div className="toolbar">
        <select value={sid} onChange={(e) => setSid(Number(e.target.value))}>
          {shows.map((s) => (
            <option key={s.id} value={s.id}>
              {s.film_title} · {s.hall_name}
            </option>
          ))}
        </select>
        <label>
          人数{" "}
          <input
            type="number"
            min={1}
            max={12}
            value={party}
            onChange={(e) => setParty(Number(e.target.value))}
            style={{ width: 72 }}
          />
        </label>
        <label>
          优先排{" "}
          <input
            value={prefRow}
            onChange={(e) => setPrefRow(e.target.value)}
            placeholder="可选"
            style={{ width: 72 }}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={isChild}
            onChange={(e) => setIsChild(e.target.checked)}
          />
          带儿童（仅家庭排）
        </label>
        <button onClick={submit}>查找并锁连座</button>
      </div>
      <p className="hint">
        {isChild
          ? "带儿童：只在家庭排内寻找连续空座；若家庭排被过道切短或占满，将提示家庭排空座不足，不会改占普通排。"
          : "普通请求默认避开家庭排，把亲子区留给带儿童的观众。"}
      </p>
      {msg && <div className="ok">{msg}</div>}
      {err && <div className="err">{err}</div>}
      {last && (
        <p className="mono">
          订单 {last.order_code} · {last.party_size} 人 · R{last.row} C{last.start_col}-
          {last.end_col}
          {last.is_child ? " · 儿童" : ""}
        </p>
      )}
    </>
  );
}
