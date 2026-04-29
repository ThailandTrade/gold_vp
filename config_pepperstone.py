"""
Config Pepperstone — compte propre 2026-04-29
Capital $200, risk 0.5%, pas de DD max, server UTC+3.
A remplir apres optimization (pipeline: optimize -> strat_exits -> combos -> config -> bt -> audit -> live).
"""
BROKER = 'pepperstone'

ALL_INSTRUMENTS = {
    # Sera rempli apres exploration des symboles disponibles + optimization par instrument
}

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = []
