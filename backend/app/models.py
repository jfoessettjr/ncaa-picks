from pydantic import BaseModel

class Pick(BaseModel):
    date: str
    home: str
    away: str
    pick: str
    win_prob: float
    confidence: str
