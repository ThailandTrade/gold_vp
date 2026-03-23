"""
Config ICMarkets — Compte propre — Calmar 12 (optimise 2026-03-23)
Risk: 1% par trade | PF 1.62 | WR 72% | DD -12.5% | Rend +3523% | 13/13 mois
Source: optimize_all.py + analyze_combos.py (critere Calmar, taille 12)
"""
BROKER = 'ICMarkets'
RISK_PCT = 0.01

PORTFOLIO = [
    'PO3_SWEEP',       # TRAIL 3.0/0.75/0.75  PF=2.46 WR=79%
    'LON_PREV',        # TRAIL 2.0/0.75/0.75  PF=1.19 WR=63%
    'TOK_2BAR',        # TRAIL 3.0/0.50/0.50  PF=1.61 WR=75%
    'LON_KZ',          # TRAIL 3.0/0.50/0.30  PF=1.80 WR=82%
    'ALL_KC_BRK',      # TRAIL 3.0/1.00/0.75  PF=1.20 WR=69%
    'ALL_3SOLDIERS',   # TPSL  3.0/2.00       PF=1.34 WR=67%
    'ALL_FVG_BULL',    # TRAIL 3.0/1.00/0.75  PF=1.63 WR=70%
    'LON_BIGGAP',      # TRAIL 3.0/0.75/0.50  PF=1.70 WR=74%
    'ALL_MACD_RSI',    # TRAIL 1.5/0.50/0.50  PF=1.67 WR=60%
    'TOK_BIG',         # TRAIL 3.0/0.30/0.30  PF=1.57 WR=76%
    'TOK_PREVEXT',     # TRAIL 1.5/0.75/1.00  PF=1.53 WR=51%
    'LON_TOKEND',      # TRAIL 3.0/0.30/0.30  PF=1.81 WR=68%
]
