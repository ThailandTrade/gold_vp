"""
Exit configs par (broker, instrument, strat) â€” genere depuis optimize_all.py pkl.
Format: STRAT_EXITS[(broker, symbol)] = {strat: (type, p1, p2, p3)}
TRAIL: (TRAIL, sl, act, trail)
TPSL:  (TPSL, sl, tp, 0)
"""

DEFAULT_EXIT = ("TRAIL", 3.0, 0.5, 0.5)

STRAT_EXITS = {}

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    'ALL_3SOLDIERS': ('TPSL', 3.00, 2.00, 0),  # PF=1.23 WR=69%
    'ALL_ADX_FAST': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.13 WR=69%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.52 WR=67%
    'ALL_CCI_14_ZERO': ('TRAIL', 2.00, 0.75, 0.50),  # PF=1.31 WR=59%
    'ALL_CCI_20_ZERO': ('TRAIL', 3.00, 0.30, 0.75),  # PF=1.15 WR=49%
    'ALL_CMO_14': ('TPSL', 1.00, 3.00, 0),  # PF=1.15 WR=26%
    'ALL_CMO_9': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.10 WR=54%
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.27 WR=60%
    'ALL_DC10': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.32 WR=65%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.28 WR=65%
    'ALL_DC50': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.10 WR=67%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.50),  # PF=1.45 WR=60%
    'ALL_FVG_BULL': ('TRAIL', 1.50, 0.75, 0.30),  # PF=1.23 WR=56%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.41 WR=61%
    'ALL_KC_BRK': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.17 WR=67%
    'ALL_MACD_ADX': ('TRAIL', 3.00, 0.50, 0.75),  # PF=1.25 WR=57%
    'ALL_MACD_MED_SIG': ('TRAIL', 1.00, 0.75, 1.00),  # PF=1.28 WR=32%
    'ALL_MACD_RSI': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.21 WR=59%
    'ALL_MACD_STD_SIG': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.45 WR=73%
    'ALL_MTF_BRK': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.14 WR=65%
    'ALL_NR4': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.08 WR=69%
    'ALL_PIVOT_BRK': ('TRAIL', 1.50, 0.75, 0.50),  # PF=1.17 WR=54%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 1.00, 0.30),  # PF=1.32 WR=72%
    'ALL_RSI_50': ('TRAIL', 1.00, 0.75, 0.75),  # PF=1.19 WR=36%
    'ALL_RSI_DIV': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.07 WR=56%
    'ALL_WILLR_14': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.18 WR=59%
    'D8': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.46 WR=51%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.31 WR=73%
    'LON_GAP': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.26 WR=70%
    'LON_KZ': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.52 WR=76%
    'LON_PREV': ('TRAIL', 2.00, 1.00, 0.75),  # PF=1.09 WR=61%
    'LON_TOKEND': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.50 WR=71%
    'NY_DAYMOM': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.14 WR=59%
    'NY_GAP': ('TPSL', 1.50, 3.00, 0),  # PF=1.18 WR=36%
    'NY_HMA_CROSS': ('TPSL', 2.50, 2.00, 0),  # PF=1.05 WR=55%
    'NY_LONEND': ('TRAIL', 1.00, 0.50, 0.30),  # PF=1.20 WR=36%
    'NY_LONMOM': ('TRAIL', 1.00, 0.50, 0.30),  # PF=1.12 WR=36%
    'PO3_SWEEP': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.81 WR=67%
    'TOK_2BAR': ('TRAIL', 2.00, 1.00, 0.75),  # PF=1.44 WR=61%
    'TOK_BIG': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.09 WR=73%
    'TOK_FADE': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.14 WR=38%
    'TOK_MACD_MED': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.26 WR=40%
    'TOK_NR4': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.21 WR=66%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.75, 0.30),  # PF=1.30 WR=61%
    'TOK_WILLR': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.29 WR=60%
}

