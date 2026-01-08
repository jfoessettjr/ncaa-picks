from .db import get_conn
from .elo import win_prob

def to_int(x):
    try:
        if x is None:
            return None
        # handle "", "—", etc.
        s = str(x).strip()
        if s == "" or s.lower() in ("-", "—", "n/a", "none"):
            return None
        return int(s)
    except (ValueError, TypeError):
        return None


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
        is_final = "final" in status or status in ("closed", "complete")
        if not is_final:
            continue


        hs = to_int(g.get("home_score"))
        as_ = to_int(g.get("away_score"))
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

import time
from .db import get_conn

def reset_all_elos(base_elo: float = 1500.0) -> int:
    conn = get_conn()
    cur = conn.execute("UPDATE teams SET elo=?", (base_elo,))
    conn.commit()
    conn.close()
    return cur.rowcount

def mark_day_processed(day_iso: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO elo_runs(day, processed_at) VALUES(?, ?)",
        (day_iso, int(time.time()))
    )
    conn.commit()
    conn.close()

def is_day_processed(day_iso: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT day FROM elo_runs WHERE day=?", (day_iso,)).fetchone()
    conn.close()
    return row is not None

def clear_processed_days() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM elo_runs")
    conn.commit()
    conn.close()

from datetime import date, timedelta
import time as _time

from .ncaa import get_scoreboard, extract_games

def rebuild_elo_range(start: date, end: date, sleep_seconds: float = 0.15) -> dict:
    """
    Rebuild Elo by replaying games from start..end inclusive.
    - Resets existing team elos to 1500
    - Skips already processed days (elo_runs table)
    """
    if end < start:
        return {"ok": False, "error": "end must be >= start"}

    reset_count = reset_all_elos(1500.0)
    clear_processed_days()

    processed_days = 0
    total_games_updated = 0
    days_with_games = 0

    d = start
    while d <= end:
        day_iso = d.isoformat()

        sb = get_scoreboard(d)
        games = extract_games(sb)

        # Apply updates for finals only
        result = update_elo_from_games(games)
        games_updated = int(result.get("games_updated", 0))

        if games_updated > 0:
            days_with_games += 1

        total_games_updated += games_updated
        processed_days += 1
        mark_day_processed(day_iso)

        d += timedelta(days=1)
        _time.sleep(sleep_seconds)

    return {
        "ok": True,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "teams_reset": reset_count,
        "days_processed": processed_days,
        "days_with_updates": days_with_games,
        "games_updated": total_games_updated,
    }
