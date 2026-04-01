# Exit configs par (broker, instrument, strat) - regenere depuis pkl 2026-04-01.
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

STRAT_EXITS[('5ers', 'XAUUSD')] = {
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.61 WR=71%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.63 WR=75%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.57 WR=79%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.63 WR=69%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.54 WR=79%
    'ALL_PIVOT_BOUNCE': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.41 WR=67%
    'ALL_PIVOT_BRK': ('TRAIL', 3.00, 0.30, 0.30),  # PF=2.02 WR=83%
    'ALL_STOCH_OB': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.66 WR=76%
    'D8': ('TPSL', 1.00, 2.00, 0),  # PF=1.79 WR=50%
    'IDX_VWAP_BOUNCE': ('TRAIL', 1.50, 0.50, 0.50),  # PF=2.12 WR=65%
    'LON_KZ': ('TPSL', 3.00, 0.75, 0),  # PF=1.84 WR=86%
    'LON_TOKEND': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.66 WR=72%
    'NY_GAP': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.39 WR=51%
    'PO3_SWEEP': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.84 WR=73%
    'TOK_FISHER': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.45 WR=58%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.68 WR=62%
    'TOK_STOCH': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.58 WR=75%
}

STRAT_EXITS[('5ers', 'JPN225')] = {
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.94 WR=83%
    'ALL_NR4': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.56 WR=77%
    'ALL_WILLR_14': ('TRAIL', 2.00, 0.75, 0.30),  # PF=1.50 WR=61%
    'D8': ('TRAIL', 3.00, 0.75, 1.00),  # PF=1.83 WR=63%
    'IDX_NR4': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.56 WR=77%
    'LON_DC10': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.53 WR=74%
    'LON_DC10_MOM': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.53 WR=74%
    'TOK_NR4': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.58 WR=79%
}

STRAT_EXITS[('5ers', 'DAX40')] = {
    'ALL_CMO_9': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.44 WR=42%
    'ALL_CONSEC_REV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.57 WR=57%
    'ALL_DC10': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.51 WR=74%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.50 WR=74%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.90 WR=74%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.82 WR=77%
    'ALL_FISHER_9': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.70 WR=75%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.94 WR=82%
    'ALL_KB_SQUEEZE': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.63 WR=60%
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.30, 0.30),  # PF=2.01 WR=68%
    'ALL_MSTAR': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.50 WR=46%
    'ALL_MTF_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.60 WR=75%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.44 WR=60%
    'ALL_STOCH_OB': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.57 WR=42%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.51 WR=68%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.44 WR=60%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.52 WR=64%
    'LON_STOCH': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.44 WR=67%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.63 WR=71%
    'TOK_FISHER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.91 WR=68%
    'TOK_WILLR': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.50 WR=62%
}

STRAT_EXITS[('5ers', 'NAS100')] = {
    'ALL_ADX_RSI50': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.56 WR=74%
    'ALL_PSAR_EMA': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.61 WR=59%
    'ALL_RSI_50': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.56 WR=74%
    'ALL_SUPERTREND': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.68 WR=60%
    'D8': ('TRAIL', 1.50, 0.50, 0.30),  # PF=2.02 WR=62%
    'LON_STOCH': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.57 WR=63%
    'TOK_NR4': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.46 WR=64%
}

STRAT_EXITS[('5ers', 'SP500')] = {
    'ALL_LR_BREAK': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.46 WR=60%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.47 WR=68%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.57 WR=71%
    'ALL_SUPERTREND': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.44 WR=68%
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.65 WR=67%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.57 WR=71%
    'LON_PREV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.55 WR=79%
}