STRAT_EXITS[('5ers', 'XAUUSD')] = {
    'ALL_3SOLDIERS': ('TPSL', 2.50, 2.00, 0),  # PF=1.25 WR=63%
    'ALL_BB_SQUEEZE': ('TPSL', 2.50, 1.50, 0),  # PF=1.36 WR=69%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.36 WR=67%
    'ALL_CCI_14_ZERO': ('TRAIL', 1.50, 0.75, 0.50),  # PF=1.36 WR=56%
    'ALL_DC10': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.30 WR=66%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.26 WR=66%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.28 WR=65%
    'ALL_FVG_BULL': ('TRAIL', 1.50, 1.00, 0.30),  # PF=1.46 WR=55%
    'ALL_MACD_STD_SIG': ('TRAIL', 3.00, 0.50, 0.75),  # PF=1.31 WR=56%
    'ALL_NR4': ('TRAIL', 1.00, 0.30, 0.75),  # PF=1.43 WR=38%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 1.00, 0.30),  # PF=1.30 WR=72%
    'D8': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.25 WR=50%
    'IDX_CONSEC_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=63%
    'IDX_NR4': ('TRAIL', 1.00, 0.30, 0.75),  # PF=1.43 WR=38%
    'LON_KZ': ('TPSL', 2.50, 0.75, 0),  # PF=1.38 WR=83%
    'LON_TOKEND': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.30 WR=70%
    'PO3_SWEEP': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.48 WR=77%
    'TOK_2BAR': ('TRAIL', 2.00, 1.00, 0.75),  # PF=1.32 WR=58%
    'TOK_BIG': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.33 WR=70%
    'TOK_NR4': ('TRAIL', 1.00, 0.50, 0.75),  # PF=1.37 WR=38%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.39 WR=56%
    'TOK_WILLR': ('TRAIL', 3.00, 0.50, 0.75),  # PF=1.29 WR=51%
}

STRAT_EXITS[('5ers', 'JPN225')] = {
    'ALL_CMO_14': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.27 WR=71%
    'ALL_EMA_513': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.27 WR=64%
    'ALL_EMA_921': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.32 WR=70%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.95 WR=82%
    'ALL_FISHER_9': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.35 WR=63%
    'ALL_MACD_FAST_SIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.36 WR=76%
    'ALL_MACD_FAST_ZERO': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.27 WR=64%
    'ALL_MACD_RSI': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.36 WR=81%
    'ALL_MTF_BRK': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.38 WR=80%
    'ALL_NR4': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.59 WR=78%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.34 WR=80%
    'ALL_WILLR_14': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.49 WR=63%
    'ALL_WILLR_7': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.41 WR=75%
    'D8': ('TRAIL', 3.00, 0.75, 1.00),  # PF=1.83 WR=63%
    'IDX_GAP_CONT': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.38 WR=82%
    'IDX_LATE_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.47 WR=83%
    'IDX_NR4': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.59 WR=78%
    'IDX_ORB15': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.39 WR=76%
    'LON_DC10': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.55 WR=74%
    'LON_DC10_MOM': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.55 WR=74%
    'LON_GAP': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.38 WR=68%
    'LON_TOKEND': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.27 WR=66%
    'NY_LONEND': ('TRAIL', 2.00, 1.00, 0.30),  # PF=1.35 WR=61%
    'TOK_MACD_MED': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.40 WR=74%
    'TOK_NR4': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.56 WR=79%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.33 WR=56%
}

