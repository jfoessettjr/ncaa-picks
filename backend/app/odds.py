import os
import requests
import json
import time
from .db import SessionLocal
from .repo import cache_get, cache_set
from datetime import datetime, timezone

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

# The Odds API uses sport key "basketball_ncaab" in v4
SPORT_KEY = "basketball_ncaab"

def american_to_implied_prob(odds: int) -> float:
    """
    Convert American odds to implied probability (no vig removal).
    -110 -> 0.5238
    +150 -> 0.4000
    """
    odds = int(odds)
    if odds < 0:
        return (-odds) / ((-odds) + 100.0)
    return 100.0 / (odds + 100.0)

def fetch_ncaab_moneylines(regions: str = "us", markets: str = "h2h") -> list[dict]:
    """
    Returns list of events with bookmakers, including home/away and odds.
    Docs: /v4/sports/{sport}/odds
    """
    if not ODDS_API_KEY:
        raise RuntimeError("ODDS_API_KEY is not set")

    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": regions,        # us bookmakers
        "markets": markets,        # h2h (moneyline)
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def build_best_price_map(events: list[dict]) -> dict:
    """
    Returns mapping keyed by normalized matchup:
      key = (home, away) lowercased strings
      value = {"home_odds": int, "away_odds": int, "book": str, "commence_time": str}
    Chooses the best (most favorable) price for each side across books.
    """
    out = {}

    for e in events:
        home = (e.get("home_team") or "").strip()
        away = (e.get("away_team") or "").strip()
        if not home or not away:
            continue

        key = (home.lower(), away.lower())

        best_home = None
        best_away = None
        best_book = None

        for b in e.get("bookmakers", []) or []:
            book = b.get("title") or b.get("key") or "book"
            for m in b.get("markets", []) or []:
                if m.get("key") != "h2h":
                    continue
                for o in m.get("outcomes", []) or []:
                    name = (o.get("name") or "").strip()
                    price = o.get("price")
                    if price is None:
                        continue
                    try:
                        price = int(price)
                    except Exception:
                        continue

                    if name.lower() == home.lower():
                        # "best" for the bettor = higher American number (less negative / more positive)
                        if best_home is None or price > best_home:
                            best_home = price
                            best_book = book
                    elif name.lower() == away.lower():
                        if best_away is None or price > best_away:
                            best_away = price
                            best_book = book

        if best_home is None or best_away is None:
            continue

        out[key] = {
            "home_odds": best_home,
            "away_odds": best_away,
            "book": best_book,
            "commence_time": e.get("commence_time"),
        }

def fetch_ncaab_moneylines_cached(ttl_seconds: int = 300) -> list[dict]:
    """
    Cached wrapper around fetch_ncaab_moneylines().
    Stores raw JSON response in Postgres cache table.
    """
    key = "odds:ncaab:h2h:us"
    now = int(time.time())

    db = SessionLocal()
    try:
        row = cache_get(db, key)
        if row and (now - int(row.created_at) <= ttl_seconds):
            try:
                return json.loads(row.value)
            except Exception:
                # bad cache; fall through and refetch
                pass

        events = fetch_ncaab_moneylines(regions="us", markets="h2h")
        cache_set(db, key, json.dumps(events), created_at=now)
        db.commit()
        return events
    finally:
        db.close()


    return out
