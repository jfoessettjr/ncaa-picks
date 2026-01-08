const API_BASE = import.meta.env.VITE_API_URL || "";

export async function fetchTopPicks(dateStr) {
  const qs = dateStr ? `?day=${encodeURIComponent(dateStr)}` : "";
  const res = await fetch(`${API_BASE}/api/picks${qs}`);
  if (!res.ok) throw new Error("Failed to load picks");
  return res.json();
}