STRAT_EXITS[('5ers', 'DAX40')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.43 WR=78%
    'ALL_ADX_FAST': ('TRAIL', 0.50, 0.50, 0.30),  # PF=1.39 WR=37%
    'ALL_BB_SQUEEZE': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.39 WR=75%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.42 WR=74%
    'ALL_CCI_14_ZERO': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.32 WR=71%
    'ALL_CCI_20_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.56 WR=81%
    'ALL_CONSEC_REV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.48 WR=57%
    'ALL_DC10': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.60 WR=74%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.60 WR=74%
    'ALL_DC50': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.47 WR=76%
    'ALL_DOJI_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.25 WR=63%
    'ALL_DPO_14': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.50 WR=79%
    'ALL_ENGULF': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.59 WR=80%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.72 WR=77%
    'ALL_FISHER_9': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.61 WR=74%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.91 WR=82%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.47 WR=77%
    'ALL_HMA_DIR': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.31 WR=74%
    'ALL_KC_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.40 WR=74%
    'ALL_MACD_FAST_SIG': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.27 WR=70%
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.96 WR=68%
    'ALL_MACD_STD_SIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.49 WR=80%
    'ALL_MOM_10': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.42 WR=76%
    'ALL_MSTAR': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.48 WR=46%
    'ALL_MTF_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.69 WR=75%
    'ALL_PSAR_EMA': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.42 WR=47%
    'ALL_RSI_50': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.52 WR=78%
    'ALL_RSI_DIV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.38 WR=57%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.44 WR=60%
    'ALL_WILLR_14': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.37 WR=62%
    'ALL_WILLR_7': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=74%
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.54 WR=78%
    'IDX_CONSEC_REV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.28 WR=70%
    'IDX_ENGULF': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.59 WR=80%
    'IDX_GAP_FILL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.27 WR=67%
    'IDX_KC_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.40 WR=74%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.52 WR=67%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.44 WR=60%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.55 WR=65%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.23 WR=52%
    'LON_GAP': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.26 WR=51%
    'TOK_BIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.47 WR=74%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.58 WR=71%
    'TOK_FISHER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.84 WR=68%
    'TOK_WILLR': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.44 WR=62%
}

STRAT_EXITS[('5ers', 'BTCUSD')] = {
    'ALL_CMO_14': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.29 WR=74%
    'ALL_EMA_513': ('TPSL', 2.50, 0.75, 0),  # PF=1.39 WR=82%
    'ALL_HAMMER': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.44 WR=80%
    'ALL_MACD_FAST_ZERO': ('TPSL', 2.50, 0.75, 0),  # PF=1.39 WR=82%
    'ALL_MACD_MED_SIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=80%
    'ALL_MSTAR': ('TRAIL', 0.50, 0.50, 0.50),  # PF=1.70 WR=47%
    'ALL_NR4': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.29 WR=39%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 1.00, 1.00, 0.30),  # PF=1.29 WR=43%
    'ALL_RSI_EXTREME': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=78%
    'D8': ('TRAIL', 1.50, 0.30, 0.75),  # PF=1.70 WR=60%
    'IDX_CONSEC_REV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.44 WR=57%
    'IDX_GAP_CONT': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.38 WR=67%
    'IDX_GAP_FILL': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.23 WR=57%
    'IDX_NR4': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.29 WR=39%
    'IDX_RSI_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=78%
    'NY_DAYMOM': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.30 WR=67%
    'PO3_SWEEP': ('TRAIL', 3.00, 0.50, 0.50),  # PF=2.49 WR=85%
    'TOK_2BAR': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.31 WR=72%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.56 WR=80%
    'TOK_FISHER': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.24 WR=39%
    'TOK_NR4': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.30 WR=39%
    'TOK_PREVEXT': ('TRAIL', 0.50, 0.30, 0.50),  # PF=3.97 WR=29%
}

