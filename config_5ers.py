"""
Config 5ers — Prop firm — MinDD 5 (optimise 2026-03-23)
Risk: 0.5% par trade | PF 1.62 | WR 82% | DD -2.5% | Rend +83% | 12/13 mois
Source: analyze_combos.py (critere MinDD, taille 5, scale 0.5x)
Max DD 5ers: 4% challenge → marge confortable a -2.5%
"""
BROKER = '5ers'
RISK_PCT = 0.005
SPREAD_OVERRIDE = 0.20

PORTFOLIO = [
    'PO3_SWEEP',       # TRAIL 3.0/0.75/0.75  PF=2.46 WR=79%
    'TOK_2BAR',        # TRAIL 3.0/0.50/0.50  PF=1.61 WR=75%
    'LON_TOKEND',      # TRAIL 3.0/0.30/0.30  PF=1.81 WR=68%
    'ALL_AO_SAUCER',   # TPSL  3.0/0.50       PF=1.23 WR=88%
    'ALL_CCI_14_ZERO', # TPSL  3.0/0.50       PF=1.13 WR=87%
]
