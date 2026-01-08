from .db import get_conn
from .elo import win_prob

def elo_delta(elo_a: float, elo_b: float, score_a: int, score_b: int, k: float = 20.0) -> float:
    """
    Returns change to team A Elo. Team B gets -delta.
    Simple Elo with optional margin-of-victory multiplier.
    """
    expected = win_prob(elo_a, elo_b)
    actual = 1.0 if score_a > score_b else 0.0

    # Margin-of-victory scaling (lightweight, safe)
    margin = abs(score_a - score_b)
    mov_mult = 1.0 + min(margin, 25) / 25.0 * 0.25  # up to +25%
    return k * mov_mult * (actual - expected)

def get_team_elo(team_id: str, name: str) -> float:
    conn = get_conn()
    row = conn.execute("SELECT elo FROM teams WHERE id=?", (team_id,)).fetchone()
    if row:
        conn.close()
        return float(row["elo"])
    elo = 1500.0
    conn.execute("INSERT INTO teams(id, name, elo) VALUES(?,?,?)", (team_id, name, elo))
    conn.commit()
    conn.close()
    return elo

def set_team_elo(team_id: str, elo: float):
    conn = get_conn()
    conn.execute("UPDATE teams SET elo=? WHERE id=?", (elo, team_id))
    conn.commit()
    conn.close()

def update_elo_from_games(games: list[dict]) -> dict:
    """
    games items must include:
    home_id, away_id, home_name, away_name, status, home_score, away_score
    """
    updated = 0

    for g in games:
        status = (g.get("status") or "").lower()
        if "final" not in status and status not in ("final", "closed"):
            continue

        hs = g.get("home_score")
        as_ = g.get("away_score")
        if hs is None or as_ is None:
            continue

        home_elo = get_team_elo(g["home_id"], g["home_name"])
        away_elo = get_team_elo(g["away_id"], g["away_name"])

        # Elo update assumes "home vs away" with no home-adv baked in
        d_home = elo_delta(home_elo, away_elo, hs, as_)
        set_team_elo(g["home_id"], home_elo + d_home)
        set_team_elo(g["away_id"], away_elo - d_home)

        updated += 1

    return {"games_updated": updated}
