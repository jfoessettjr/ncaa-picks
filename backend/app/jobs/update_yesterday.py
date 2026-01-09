from datetime import date, timedelta
import sys

from app.db import init_db
from app.ncaa import get_scoreboard, extract_games
from app.elo_update import update_elo_from_games


def main():
    init_db()

    d = date.today() - timedelta(days=1)
    print(f"[cron] Running Elo update for {d.isoformat()}")

    try:
        sb = get_scoreboard(d)
        games = extract_games(sb)
    except Exception as e:
        print(f"[cron][ERROR] Failed to fetch games: {e}")
        sys.exit(1)

    if not games:
        print(f"[cron] No games found for {d.isoformat()}")
        return

    try:
        result = update_elo_from_games(games)
        print(f"[cron] Elo update complete: {result}")
    except Exception as e:
        print(f"[cron][ERROR] Elo update failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
