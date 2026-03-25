"""
Config 5ers — Prop firm — MinDD 10 (optimise 2026-03-25 sur donnees 5ers)
Risk: 0.25% par trade | PF 1.46 | WR 74% | DD -2.5% | Rend +104% | 11/13 mois
Source: analyze_combos.py 5ers (critere MinDD, taille 10, scale 0.25x)
Max DD 5ers: 4% challenge → marge confortable a -2.5%
"""
BROKER = '5ers'
RISK_PCT = 0.0025

PORTFOLIO = [
    'TOK_PREVEXT',     # TRAIL 2.0/1.00/1.00  PF=1.86 WR=51%
    'LON_TOKEND',      # TRAIL 3.0/0.75/0.30  PF=1.12 WR=69%
    'LON_PREV',        # TRAIL 3.0/1.00/0.75  PF=1.21 WR=70%
    'TOK_BIG',         # TRAIL 3.0/0.30/0.30  PF=1.24 WR=71%
    'PO3_SWEEP',       # TRAIL 3.0/0.50/0.30  PF=1.18 WR=81%
    'LON_PIN',         # TPSL  3.0/1.50       PF=1.14 WR=72%
    'ALL_ADX_FAST',    # TPSL  3.0/1.00       PF=1.07 WR=80%
    'TOK_WILLR',       # TPSL  3.0/1.50       PF=1.11 WR=71%
    'ALL_KC_BRK',      # TRAIL 3.0/1.00/0.75  PF=1.37 WR=70%
    'TOK_FADE',        # TRAIL 1.5/0.75/0.50  PF=1.07 WR=54%
]
