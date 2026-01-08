import json
import time
import requests
from datetime import date
from .db import get_conn

def _ncaa_url(d: date) -> str:
    yyyy, mm, dd = d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")
    return f"https://data.ncaa.com/casablanca/scoreboard/basketball-men/d1/{yyyy}/{mm}/{dd}/scoreboard.json"

def _proxy_url(d: date) -> str:
    yyyy, mm, dd = d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")
    # ✅ henrygd API uses ncaa.com-style paths (no casablanca, no scoreboard.json)
    return f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{yyyy}/{mm}/{dd}"


def get_scoreboard(d: date, cache_seconds: int = 300) -> dict:
    """
    Fetch the NCAA scoreboard JSON with a simple DB cache.
    Tries NCAA first, then proxy fallback. Returns {"games": []} if 404.
    """
    key = f"scoreboard:{d.isoformat()}"
    now = int(time.time())

    conn = get_conn()
    row = conn.execute("SELECT value, created_at FROM cache WHERE key=?", (key,)).fetchone()
    if row and (now - int(row["created_at"]) <= cache_seconds):
        conn.close()
        return json.loads(row["value"])

    # ✅ IMPORTANT: build URLs *inside* the function where d exists
    try_urls = [_ncaa_url(d), _proxy_url(d)]

    payload = None
    last_resp = None

    for url in try_urls:
        try:
            r = requests.get(url, timeout=20)
            last_resp = r
        except requests.RequestException:
            continue

        if r.status_code == 404:
            payload = {"games": []}
            break

        if r.ok:
            try:
                payload = r.json()
        except ValueError:
        # Not JSON response
        payload = None
        if payload is not None:
        break

    if payload is None:
        # If we got a response but it wasn't ok and not 404, raise it
        if last_resp is not None:
            last_resp.raise_for_status()
        # Otherwise, all requests failed (network)
        raise RuntimeError("Failed to fetch scoreboard from all sources")

    conn.execute(
        "INSERT OR REPLACE INTO cache(key, value, created_at) VALUES(?,?,?)",
        (key, json.dumps(payload), now),
    )
    conn.commit()
    conn.close()

    return payload

def extract_games(scoreboard_json: dict) -> list[dict]:
    """
    Normalize the scoreboard feed into:
    [{home_id, home_name, away_id, away_name, neutral, status}, ...]
    """
    games = []

    raw_games = scoreboard_json.get("games") or scoreboard_json.get("scoreboard", {}).get("games") or []
    for g in raw_games:
        g = wrapper.get("game", wrapper) # <-- supports both shapes
        
        home = g.get("home") or {}
        away = g.get("away") or {}

        def team_name(t):
            names = t.get("names") or {}
            return names.get("short") or names.get("seo") or t.get("name") or "Unknown"

        def team_id(t):
            return str(t.get("id") or t.get("teamId") or team_name(t))

        games.append({
            "home_id": team_id(home),
            "home_name": team_name(home),
            "away_id": team_id(away),
            "away_name": team_name(away),
            "neutral": bool(g.get("neutralSite") or g.get("neutral")),
            "status": g.get("gameState") or g.get("status") or "unknown",
        })

    return games
