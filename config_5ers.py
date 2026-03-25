"""
Config 5ers — Prop firm — Calmar 5 (optimise 2026-03-25 sur donnees 5ers)
Risk: 0.25% par trade | PF 1.38 | WR 67% | DD -2.4% | Rend +43% | 11/13 mois
Source: optimize_all.py 5ers + analyze_combos.py 5ers (critere Calmar, taille 5, scale 0.25x)
Max DD 5ers: 4% challenge → marge confortable a -2.4%
"""
BROKER = '5ers'
RISK_PCT = 0.0025

PORTFOLIO = [
    'TOK_PREVEXT',     # TRAIL 2.0/1.00/1.00  PF=1.86 WR=51%
    'TOK_2BAR',        # TRAIL 3.0/1.00/1.00  PF=1.43 WR=65%
    'ALL_PSAR_EMA',    # TRAIL 3.0/1.00/0.30  PF=1.27 WR=70%
    'ALL_FVG_BULL',    # TRAIL 3.0/0.30/0.30  PF=1.60 WR=72%
    'NY_LONEND',       # TRAIL 2.0/0.30/0.30  PF=1.19 WR=54%
]