STRAT_EXITS[('5ers', 'NAS100')] = {
    'ALL_3SOLDIERS': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.42 WR=62%
    'ALL_DC10': ('TPSL', 2.50, 0.75, 0),  # PF=1.45 WR=81%
    'ALL_DC10_EMA': ('TPSL', 2.50, 0.75, 0),  # PF=1.47 WR=81%
    'ALL_DC50': ('TPSL', 3.00, 0.50, 0),  # PF=1.54 WR=89%
    'ALL_DPO_14': ('TRAIL', 2.00, 0.30, 0.50),  # PF=1.27 WR=61%
    'ALL_EMA_513': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.29 WR=72%
    'ALL_EMA_821': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.36 WR=81%
    'ALL_FISHER_9': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.31 WR=74%
    'ALL_FVG_BULL': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.49 WR=78%
    'ALL_MACD_FAST_ZERO': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.29 WR=72%
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.32 WR=69%
    'ALL_MSTAR': ('TPSL', 2.50, 0.50, 0),  # PF=1.52 WR=85%
    'ALL_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.25 WR=62%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.24 WR=65%
    'ALL_RSI_50': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.54 WR=74%
    'ALL_WILLR_7': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.34 WR=64%
    'D8': ('TRAIL', 1.50, 0.50, 0.30),  # PF=2.02 WR=62%
    'IDX_BB_REV': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.27 WR=69%
    'IDX_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.25 WR=62%
    'IDX_NY_MOM': ('TPSL', 3.00, 3.00, 0),  # PF=1.24 WR=54%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.44 WR=67%
    'LON_BIGGAP': ('TRAIL', 3.00, 1.00, 0.30),  # PF=1.36 WR=68%
    'LON_PIN': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.25 WR=67%
    'LON_PREV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.32 WR=76%
    'TOK_FISHER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.34 WR=75%
    'TOK_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.41 WR=64%
    'TOK_PREVEXT': ('TPSL', 3.00, 1.50, 0),  # PF=1.49 WR=74%
}

STRAT_EXITS[('5ers', 'SP500')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.52 WR=82%
    'ALL_DC50': ('TPSL', 3.00, 0.50, 0),  # PF=1.82 WR=90%
    'ALL_DOJI_REV': ('TPSL', 3.00, 0.25, 0),  # PF=2.31 WR=94%
    'ALL_FIB_618': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.36 WR=69%
    'ALL_ICHI_TK': ('TPSL', 3.00, 0.50, 0),  # PF=1.60 WR=90%
    'ALL_MACD_FAST_SIG': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.33 WR=61%
    'ALL_MACD_HIST': ('TRAIL', 1.00, 0.50, 0.50),  # PF=1.28 WR=56%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.43 WR=68%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.55 WR=70%
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.62 WR=66%
    'IDX_ORB15': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.47 WR=27%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.55 WR=70%
    'LON_PREV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.53 WR=79%
    'TOK_FISHER': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.33 WR=78%
}

