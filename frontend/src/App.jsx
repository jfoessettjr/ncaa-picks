import { useEffect, useState } from "react";
import { fetchTopPicks } from "./api";

export default function App() {
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const [picks, setPicks] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      console.log("VITE_API_URL =", import.meta.env.VITE_API_URL);
      setLoading(true);
      setErr("");

      try {
        const data = await fetchTopPicks(day);
        if (!cancelled) setPicks(Array.isArray(data) ? data : []);
      } catch (e) {
        if (!cancelled) setErr(e?.message || "Failed to load picks");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [day]);

  const badgeStyle = (confidence) => {
    const c = (confidence || "").toUpperCase();
    if (c === "LOCK") return { background: "#e7f7ee", border: "1px solid #b8e6c9" };
    if (c === "STRONG") return { background: "#e7f0ff", border: "1px solid #b9d0ff" };
    if (c === "LEAN") return { background: "#fff7e6", border: "1px solid #ffd38a" };
    return { background: "#f3f3f3", border: "1px solid #ddd" };
  };

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 6 }}>NCAA Men’s Basketball — Top 5 Safest Winners</h1>
      <div style={{ color: "#666", marginBottom: 18 }}>
        Elo model (home-court adjustment when not neutral). “Safest” = highest predicted win probability.
      </div>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <label>
          Date:&nbsp;
          <input
            type="date"
            value={day}
            onChange={(e) => setDay(e.target.value)}
            style={{ padding: 6 }}
          />
        </label>

        <button
          onClick={async () => {
            setLoading(true);
            setErr("");
            try {
              const data = await fetchTopPicks(day);
              setPicks(Array.isArray(data) ? data : []);
            } catch (e) {
              setErr(e?.message || "Failed to load picks");
            } finally {
              setLoading(false);
            }
          }}
          style={{
            padding: "7px 10px",
            border: "1px solid #ddd",
            background: "white",
            cursor: "pointer",
          }}
        >
          Refresh
        </button>

        {loading && <span style={{ color: "#666" }}>Loading…</span>}
      </div>

      {err && (
        <div style={{ padding: 12, background: "#fee", border: "1px solid #f99", marginBottom: 12 }}>
          {err}
        </div>
      )}

      {!err && !loading && picks.length === 0 && (
        <div style={{ padding: 12, background: "#f7f7f7", border: "1px solid #ddd", marginBottom: 12 }}>
          No upcoming games found for this date.
        </div>
      )}

      {picks.length > 0 && (
        <table width="100%" cellPadding="10" style={{ borderCollapse: "collapse", marginTop: 8 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th>Matchup</th>
              <th>Pick</th>
              <th>Win Prob</th>
              <th>Confidence</th>
              <th>Vegas Odds</th>
              <th>Vegas Implied Prob</th>
              <th>Edge</th>
            </tr>
          </thead>
          <tbody>
            {picks.map((p, i) => {
              const probPct = p?.win_prob != null ? Math.round(Number(p.win_prob) * 1000) / 10 : null;
              const conf = (p?.confidence || "").toUpperCase();

              return (
                <tr key={i} style={{ borderBottom: "1px solid #eee" }}>
                  <td>
                    {p.away} @ {p.home}
                  </td>
                  <td>
                    <b>{p.pick}</b>
                  </td>
                  <td>{probPct != null && !Number.isNaN(probPct) ? `${probPct}%` : "—"}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "4px 8px",
                        borderRadius: 999,
                        fontSize: 12,
                        ...badgeStyle(conf),
                      }}
                    >
                      {conf || "—"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
