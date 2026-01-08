import { useEffect, useState } from "react";
import { fetchTopPicks } from "./api";

export default function App() {
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const [picks, setPicks] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    setErr("");
    fetchTopPicks(day).then(setPicks).catch(e => setErr(e.message));
  }, [day]);

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>NCAA Men’s Basketball — Top 5 Safest Winners</h1>

      <label style={{ display: "block", margin: "16px 0" }}>
        Date:&nbsp;
        <input type="date" value={day} onChange={(e) => setDay(e.target.value)} />
      </label>

      {err && <div style={{ padding: 12, background: "#fee", border: "1px solid #f99" }}>{err}</div>}

      <table width="100%" cellPadding="10" style={{ borderCollapse: "collapse", marginTop: 12 }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
            <th>Matchup</th>
            <th>Pick</th>
            <th>Win Prob</th>
          </tr>
        </thead>
        <tbody>
          {picks.map((p, i) => (
            <tr key={i} style={{ borderBottom: "1px solid #eee" }}>
              <td>{p.away} @ {p.home}</td>
              <td><b>{p.pick}</b></td>
              <td>{Math.round(p.win_prob * 1000) / 10}%</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p style={{ marginTop: 16, color: "#666" }}>
        Model: Elo + (optional) small home-court adjustment. “Safest” = highest predicted win probability.
      </p>
    </div>
  );
}
