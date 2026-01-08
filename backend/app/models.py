from sqlalchemy import Column, String, Float, Integer, Text
from .db import Base

class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    elo = Column(Float, nullable=False, default=1500.0)

class Cache(Base):
    __tablename__ = "cache"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    created_at = Column(Integer, nullable=False)

class EloRun(Base):
    __tablename__ = "elo_runs"
    day = Column(String, primary_key=True)         # YYYY-MM-DD
    processed_at = Column(Integer, nullable=False) # unix ts
