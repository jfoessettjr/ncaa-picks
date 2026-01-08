from __future__ import annotations

from datetime import date, timedelta
import time

from .db import SessionLocal
from .elo import win_prob
from .repo import (
    get_or_create_team,
    set_team_elo,
    reset_all_elos,
    mark_day_processed,
    clear_processed_days,
)
from .ncaa import get_scoreboard, extract_games


def to_int(x):
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == "" or s.lower() in ("-", "—", "n/a", "none"):
            return None
        return int(s)
    except (ValueError, TypeError):
        return None


def elo_delta(elo_a: float, elo_b: float, score_a: int, score_b: int, k: float = 20.0) -> float:
    """
    Returns change to team A Elo. Team B gets -delta.
    Simple Elo with a light margin-of-victory multiplier.
    """
    expected = win_prob(elo_a, elo_b)
    actual = 1.0 if score_a > score_b else 0.0

    margin = abs(score_a - score_b)
    mov_mult = 1.0 + min(margin, 25) / 25.0 * 0.25  # up to +25%
    return k * mov_mult * (actual - expected)


def update_elo_from_games(games: list[dict]) -> dict:
    """
    games items must include:
    home_id, away_id, home_name, away_name, status, home_score, away_score
    """
    updated = 0

    db = SessionLocal()
    try:
        for g in games:
            status = (g.get("status") or "").strip().lower()
            is_final = ("final" in status) or (status in ("final", "closed", "complete"))
            if not is_final:
                continue

            hs = to_int(g.get("home_score"))
            as_ = to_int(g.get("away_score"))
            if hs is None or as_ is None:
                continue

            home = get_or_create_team(db, g["home_id"], g["home_name"])
            away = get_or_create_team(db, g["away_id"], g["away_name"])

            d_home = elo_delta(home.elo, away.elo, hs, as_)
            set_team_elo(db, home.id, home.elo + d_home)
            set_team_elo(db, away.id, away.elo - d_home)

            updated += 1

        db.commit()
        return {"games_updated": updated}
    finally:
        db.close()


def rebuild_elo_range(start: date, end: date, sleep_seconds: float = 0.15) -> dict:
    """
    Rebuild Elo by replaying games from start..end inclusive.
    - Resets existing team elos to 1500
    - Clears elo_runs and then records each day as processed
    """
    if end < start:
        return {"ok": False, "error": "end must be >= start"}

    db = SessionLocal()
    try:
        reset_count = reset_all_elos(db, 1500.0)
        clear_processed_days(db)
        db.commit()
    finally:
        db.close()

    processed_days = 0
    total_games_updated = 0
    days_with_updates = 0

    d = start
    while d <= end:
        day_iso = d.isoformat()

        sb = get_scoreboard(d)
        games = extract_games(sb)

        result = update_elo_from_games(games)
        games_updated = int(result.get("games_updated", 0))

        if games_updated > 0:
            days_with_updates += 1

        total_games_updated += games_updated
        processed_days += 1

        db = SessionLocal()
        try:
            mark_day_processed(db, day_iso)
            db.commit()
        finally:
            db.close()

        d += timedelta(days=1)
        time.sleep(sleep_seconds)

    return {
        "ok": True,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "teams_reset": reset_count,
        "days_processed": processed_days,
        "days_with_updates": days_with_updates,
        "games_updated": total_games_updated,
    }
