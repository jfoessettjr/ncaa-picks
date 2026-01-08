from datetime import date, datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db, get_conn
from .ncaa import get_scoreboard, extract_games
from .elo import pick_winner
from .models import Pick
from .elo_update import update_elo_from_games
from .elo_update import rebuild_elo_range

app = FastAPI(title="NCAA Safest Picks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

def get_or_create_team(team_id: str, name: str) -> float:
    conn = get_conn()
    row = conn.execute("SELECT elo FROM teams WHERE id=?", (team_id,)).fetchone()
    if row:
        conn.close()
        return float(row["elo"])

    # New team: start neutral
    elo = 1500.0
    conn.execute("INSERT INTO teams(id, name, elo) VALUES(?,?,?)", (team_id, name, elo))
    conn.commit()
    conn.close()
    return elo

@app.get("/api/picks", response_model=list[Pick])
def picks(day: str | None = None):
    d = date.fromisoformat(day) if day else date.today()

    sb = get_scoreboard(d)
    games = extract_games(sb)

    def is_upcoming(g):
        s = (g.get("status") or "").lower()
        # keep only pregame/scheduled-ish statuses
        return ("pre" in s) or ("scheduled" in s) or (s in ("pre", "scheduled"))

    games = [g for g in games if is_upcoming(g)]

    
    picks = []
    for g in games:
        home_elo = get_or_create_team(g["home_id"], g["home_name"])
        away_elo = get_or_create_team(g["away_id"], g["away_name"])

        # Neutral site? remove home advantage
        home_adv = 0.0 if g["neutral"] else 50.0

        side, prob = pick_winner(home_elo, away_elo, home_adv=home_adv)
        pick_team = g["home_name"] if side == "HOME" else g["away_name"]
        
        if prob >= 0.85:
            label = "LOCK"
        elif prob >= 0.75:
            label = "STRONG"
        elif prob >= 0.65:
            label = "LEAN"
        else:
            label = "PASS"
            
        if label == "PASS":
            continue



        picks.append({
            "date": d.isoformat(),
            "home": g["home_name"],
            "away": g["away_name"],
            "pick": pick_team,
            "win_prob": round(float(prob), 4),
        })

    picks.sort(key=lambda x: x["win_prob"], reverse=True)
    return picks[:5]

    from .elo_update import update_elo_from_games
from .ncaa import get_scoreboard, extract_games
from datetime import date
from fastapi import HTTPException

@app.post("/api/admin/update-elo")
def admin_update_elo(day: str):
    d = date.fromisoformat(day)
    sb = get_scoreboard(d)
    games = extract_games(sb)
    if not games:
        return {"games_updated": 0, "note": "No games found."}

    result = update_elo_from_games(games)
    return result

from datetime import date

@app.post("/api/admin/rebuild-elo")
def admin_rebuild_elo(start: str, end: str):
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    return rebuild_elo_range(start_d, end_d)

@app.get("/api/debug/sample-game")
def debug_sample_game(day: str):
    from datetime import date
    from .ncaa import get_scoreboard, extract_games

    d = date.fromisoformat(day)
    sb = get_scoreboard(d)
    games = extract_games(sb)

    if not games:
        return {"error": "No games found for this date"}

    # Return just the first game
    return games[0]
