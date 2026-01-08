import math

def win_prob(elo_a: float, elo_b: float) -> float:
    # Probability team A beats team B
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def pick_winner(home_elo: float, away_elo: float, home_adv: float = 50.0):
    # simple home court bump
    p_home = win_prob(home_elo + home_adv, away_elo)
    if p_home >= 0.5:
        return "HOME", p_home
    return "AWAY", 1 - p_home