STRAT_EXITS[('5ers', 'UK100')] = {
    'ALL_CONSEC_REV': ('TPSL', 3.00, 1.00, 0),  # PF=1.66 WR=81%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.55 WR=79%
    'IDX_LATE_REV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.62 WR=76%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.41 WR=66%
    'LON_GAP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.44 WR=67%
    'NY_HMA_CROSS': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.66 WR=71%
}

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.83 WR=72%
    'ALL_CCI_14_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.56 WR=78%
    'ALL_DC10': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.50 WR=69%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.46 WR=69%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.62 WR=74%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.62 WR=74%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.64 WR=72%
    'ALL_KB_SQUEEZE': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.96 WR=77%
    'ALL_MACD_RSI': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.56 WR=65%
    'ALL_MOM_10': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.54 WR=73%
    'ALL_MSTAR': ('TRAIL', 2.00, 0.50, 0.30),  # PF=2.05 WR=78%
    'ALL_PIVOT_BRK': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.51 WR=77%
    'ALL_ROC_ZERO': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.54 WR=73%
    'ALL_STOCH_OB': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.77 WR=77%
    'ALL_WILLR_14': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.61 WR=75%
    'D8': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.90 WR=53%
    'IDX_GAP_FILL': ('TRAIL', 1.50, 0.75, 0.50),  # PF=1.43 WR=50%
    'IDX_NY_MOM': ('TPSL', 2.50, 0.75, 0),  # PF=1.60 WR=81%
    'IDX_ORB30': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.47 WR=68%
    'IDX_PREV_HL': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.66 WR=68%
    'IDX_VWAP_BOUNCE': ('TRAIL', 1.50, 0.50, 0.50),  # PF=2.12 WR=63%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.55 WR=73%
    'LON_KZ': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.89 WR=85%
    'LON_TOKEND': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.99 WR=78%
    'NY_GAP': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.52 WR=51%
    'PO3_SWEEP': ('TRAIL', 1.50, 0.75, 0.75),  # PF=2.25 WR=69%
    'TOK_PREVEXT': ('TRAIL', 1.50, 0.75, 0.75),  # PF=1.95 WR=55%
    'TOK_STOCH': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.58 WR=74%
    'TOK_TRIX': ('TRAIL', 1.50, 0.75, 0.75),  # PF=1.39 WR=53%
}

STRAT_EXITS[('ftmo', 'GER40.cash')] = {
    'ALL_ADX_RSI50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.79 WR=82%
    'ALL_AROON_CROSS': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.45 WR=70%
    'ALL_BB_SQUEEZE': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.64 WR=69%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.50 WR=73%
    'ALL_CMO_14': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.61 WR=80%
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.54 WR=76%
    'ALL_DC10': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.63 WR=73%
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.54 WR=75%
    'ALL_DPO_14': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.73 WR=79%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=2.04 WR=78%
    'ALL_ENGULF': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.47 WR=62%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.47 WR=68%
    'ALL_FISHER_9': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.80 WR=70%
    'ALL_FVG_BULL': ('TRAIL', 1.50, 0.30, 0.30),  # PF=2.09 WR=70%
    'ALL_INSIDE_BRK': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.54 WR=74%
    'ALL_KB_SQUEEZE': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.45 WR=56%
    'ALL_MACD_HIST': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.24 WR=75%
    'ALL_MTF_BRK': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.87 WR=71%
    'ALL_RSI_50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.78 WR=81%
    'ALL_RSI_DIV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.65 WR=59%
    'ALL_STOCH_RSI': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.70 WR=38%
    'ALL_WILLR_14': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.53 WR=61%
    'ALL_WILLR_7': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.48 WR=69%
    'IDX_CONSEC_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.67 WR=77%
    'IDX_ENGULF': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.47 WR=62%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.40 WR=61%
    'TOK_BIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.67 WR=74%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.56 WR=71%
    'TOK_FISHER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.54 WR=72%
    'TOK_WILLR': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.44 WR=70%
}

STRAT_EXITS[('ftmo', 'UK100.cash')] = {
    'ALL_MSTAR': ('TPSL', 2.00, 2.00, 0),  # PF=1.38 WR=55%
    'ALL_RSI_DIV': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.50 WR=71%
    'IDX_LATE_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.50 WR=69%
    'LON_GAP': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.47 WR=65%
    'NY_HMA_CROSS': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.58 WR=70%
}

STRAT_EXITS[('ftmo', 'US500.cash')] = {
    'ALL_CONSEC_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.43 WR=67%
    'ALL_ELDER_BULL': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.50 WR=75%
    'ALL_KB_SQUEEZE': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.62 WR=63%
    'ALL_LR_BREAK': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.51 WR=60%
    'ALL_MACD_FAST_SIG': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.41 WR=62%
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.56 WR=70%
    'ALL_SUPERTREND': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.53 WR=70%
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.45 WR=71%
    'LON_PREV': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.55 WR=77%
    'TOK_FISHER': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.51 WR=71%
}

