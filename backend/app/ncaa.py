import json
import time
import requests
from datetime import date

from .db import SessionLocal
from .repo import cache_get, cache_set


def _proxy_url(d: date) -> str:
    yyyy, mm, dd = d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")
    return f"https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{yyyy}/{mm}/{dd}"


def get_scoreboard(d: date, cache_seconds: int = 300) -> dict:
    """
    Fetch NCAA men's D1 basketball scoreboard (JSON).
    Uses Postgres-backed cache table via repo.py (shared across instances).
    Returns {"games": []} on 404 or request failure.
    """
    key = f"scoreboard:{d.isoformat()}"
    now = int(time.time())

    db = SessionLocal()
    try:
        row = cache_get(db, key)
        if row and (now - int(row.created_at) <= cache_seconds):
            try:
                return json.loads(row.value)
            except Exception:
                # corrupted cache entry; fall through to refetch
                pass

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

        cache_set(db, key, json.dumps(payload), created_at=now)
        db.commit()
        return payload
    finally:
        db.close()


def extract_games(scoreboard_json: dict) -> list[dict]:
    """
    Normalize the henrygd scoreboard into:
    [{home_id, home_name, away_id, away_name, neutral, status, home_score, away_score}, ...]
    """
    games = []

    raw_games = scoreboard_json.get("games", [])
    for wrapper in raw_games:
        g = wrapper.get("game", wrapper)

        home = g.get("home", {}) or {}
        away = g.get("away", {}) or {}

        def team_name(t: dict) -> str:
            names = t.get("names", {}) or {}
            return names.get("short") or names.get("seo") or t.get("name") or "Unknown"

        def team_id(t: dict) -> str:
            # If the API provides a stable id, use it. Otherwise fall back to name.
            return str(t.get("id") or team_name(t))

        games.append({
            "home_id": team_id(home),
            "home_name": team_name(home),
            "away_id": team_id(away),
            "away_name": team_name(away),
            "neutral": bool(g.get("neutralSite")),
            "status": (g.get("gameState") or g.get("status") or "unknown"),
            "home_score": home.get("score"),
            "away_score": away.get("score"),
        })

    return games
