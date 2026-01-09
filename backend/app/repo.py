import time
from sqlalchemy.orm import Session
from .models import Team, Cache, EloRun

# ---- Teams ----
def get_or_create_team(db: Session, team_id: str, name: str, base_elo: float = 1500.0) -> Team:
    # NOTE: with autoflush=False, db.get won't see pending inserts unless we flush
    t = db.get(Team, team_id)
    if t:
        if name and t.name != name:
            t.name = name
        return t

    t = Team(id=team_id, name=name, elo=base_elo)
    db.add(t)
    db.flush()  # <-- critical: makes the pending row visible to subsequent db.get calls
    return t

def set_team_elo(db: Session, team_id: str, elo: float):
    t = db.get(Team, team_id)
    if not t:
        t = Team(id=team_id, name=team_id, elo=float(elo))
        db.add(t)
        db.flush()  # <-- also flush here in case called before get_or_create_team
    else:
        t.elo = float(elo)

def reset_all_elos(db: Session, base_elo: float = 1500.0) -> int:
    return db.query(Team).update({Team.elo: float(base_elo)})

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
