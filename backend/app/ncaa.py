import json
import time
import requests
from datetime import date
from .db import get_conn


def _proxy_url(d: date) -> str:
    yyyy, mm, dd = d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")
    return f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{yyyy}/{mm}/{dd}"


def get_scoreboard(d: date, cache_seconds: int = 300) -> dict:
    """
    Fetch NCAA men's D1 basketball scoreboard.
    Uses henrygd NCAA API. Gracefully handles 404 / empty days.
    """
    key = f"scoreboard:{d.isoformat()}"
    now = int(time.time())

    conn = get_conn()
    row = conn.execute(
        "SELECT value, created_at FROM cache WHERE key=?",
        (key,)
    ).fetchone()

    if row and (now - int(row["created_at"]) <= cache_seconds):
        conn.close()
        return json.loads(row["value"])

    payload = {"games": []}

    try:
        r = requests.get(_proxy_url(d), timeout=20)

        if r.status_code == 404:
            payload = {"games": []}
        elif r.ok:
            payload = r.json()
        else:
            r.raise_for_status()

    except requests.RequestException:
        payload = {"games": []}

    conn.execute(
        "INSERT OR REPLACE INTO cache(key, value, created_at) VALUES (?,?,?)",
        (key, json.dumps(payload), now)
    )
    conn.commit()
    conn.close()

    return payload


def extract_games(scoreboard_json: dict) -> list[dict]:
    """
    Normalize games from henrygd NCAA scoreboard.
    """
    games = []

    raw_games = scoreboard_json.get("games", [])
    for wrapper in raw_games:
        g = wrapper.get("game", wrapper)

        home = g.get("home", {})
        away = g.get("away", {})
        
        def team_name(t):
            names = t.get("names", {})
            return (
                names.get("short")
                or names.get("seo")
                or t.get("name")
                or "Unknown"
            )

        def team_id(t):
            return str(t.get("id") or team_name(t))

        games.append({
            "home_id": team_id(home),
            "home_name": team_name(home),
            "away_id": team_id(away),
            "away_name": team_name(away),
            "neutral": bool(g.get("neutralSite")),
            "status": g.get("gameState", "unknown"),
            "home_score": home.get("score"),
            "away_score": away.get("score"),
        })

    return games

