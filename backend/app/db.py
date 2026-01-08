import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "ncaa.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  elo REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cache (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS elo_runs (
  day TEXT PRIMARY KEY,
  processed_at INTEGER NOT NULL
);
"""

def get_conn() -> sqlite3.Connection:
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn

def init_db():
  conn = get_conn()
  conn.executescript(SCHEMA)
  conn.commit()
  conn.close()
