"""
Config FTMO — Prop firm — Calmar 5 (optimise 2026-03-25 sur donnees FTMO)
Risk: 0.5% par trade | PF 1.41 | WR 66% | DD -9.1% | Rend +269% | 11/13 mois
Source: analyze_combos.py ftmo (critere Calmar, taille 5)
Max DD FTMO: 10% → marge 0.9%
"""
BROKER = 'FTMO'
RISK_PCT = 0.005

PORTFOLIO = [
    'PO3_SWEEP',       # TRAIL 3.0/0.75/0.75  PF=1.81 WR=67%
    'LON_PREV',        # TRAIL 2.0/0.75/0.75  PF=1.50 WR=71%
    'ALL_PSAR_EMA',    # TPSL  3.0/1.50       PF=1.32 WR=72%
    'TOK_2BAR',        # TRAIL 3.0/0.50/0.50  PF=1.44 WR=61%
    'ALL_DC10',        # TRAIL 3.0/0.75/0.75  PF=1.33 WR=66%
]