STRAT_EXITS[('5ers', 'UK100')] = {
    'ALL_CONSEC_REV': ('TPSL', 3.00, 1.00, 0),  # PF=1.73 WR=81%
    'ALL_ENGULF': ('TRAIL', 0.50, 0.75, 0.75),  # PF=1.33 WR=29%
    'ALL_HAMMER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.32 WR=76%
    'IDX_CONSEC_REV': ('TPSL', 3.00, 1.00, 0),  # PF=1.46 WR=79%
    'IDX_ENGULF': ('TRAIL', 0.50, 0.75, 0.75),  # PF=1.33 WR=29%
    'IDX_LATE_REV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.66 WR=77%
    'IDX_ORB15': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.37 WR=73%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.44 WR=72%
    'IDX_VWAP_BOUNCE': ('TPSL', 2.00, 1.50, 0),  # PF=1.33 WR=63%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.39 WR=66%
    'LON_GAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.41 WR=67%
    'LON_PREV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.32 WR=62%
    'NY_HMA_CROSS': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.66 WR=71%
    'TOK_MACD_MED': ('TPSL', 3.00, 3.00, 0),  # PF=1.23 WR=52%
    'TOK_NR4': ('TPSL', 2.50, 0.75, 0),  # PF=1.37 WR=80%
}

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    'ALL_ADX_FAST': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.45 WR=78%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.80 WR=72%
    'ALL_CCI_14_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.54 WR=78%
    'ALL_CMO_14': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.24 WR=64%
    'ALL_CMO_9': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.31 WR=61%
    'ALL_DC10': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.55 WR=70%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.50 WR=69%
    'ALL_DC50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.45 WR=75%
    'ALL_EMA_TREND_PB': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.40 WR=75%
    'ALL_ENGULF': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.35 WR=70%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.56 WR=74%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.68 WR=72%
    'ALL_HMA_DIR': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.32 WR=77%
    'ALL_INSIDE_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.41 WR=78%
    'ALL_MACD_MED_SIG': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.30 WR=72%
    'ALL_MACD_RSI': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.45 WR=68%
    'ALL_MOM_10': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.62 WR=73%
    'ALL_MSTAR': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.93 WR=78%
    'ALL_MTF_BRK': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.29 WR=74%
    'ALL_NR4': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.39 WR=78%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.33 WR=55%
    'ALL_PIVOT_BRK': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.43 WR=77%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.45 WR=78%
    'ALL_WILLR_14': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.50 WR=74%
    'D8': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.86 WR=52%
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.43 WR=72%
    'IDX_ENGULF': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.35 WR=70%
    'IDX_GAP_FILL': ('TRAIL', 1.50, 0.75, 0.50),  # PF=1.43 WR=49%
    'IDX_LATE_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.39 WR=68%
    'IDX_NR4': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.39 WR=78%
    'IDX_NY_MOM': ('TPSL', 2.50, 0.75, 0),  # PF=1.55 WR=81%
    'IDX_ORB30': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.46 WR=68%
    'IDX_PREV_HL': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.70 WR=68%
    'IDX_TREND_DAY': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.51 WR=70%
    'IDX_VWAP_BOUNCE': ('TRAIL', 1.50, 0.50, 0.50),  # PF=2.13 WR=63%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.44 WR=77%
    'LON_GAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.44 WR=78%
    'LON_KZ': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.86 WR=84%
    'LON_PREV': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.36 WR=66%
    'LON_TOKEND': ('TRAIL', 3.00, 0.30, 0.30),  # PF=2.09 WR=77%
    'NY_DAYMOM': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.36 WR=63%
    'NY_GAP': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.50 WR=51%
    'NY_HMA_CROSS': ('TPSL', 2.50, 2.00, 0),  # PF=1.25 WR=56%
    'NY_LONEND': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.36 WR=60%
    'PO3_SWEEP': ('TRAIL', 1.50, 0.75, 0.75),  # PF=2.42 WR=69%
    'TOK_FADE': ('TRAIL', 1.50, 0.50, 0.30),  # PF=1.23 WR=56%
    'TOK_MACD_MED': ('TPSL', 3.00, 2.00, 0),  # PF=1.32 WR=62%
    'TOK_PREVEXT': ('TRAIL', 1.50, 0.75, 0.75),  # PF=1.68 WR=52%
    'TOK_WILLR': ('TPSL', 2.50, 0.25, 0),  # PF=2.34 WR=94%
}

