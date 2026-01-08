export async function fetchTopPicks(dateStr) {
  const qs = dateStr ? `?day=${encodeURIComponent(dateStr)}` : "";
  const res = await fetch(`http://localhost:8000/api/picks${qs}`);
  if (!res.ok) throw new Error("Failed to load picks");
  return res.json();
}
