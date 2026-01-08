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
    return f"https://ncaa-api.henrygd.me/casablanca/scoreboard/basketball-men/d1/{yyyy}/{mm}/{dd}/scoreboard.json"


def get_scoreboard(d: date, cache_seconds: int = 300) -> dict:
    key = f"scoreboard:{d.isoformat()}"
    now = int(time.time())

    conn = get_conn()
    row = conn.execute("SELECT value, created_at FROM cache WHERE key=?", (key,)).fetchone()
    if row and (now - int(row["created_at"]) <= cache_seconds):
        conn.close()
        return json.loads(row["value"])

    url = _ncaa_url(d)
    r = requests.get(url, timeout=20)

    # ✅ If NCAA has no file for that date, treat it as “no games”
    if r.status_code == 404:
        payload = {"games": []}
    else:
        r.raise_for_status()
        payload = r.json()

    conn.execute(
        "INSERT OR REPLACE INTO cache(key, value, created_at) VALUES(?,?,?)",
        (key, json.dumps(payload), now),
    )
    conn.commit()
    conn.close()
    return payload

try_urls = [_ncaa_url(d), _proxy_url(d)]
payload = None

for url in try_urls:
    r = requests.get(url, timeout=20)
    if r.status_code == 404:
        payload = {"games": []}
        break
    if r.ok:
        payload = r.json()
        break

if payload is None:
    r.raise_for_status()


def extract_games(scoreboard_json: dict) -> list[dict]:
    """
    Normalize the scoreboard feed into:
    [{home_id, home_name, away_id, away_name, neutral?}, ...]
    Field names can vary slightly over time, so we try a few common patterns.
    """
    games = []

    # Common key observed in many NCAA feeds
    raw_games = scoreboard_json.get("games") or scoreboard_json.get("scoreboard", {}).get("games") or []
    for g in raw_games:
        # Try a few patterns for team data
        home = g.get("home") or {}
        away = g.get("away") or {}

        def team_name(t):
            names = t.get("names") or {}
            return names.get("short") or names.get("seo") or t.get("name") or "Unknown"

        def team_id(t):
            # Sometimes "id", sometimes nested.
            return str(t.get("id") or t.get("teamId") or team_name(t))

        games.append({
            "home_id": team_id(home),
            "home_name": team_name(home),
            "away_id": team_id(away),
            "away_name": team_name(away),
            "neutral": bool(g.get("neutralSite") or g.get("neutral")),
            "status": g.get("gameState") or g.get("status") or "unknown",
        })

    games = extract_games(sb)
    if not games:
        return []