STRAT_EXITS[('ftmo', 'GER40.cash')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.51 WR=79%
    'ALL_ADX_FAST': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.48 WR=75%
    'ALL_BB_SQUEEZE': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.63 WR=69%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.56 WR=73%
    'ALL_CCI_14_ZERO': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.32 WR=72%
    'ALL_CCI_20_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.39 WR=78%
    'ALL_CMO_14': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.70 WR=81%
    'ALL_CMO_14_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=77%
    'ALL_CMO_9': ('TPSL', 2.50, 3.00, 0),  # PF=1.29 WR=53%
    'ALL_CONSEC_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.76 WR=65%
    'ALL_DC10': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.73 WR=76%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.70 WR=76%
    'ALL_DC50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.55 WR=79%
    'ALL_DOJI_REV': ('TRAIL', 1.50, 0.50, 0.30),  # PF=1.31 WR=62%
    'ALL_DPO_14': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.67 WR=79%
    'ALL_EMA_513': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.47 WR=81%
    'ALL_EMA_821': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.28 WR=69%
    'ALL_ENGULF': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.38 WR=61%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.29 WR=71%
    'ALL_FISHER_9': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.79 WR=70%
    'ALL_FVG_BULL': ('TRAIL', 1.50, 0.30, 0.30),  # PF=2.13 WR=70%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.34 WR=76%
    'ALL_INSIDE_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.55 WR=74%
    'ALL_KC_BRK': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.32 WR=65%
    'ALL_MACD_ADX': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.33 WR=72%
    'ALL_MACD_FAST_SIG': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.29 WR=65%
    'ALL_MACD_FAST_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.47 WR=81%
    'ALL_MACD_HIST': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.20 WR=75%
    'ALL_MACD_STD_SIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.34 WR=78%
    'ALL_MOM_10': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.42 WR=71%
    'ALL_MOM_14': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.33 WR=77%
    'ALL_MTF_BRK': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.93 WR=71%
    'ALL_NR4': ('TRAIL', 1.50, 0.75, 0.75),  # PF=1.27 WR=54%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.36 WR=70%
    'ALL_PSAR_EMA': ('TRAIL', 2.00, 0.75, 0.50),  # PF=1.35 WR=54%
    'ALL_RSI_50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.71 WR=81%
    'ALL_RSI_DIV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.71 WR=59%
    'ALL_RSI_EXTREME': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.35 WR=68%
    'ALL_WILLR_14': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.53 WR=61%
    'ALL_WILLR_7': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.41 WR=69%
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.48 WR=76%
    'IDX_CONSEC_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.60 WR=77%
    'IDX_ENGULF': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.38 WR=61%
    'IDX_GAP_FILL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.26 WR=65%
    'IDX_KC_BRK': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.32 WR=65%
    'IDX_NR4': ('TRAIL', 1.50, 0.75, 0.75),  # PF=1.27 WR=54%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.37 WR=63%
    'IDX_RSI_REV': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.35 WR=68%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.38 WR=61%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.30 WR=50%
    'LON_GAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.27 WR=53%
    'TOK_BIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.78 WR=75%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.49 WR=71%
    'TOK_FISHER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.40 WR=72%
    'TOK_PREVEXT': ('TRAIL', 1.50, 1.00, 0.30),  # PF=1.38 WR=53%
    'TOK_WILLR': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.43 WR=70%
}

STRAT_EXITS[('ftmo', 'UK100.cash')] = {
    'ALL_CONSEC_REV': ('TPSL', 3.00, 1.00, 0),  # PF=1.64 WR=81%
    'ALL_FIB_618': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.39 WR=70%
    'ALL_MACD_HIST': ('TPSL', 2.50, 0.75, 0),  # PF=1.50 WR=81%
    'ALL_MSTAR': ('TPSL', 2.00, 2.00, 0),  # PF=1.31 WR=54%
    'ALL_RSI_EXTREME': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.30 WR=71%
    'IDX_CONSEC_REV': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.56 WR=76%
    'IDX_GAP_CONT': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.27 WR=61%
    'IDX_RSI_REV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.30 WR=71%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.43 WR=71%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.41 WR=66%
    'LON_GAP': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.47 WR=64%
    'LON_PREV': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.36 WR=61%
    'NY_HMA_CROSS': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.54 WR=70%
    'TOK_NR4': ('TPSL', 2.50, 0.75, 0),  # PF=1.35 WR=81%
}

STRAT_EXITS[('ftmo', 'US100.cash')] = {
    'ALL_DPO_14': ('TRAIL', 2.00, 0.30, 0.50),  # PF=1.27 WR=60%
    'ALL_EMA_821': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.53 WR=82%
    'ALL_EMA_921': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.34 WR=80%
    'ALL_FIB_618': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.33 WR=67%
    'ALL_FVG_BULL': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.49 WR=77%
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.38 WR=70%
    'ALL_MTF_BRK': ('TPSL', 2.00, 0.25, 0),  # PF=1.70 WR=91%
    'ALL_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.35 WR=63%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 3.00, 0.30, 0.50),  # PF=1.33 WR=67%
    'ALL_PIVOT_BRK': ('TRAIL', 1.00, 0.75, 0.75),  # PF=1.31 WR=44%
    'ALL_RSI_50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.59 WR=80%
    'ALL_WILLR_14': ('TPSL', 2.00, 0.50, 0),  # PF=1.42 WR=82%
    'ALL_WILLR_7': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.27 WR=68%
    'D8': ('TRAIL', 1.50, 0.50, 0.30),  # PF=2.03 WR=62%
    'IDX_3SOLDIERS': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.47 WR=75%
    'IDX_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.35 WR=63%
    'IDX_NY_MOM': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.23 WR=61%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.36 WR=66%
    'LON_BIGGAP': ('TRAIL', 3.00, 1.00, 0.30),  # PF=1.34 WR=69%
    'LON_PIN': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.32 WR=68%
    'LON_PREV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.31 WR=76%
    'NY_GAP': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.60 WR=15%
    'TOK_MACD_MED': ('TPSL', 2.50, 0.75, 0),  # PF=1.34 WR=80%
    'TOK_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.48 WR=64%
    'TOK_PREVEXT': ('TPSL', 3.00, 1.50, 0),  # PF=1.49 WR=74%
    'TOK_WILLR': ('TPSL', 2.00, 0.50, 0),  # PF=1.45 WR=83%
}

