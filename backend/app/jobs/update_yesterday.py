from datetime import date, timedelta

from app.db import init_db
from app.ncaa import get_scoreboard, extract_games
from app.elo_update import update_elo_from_games


def main():
    init_db()

    d = date.today() - timedelta(days=1)

    sb = get_scoreboard(d)
    games = extract_games(sb)

    result = update_elo_from_games(games)
    print(f"[cron] Updated Elo for {d.isoformat()}: {result}")


if __name__ == "__main__":
    main()
