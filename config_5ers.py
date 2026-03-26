"""
Config 5ers — Prop firm — Calmar 6 (optimise 2026-03-26 sur donnees 5ers)
Risk: 0.25% par trade | PF 1.32 | WR 68% | DD -3.6% | Rend +45% | 11/13 mois
Source: analyze_combos.py 5ers (critere Calmar, taille 6)
Filtre: toutes strats marge WR > 5% (RR sain, rentable avec frais)
Max DD 5ers: 4% challenge → marge a -3.6%
"""
BROKER = '5ers'
RISK_PCT = 0.0025

PORTFOLIO = [
    'PO3_SWEEP',       # TRAIL 3.0/0.75/0.50  PF=1.48 WR=77%
    'ALL_PSAR_EMA',    # TRAIL 3.0/1.00/0.30  PF=1.30 WR=72%
    'TOK_2BAR',        # TRAIL 2.0/1.00/0.75  PF=1.32 WR=58%
    'ALL_DC10',        # TRAIL 3.0/1.00/0.75  PF=1.30 WR=66%
    'TOK_BIG',         # TRAIL 3.0/1.00/0.50  PF=1.33 WR=70%
    'TOK_PREVEXT',     # TRAIL 2.0/0.75/0.75  PF=1.39 WR=56%
]