STRAT_EXITS[('ftmo', 'US500.cash')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.42 WR=81%
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.35 WR=79%
    'ALL_DC50': ('TPSL', 3.00, 0.50, 0),  # PF=1.89 WR=91%
    'ALL_DOJI_REV': ('TPSL', 2.50, 0.25, 0),  # PF=1.91 WR=93%
    'ALL_FIB_618': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.53 WR=70%
    'ALL_FVG_BULL': ('TPSL', 3.00, 0.50, 0),  # PF=1.53 WR=88%
    'ALL_ICHI_TK': ('TPSL', 3.00, 0.50, 0),  # PF=1.64 WR=90%
    'ALL_MACD_FAST_SIG': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.37 WR=62%
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.27 WR=65%
    'ALL_RSI_50': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.47 WR=68%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.61 WR=71%
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 0.50, 0.30),  # PF=1.56 WR=68%
    'IDX_GAP_FILL': ('TRAIL', 3.00, 1.00, 0.30),  # PF=1.25 WR=59%
    'IDX_ORB15': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.48 WR=27%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.61 WR=71%
    'LON_PIN': ('TRAIL', 3.00, 0.30, 1.00),  # PF=1.25 WR=52%
    'LON_PREV': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.61 WR=78%
    'TOK_FISHER': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.46 WR=71%
    'TOK_PREVEXT': ('TPSL', 1.50, 3.00, 0),  # PF=1.34 WR=32%
}

STRAT_EXITS[('ftmo', 'US30.cash')] = {
    'ALL_DC50': ('TRAIL', 3.00, 1.00, 0.30),  # PF=1.30 WR=69%
    'ALL_FIB_618': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.51 WR=70%
    'ALL_MACD_HIST': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.41 WR=78%
    'ALL_MSTAR': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.31 WR=65%
    'ALL_NR4': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.31 WR=63%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.35 WR=79%
    'ALL_RSI_DIV': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.26 WR=44%
    'ALL_WILLR_7': ('TPSL', 1.00, 2.00, 0),  # PF=1.26 WR=37%
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.54 WR=76%
    'IDX_NR4': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.31 WR=63%
    'IDX_ORB30': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.31 WR=62%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.81 WR=65%
    'IDX_TREND_DAY': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.37 WR=65%
    'IDX_VWAP_BOUNCE': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.34 WR=60%
    'LON_DC10': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.29 WR=65%
    'LON_DC10_MOM': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.29 WR=65%
    'LON_PREV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.36 WR=47%
    'NY_DAYMOM': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.47 WR=50%
    'NY_LONEND': ('TRAIL', 0.50, 0.30, 1.00),  # PF=1.69 WR=17%
    'TOK_2BAR': ('TPSL', 3.00, 0.50, 0),  # PF=1.58 WR=89%
    'TOK_FADE': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.29 WR=31%
    'TOK_FISHER': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.27 WR=59%
    'TOK_PREVEXT': ('TPSL', 1.00, 3.00, 0),  # PF=1.35 WR=26%
}
