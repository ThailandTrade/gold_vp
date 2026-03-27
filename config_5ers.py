"""
Config 5ers — Multi-instrument (optimise 2026-03-26)
Max DD 5ers: 4% challenge
Filtre: toutes strats marge WR > 5%
"""
BROKER = '5ers'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0025,
        'portfolio': [
            'PO3_SWEEP',       # TRAIL 3.0/0.75/0.50  PF=1.48 WR=77%
            'ALL_PSAR_EMA',    # TRAIL 3.0/1.00/0.30  PF=1.30 WR=72%
            'TOK_2BAR',        # TRAIL 2.0/1.00/0.75  PF=1.32 WR=58%
            'ALL_DC10',        # TRAIL 3.0/1.00/0.75  PF=1.30 WR=66%
            'TOK_BIG',         # TRAIL 3.0/1.00/0.50  PF=1.33 WR=70%
            'TOK_PREVEXT',     # TRAIL 2.0/0.75/0.75  PF=1.39 WR=56%
        ],
        # PF 1.32 | WR 68% | DD -3.6% @ 0.25% | Rend +45% | 11/13
    },
    'JPN225': {
        'risk_pct': 0.0025,
        'portfolio': [
            'ALL_FIB_618',     # TRAIL 3.0  PF=1.95 WR=82%
            'IDX_LATE_REV',    # TRAIL 3.0  PF=1.47 WR=83%
            'D8',              # TRAIL 1.5  PF=2.02 WR=62%
            'TOK_NR4',         # TRAIL 1.5  PF=1.41 WR=64%
            'LON_GAP',         # TRAIL 2.0  PF=1.38 WR=68%
            'LON_DC10_MOM',    # TRAIL 3.0  PF=1.55 WR=74%
            'LON_TOKEND',      # TRAIL 3.0  PF=1.30 WR=70%
            'ALL_MACD_RSI',    # TRAIL 3.0  PF=1.26 WR=79%
            'TOK_PREVEXT',     # TPSL  3.0  PF=1.49 WR=74%
        ],
        # PF*WR 9: PF 1.85 | WR 79% | DD -2.0% @ 0.25% | +258% | 13/13
    },
    'DAX40': {
        'risk_pct': 0.0025,
        'portfolio': [
            # TODO: run analyze_combos.py 5ers --symbol dax40
        ],
        # PF 1.60 | WR 67% | DD -1.9% @ 0.25% | 13/13
    },
    'BTCUSD': {
        'risk_pct': 0.0025,
        'portfolio': [
            # TODO: run analyze_combos.py 5ers --symbol btcusd
        ],
        # PF 1.47 | WR 54% | DD -3.2% @ 0.25% | 12/13
    },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
