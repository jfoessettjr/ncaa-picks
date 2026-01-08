import time
from sqlalchemy.orm import Session
from .models import Team, Cache, EloRun

# ---- Teams ----
def get_or_create_team(db: Session, team_id: str, name: str, base_elo: float = 1500.0) -> Team:
    t = db.get(Team, team_id)
    if t:
        # keep latest name if it changes slightly
        if name and t.name != name:
            t.name = name
        return t
    t = Team(id=team_id, name=name, elo=base_elo)
    db.add(t)
    return t

def set_team_elo(db: Session, team_id: str, elo: float):
    t = db.get(Team, team_id)
    if not t:
        # should not happen if you call get_or_create_team first
        t = Team(id=team_id, name=team_id, elo=elo)
        db.add(t)
    else:
        t.elo = float(elo)

def reset_all_elos(db: Session, base_elo: float = 1500.0) -> int:
    # Returns number of rows updated
    rows = db.query(Team).update({Team.elo: float(base_elo)})
    return rows

# ---- Cache ----
def cache_get(db: Session, key: str):
    return db.get(Cache, key)

def cache_set(db: Session, key: str, value: str, created_at: int | None = None):
    created_at = created_at or int(time.time())
    c = db.get(Cache, key)
    if c:
        c.value = value
        c.created_at = created_at
    else:
        db.add(Cache(key=key, value=value, created_at=created_at))

# ---- Elo Runs ----
# ---- Elo Runs ----
def is_day_processed(db: Session, day_iso: str) -> bool:
    return db.get(EloRun, day_iso) is not None

def mark_day_processed(db: Session, day_iso: str):
    r = db.get(EloRun, day_iso)
    ts = int(time.time())
    if r:
        r.processed_at = ts
    else:
        db.add(EloRun(day=day_iso, processed_at=ts))

def clear_processed_days(db: Session):
    db.query(EloRun).delete()

