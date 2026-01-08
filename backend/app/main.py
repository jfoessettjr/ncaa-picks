import os
from datetime import date
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db, SessionLocal
from .ncaa import get_scoreboard, extract_games
from .elo import pick_winner
from .elo_update import update_elo_from_games, rebuild_elo_range
from .repo import get_or_create_team
from .odds import (
    fetch_ncaab_moneylines_cached,
    build_best_price_map,
    american_to_implied_prob,
)



app = FastAPI(title="NCAA Safest Picks API")

# CORS (Render/Netlify friendly)
# Set CORS_ORIGINS to comma-separated list, e.g.:
# https://your-site.netlify.app,http://localhost:5173
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

def is_upcoming_game(g: dict) -> bool:
    """
    Based on your sample: status can be 'final'.
    We'll allow only pregame-ish statuses.
    """
    s = (g.get("status") or "").strip().lower()
    return s in ("pre", "scheduled", "pregame", "upcoming")

def confidence_label(prob: float) -> str:
    if prob >= 0.85:
        return "LOCK"
    if prob >= 0.75:
        return "STRONG"
    if prob >= 0.65:
        return "LEAN"
    return "PASS"

@app.get("/api/picks")
def picks(day: str | None = None):
    d = date.fromisoformat(day) if day else date.today()

    sb = get_scoreboard(d)
    games = extract_games(sb)
    games = [g for g in games if is_upcoming_game(g)]
    # Pull vegas odds once per request (you can cache later)
    odds_map = {}
    try:
        events = fetch_ncaab_moneylines_cached(ttl_seconds=300)  # 5 min cache
        odds_map = build_best_price_map(events)
    except Exception:
        odds_map = {}



    db = SessionLocal()
    try:
        out = []
        for g in games:
            home_team = get_or_create_team(db, g["home_id"], g["home_name"])
            away_team = get_or_create_team(db, g["away_id"], g["away_name"])

            home_adv = 0.0 if g.get("neutral") else 50.0
            side, prob = pick_winner(home_team.elo, away_team.elo, home_adv=home_adv)
            match_key = (g["home_name"].lower(), g["away_name"].lower())
            vegas = odds_map.get(match_key)

            vegas_home_prob = vegas_away_prob = None
            home_odds = away_odds = book = None

            if vegas:
                home_odds = vegas["home_odds"]
                away_odds = vegas["away_odds"]
                book = vegas.get("book")
                vegas_home_prob = round(american_to_implied_prob(home_odds), 4)
                vegas_away_prob = round(american_to_implied_prob(away_odds), 4)

            pick_team = g["home_name"] if side == "HOME" else g["away_name"]

            conf = confidence_label(float(prob))
            if conf == "PASS":
                continue

            out.append({
                "date": d.isoformat(),
                "home": g["home_name"],
                "away": g["away_name"],
                "pick": pick_team,
                "win_prob": round(float(prob), 4),
                "confidence": conf,
                "status": g.get("status"),
                "neutral": bool(g.get("neutral")),
                "home_odds": home_odds,
                "away_odds": away_odds,
                "vegas_home_prob": vegas_home_prob,
                "vegas_away_prob": vegas_away_prob,
                "book": book,
                "edge": round(float(prob) - (vegas_home_prob if side == "HOME" else vegas_away_prob or 0.0), 4) if vegas else None,
            })

        # Commit any “new team inserted” changes
        db.commit()

        out.sort(key=lambda x: x["win_prob"], reverse=True)
        return out[:5]
    finally:
        db.close()

@app.post("/api/admin/update-elo")
def admin_update_elo(day: str):
    d = date.fromisoformat(day)
    sb = get_scoreboard(d)
    games = extract_games(sb)
    if not games:
        return {"games_updated": 0, "note": "No games found."}

    return update_elo_from_games(games)

@app.post("/api/admin/rebuild-elo")
def admin_rebuild_elo(start: str, end: str):
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    return rebuild_elo_range(start_d, end_d)

@app.get("/api/debug/sample-game")
def debug_sample_game(day: str):
    d = date.fromisoformat(day)
    sb = get_scoreboard(d)
    games = extract_games(sb)
    if not games:
        return {"error": "No games found for this date"}
    return games[0]
