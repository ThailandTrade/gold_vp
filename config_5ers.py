"""
Config 5ers — Multi-instrument (optimise 2026-03-26)
Max DD 5ers: 4% challenge
Filtre: toutes strats marge WR > 5%
"""
BROKER = '5ers'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
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
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_FIB_618',     # TRAIL 3.0  PF=1.95 WR=82%
            'IDX_LATE_REV',    # TRAIL 3.0  PF=1.47 WR=83%
            'D8',              # TRAIL 1.5  PF=2.02 WR=62%
            'TOK_NR4',         # TRAIL 1.5  PF=1.41 WR=64%
            'LON_DC10_MOM',    # TRAIL 3.0  PF=1.55 WR=74%
            'LON_TOKEND',      # TRAIL 3.0  PF=1.30 WR=70%
            'ALL_MACD_RSI',    # TRAIL 3.0  PF=1.26 WR=79%
            'TOK_PREVEXT',     # TPSL  3.0  PF=1.49 WR=74%
        ],
        # PF*WR 9: PF 1.85 | WR 79% | DD -2.0% @ 0.25% | +258% | 13/13
    },
    'DAX40': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_MACD_HIST',   # TRAIL 1.5/0.30/0.30  PF=1.96 WR=68%
            'TOK_FADE',        # TRAIL 3.0/0.50/0.50  PF=1.58 WR=71%
            'ALL_FIB_618',     # TRAIL 3.0/0.30/0.30  PF=1.72 WR=77%
            'ALL_ENGULF',      # TRAIL 3.0/0.30/0.30  PF=1.59 WR=80%
            'TOK_BIG',         # TRAIL 3.0/0.30/0.30  PF=1.47 WR=74%
            'ALL_FISHER_9',    # TRAIL 3.0/0.30/0.30  PF=1.61 WR=74%
        ],
        # MinDD6: PF 1.97 | WR 77% | DD -8.0% @ 0.25% | Rend +768% | 13/13
    },
    'BTCUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_PREVEXT',     # TRAIL 0.5/0.30/0.50  PF=3.97 WR=29%
            'ALL_EMA_513',     # TPSL  2.5/0.75       PF=1.39 WR=82%
            'PO3_SWEEP',       # TRAIL 3.0/0.50/0.50  PF=2.49 WR=85%
            'ALL_HAMMER',      # TRAIL 3.0/0.30/0.30  PF=1.44 WR=80%
        ],
        # MinDD4: PF 1.73 | WR 79% | DD -7.1% @ 0.25% | Rend +251% | 13/13
    },
    'NAS100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',              # TRAIL 1.5/0.50/0.30  PF=2.02 WR=62%
            'ALL_DC50',        # TPSL  3.0/0.50       PF=1.54 WR=89%
            'ALL_DC10_EMA',    # TPSL  2.5/0.75       PF=1.47 WR=81%
            'TOK_FISHER',      # TRAIL 2.0/0.30/0.30  PF=1.34 WR=75%
            'TOK_PREVEXT',     # TPSL  3.0/1.50       PF=1.49 WR=74%
            'ALL_FVG_BULL',    # TRAIL 2.0/0.30/0.30  PF=1.49 WR=78%
            'ALL_MACD_HIST',   # TRAIL 1.5/0.30/0.30  PF=1.32 WR=69%
            'IDX_PREV_HL',     # TRAIL 3.0/0.30/0.30  PF=1.44 WR=67%
            'ALL_MSTAR',       # TPSL  2.5/0.50       PF=1.52 WR=85%
            'TOK_NR4',         # TRAIL 1.5/0.50/0.50  PF=1.41 WR=64%
        ],
        # MinDD10: PF 1.40 | WR 77% | DD -0.4% @ 0.05% | Rend +8% | 13/13
    },
    'SP500': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_DOJI_REV',    # TPSL  3.0/0.25       PF=2.31 WR=94%
            'ALL_ICHI_TK',     # TPSL  3.0/0.50       PF=1.60 WR=90%
            'ALL_DC50',        # TPSL  3.0/0.50       PF=1.82 WR=90%
            'ALL_3SOLDIERS',   # TRAIL 3.0/0.30/0.30  PF=1.52 WR=82%
            'TOK_FISHER',      # TRAIL 3.0/0.50/0.50  PF=1.33 WR=78%
            'IDX_CONSEC_REV',  # TRAIL 1.5/0.50/0.50  PF=1.62 WR=66%
            'ALL_FIB_618',     # TRAIL 3.0/1.00/1.00  PF=1.36 WR=69%
            'ALL_MACD_HIST',   # TRAIL 1.0/0.50/0.50  PF=1.28 WR=56%
            'ALL_PSAR_EMA',    # TRAIL 3.0/1.00/1.00  PF=1.43 WR=68%
            'IDX_RSI_REV',     # TRAIL 1.5/0.30/0.30  PF=1.55 WR=70%
            'LON_PREV',        # TRAIL 3.0/0.30/0.30  PF=1.53 WR=79%
        ],
        # MinDD11: PF 1.48 | WR 78% | DD -0.7% @ 0.05% | Rend +13% | 13/13
    },
    'UK100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',  # TPSL  3.0/1.00       PF=1.73 WR=81%
            'NY_HMA_CROSS',    # TRAIL 2.0/0.30/0.30  PF=1.66 WR=71%
            'IDX_LATE_REV',    # TRAIL 2.0/0.30/0.30  PF=1.66 WR=77%
        ],
        # PF3: PF 1.66 | WR 77% | DD -0.4% @ 0.05% | Rend +6% | 13/13
    },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
