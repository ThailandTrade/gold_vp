# Exit configs par (broker, instrument, strat) - regenere 2026-04-06 (pipeline unifie).
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

STRAT_EXITS[('5ers', 'XAUUSD')] = {
    'ALL_AROON_CROSS': ('TRAIL', 3.00, 0.75, 1.00),  # PF=1.46 WR=60%
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.73 WR=71%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.51 WR=75%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.54 WR=78%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.60 WR=69%
    'ALL_PIVOT_BRK': ('TPSL', 3.00, 0.75, 0.00),  # PF=1.82 WR=87%
    'D8': ('TPSL', 1.00, 2.00, 0.00),  # PF=1.79 WR=50%
    'IDX_ORB30': ('TRAIL', 3.00, 0.50, 1.00),  # PF=1.57 WR=58%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.59 WR=73%
    'IDX_VWAP_BOUNCE': ('TRAIL', 1.50, 0.50, 0.50),  # PF=2.11 WR=65%
    'LON_KZ': ('TPSL', 3.00, 0.75, 0.00),  # PF=1.95 WR=87%
    'LON_TOKEND': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.61 WR=73%
    'NY_GAP': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.44 WR=52%
    'PO3_SWEEP': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.83 WR=73%
    'TOK_FISHER': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.38 WR=57%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.92 WR=64%
    'TOK_STOCH': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.53 WR=75%
    'TOK_WILLR': ('TPSL', 1.50, 0.50, 0.00),  # PF=1.54 WR=77%
}

STRAT_EXITS[('5ers', 'JPN225')] = {
    'ALL_NR4': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.71 WR=78%
    'ALL_STOCH_PIVOT': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.71 WR=79%
    'IDX_NR4': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.71 WR=78%
    'LON_BIGGAP': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.45 WR=68%
    'TOK_NR4': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.71 WR=79%
}

STRAT_EXITS[('5ers', 'DAX40')] = {
    'ALL_CCI_20_ZERO': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.66 WR=82%
    'ALL_CONSEC_REV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.58 WR=57%
    'ALL_DOJI_REV': ('TRAIL', 1.50, 0.50, 0.30),  # PF=1.54 WR=64%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.71 WR=76%
    'ALL_ENGULF': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.68 WR=80%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.75 WR=77%
    'ALL_FISHER_9': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.86 WR=75%
    'ALL_KB_SQUEEZE': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.72 WR=60%
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.30, 0.30),  # PF=2.05 WR=68%
    'ALL_MSTAR': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.61 WR=47%
    'ALL_RSI_DIV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.58 WR=57%
    'ALL_STOCH_OB': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.72 WR=43%
    'ALL_WILLR_14': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.55 WR=62%
    'ALL_WILLR_7': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.49 WR=75%
    'IDX_BB_REV': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.49 WR=73%
    'IDX_ENGULF': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.68 WR=80%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.68 WR=68%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.58 WR=65%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.49 WR=71%
    'TOK_FISHER': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.95 WR=75%
    'TOK_STOCH': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.56 WR=74%
    'TOK_WILLR': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.59 WR=62%
}

STRAT_EXITS[('5ers', 'NAS100')] = {
    'ALL_ADX_RSI50': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.56 WR=74%
    'ALL_CCI_100': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.40 WR=60%
    'ALL_DOJI_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.47 WR=69%
    'ALL_RSI_50': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.56 WR=74%
    'ALL_STOCH_RSI': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.43 WR=62%
    'ALL_WILLR_7': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.48 WR=69%
    'D8': ('TRAIL', 1.50, 0.50, 0.30),  # PF=2.02 WR=62%
    'LON_STOCH': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.47 WR=62%
    'TOK_PREVEXT': ('TPSL', 3.00, 1.50, 0.00),  # PF=1.75 WR=75%
}

STRAT_EXITS[('5ers', 'SP500')] = {
    'ALL_ENGULF': ('TRAIL', 1.50, 0.50, 0.30),  # PF=1.46 WR=66%
    'ALL_HAMMER': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.56 WR=59%
    'ALL_LR_BREAK': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.45 WR=60%
    'ALL_MACD_FAST_SIG': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.75 WR=62%
    'ALL_MACD_HIST': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.47 WR=72%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.53 WR=71%
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.78 WR=67%
    'IDX_ENGULF': ('TRAIL', 1.50, 0.50, 0.30),  # PF=1.46 WR=66%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.53 WR=71%
    'TOK_FISHER': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.80 WR=61%
}

STRAT_EXITS[('5ers', 'UK100')] = {
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.76 WR=81%
    'ALL_MACD_DIV': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.74 WR=74%
    'ALL_MACD_HIST': ('TPSL', 3.00, 0.50, 0.00),  # PF=2.03 WR=90%
    'IDX_LATE_REV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.52 WR=76%
    'LON_GAP': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.43 WR=64%
    'LON_PREV': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.39 WR=61%
}

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.88 WR=72%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.59 WR=75%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.59 WR=74%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.51 WR=72%
    'ALL_KB_SQUEEZE': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.93 WR=77%
    'ALL_MACD_RSI': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.53 WR=65%
    'ALL_MOM_10': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.46 WR=73%
    'ALL_MSTAR': ('TRAIL', 2.00, 0.50, 0.30),  # PF=2.12 WR=77%
    'ALL_ROC_ZERO': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.46 WR=73%
    'ALL_STOCH_OB': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.75 WR=77%
    'ALL_WILLR_14': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.51 WR=74%
    'D8': ('TRAIL', 1.00, 1.00, 0.75),  # PF=1.72 WR=52%
    'IDX_GAP_FILL': ('TRAIL', 1.50, 0.75, 0.50),  # PF=1.42 WR=50%
    'IDX_ORB30': ('TRAIL', 3.00, 0.75, 1.00),  # PF=1.42 WR=61%
    'IDX_PREV_HL': ('TRAIL', 3.00, 1.00, 0.50),  # PF=1.73 WR=68%
    'IDX_VWAP_BOUNCE': ('TRAIL', 1.50, 0.50, 0.50),  # PF=2.13 WR=63%
    'LON_BIGGAP': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.50 WR=73%
    'LON_KZ': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.97 WR=85%
    'LON_TOKEND': ('TRAIL', 3.00, 0.30, 0.30),  # PF=2.07 WR=78%
    'NY_GAP': ('TRAIL', 1.50, 0.50, 0.50),  # PF=1.55 WR=51%
    'NY_LONMOM': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.43 WR=38%
    'PO3_SWEEP': ('TRAIL', 1.50, 0.75, 0.75),  # PF=2.23 WR=69%
    'TOK_FADE': ('TRAIL', 0.50, 0.30, 0.30),  # PF=1.85 WR=37%
    'TOK_PREVEXT': ('TRAIL', 1.50, 0.75, 0.75),  # PF=2.06 WR=56%
    'TOK_STOCH': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.58 WR=75%
    'TOK_WILLR': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.74 WR=77%
}

STRAT_EXITS[('ftmo', 'GER40.cash')] = {
    'ALL_ADX_RSI50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.79 WR=81%
    'ALL_BB_SQUEEZE': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.56 WR=68%
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.90 WR=77%
    'ALL_ENGULF': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.66 WR=62%
    'ALL_FIB_618': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.42 WR=68%
    'ALL_FISHER_9': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.03 WR=71%
    'ALL_FVG_BULL': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.76 WR=69%
    'ALL_MACD_DIV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.86 WR=60%
    'ALL_MACD_FAST_SIG': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.46 WR=65%
    'ALL_MACD_HIST': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.71 WR=75%
    'ALL_MTF_BRK': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.49 WR=69%
    'ALL_PSAR_EMA': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.46 WR=65%
    'ALL_RSI_DIV': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.95 WR=59%
    'ALL_STOCH_CROSS': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.47 WR=61%
    'ALL_STOCH_RSI': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.44 WR=66%
    'ALL_WILLR_14': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.65 WR=62%
    'ALL_WILLR_7': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.59 WR=77%
    'IDX_ENGULF': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.66 WR=62%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.61 WR=65%
    'IDX_TREND_DAY': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.46 WR=61%
    'TOK_BIG': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.59 WR=74%
    'TOK_FISHER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.41 WR=72%
    'TOK_STOCH': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.49 WR=72%
    'TOK_WILLR': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.59 WR=70%
}

STRAT_EXITS[('ftmo', 'US500.cash')] = {
    'ALL_ELDER_BULL': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.64 WR=74%
    'ALL_FISHER_9': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.42 WR=67%
    'ALL_LR_BREAK': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.47 WR=60%
    'ALL_MACD_FAST_SIG': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.44 WR=62%
    'ALL_RSI_EXTREME': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.56 WR=72%
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.53 WR=72%
    'IDX_RSI_REV': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.56 WR=72%
    'TOK_FISHER': ('TRAIL', 1.00, 0.50, 0.50),  # PF=1.94 WR=59%
}

STRAT_EXITS[('ftmo', 'US100.cash')] = {
    'ALL_ADX_RSI50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.65 WR=81%
    'ALL_CCI_100': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.39 WR=59%
    'ALL_HMA_CROSS': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.49 WR=75%
    'ALL_RSI_50': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.62 WR=81%
    'ALL_STOCH_RSI': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.47 WR=63%
    'ALL_WILLR_7': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.51 WR=69%
    'D8': ('TRAIL', 1.50, 0.50, 0.30),  # PF=2.03 WR=62%
    'LON_STOCH': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.43 WR=62%
    'TOK_PREVEXT': ('TPSL', 3.00, 1.50, 0.00),  # PF=1.74 WR=75%
}

STRAT_EXITS[('ftmo', 'US30.cash')] = {
    'ALL_EMA_TREND_PB': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.42 WR=61%
    'ALL_FIB_618': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.57 WR=70%
    'ALL_MACD_HIST': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.73 WR=79%
    'ALL_MSTAR': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.54 WR=65%
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.65 WR=65%
    'IDX_VWAP_BOUNCE': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.66 WR=61%
    'NY_LONEND': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.68 WR=46%
    'NY_LONMOM': ('TRAIL', 1.00, 1.00, 0.50),  # PF=1.68 WR=28%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.45 WR=72%
}

STRAT_EXITS[('ftmo', 'JP225.cash')] = {
    'ALL_FIB_618': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.84 WR=70%
    'ALL_FISHER_9': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.42 WR=60%
    'ALL_NR4': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.63 WR=77%
    'ALL_WILLR_7': ('TRAIL', 2.00, 0.75, 0.30),  # PF=1.58 WR=63%
    'IDX_LATE_REV': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.62 WR=77%
    'IDX_NR4': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.63 WR=77%
    'LON_BIGGAP': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.54 WR=73%
    'LON_GAP': ('TRAIL', 2.00, 0.75, 0.75),  # PF=1.53 WR=70%
    'LON_TOKEND': ('TRAIL', 2.00, 1.00, 1.00),  # PF=1.82 WR=62%
    'TOK_NR4': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.76 WR=79%
}

STRAT_EXITS[('crypto', 'BNBUSD')] = {
    'ALL_CMO_9': ('TRAIL', 2.00, 0.30, 0.30),  # PF=2.03 WR=77%
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.63 WR=76%
    'ALL_MACD_FAST_SIG': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.58 WR=71%
    'ALL_MACD_RSI': ('TRAIL', 3.00, 1.00, 0.75),  # PF=1.44 WR=66%
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.57 WR=80%
    'IDX_BB_REV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.51 WR=71%
    'LON_ASIAN_BRK': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.55 WR=72%
    'LON_STOCH': ('TRAIL', 1.00, 0.50, 0.30),  # PF=1.44 WR=56%
    'NY_HMA_CROSS': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.72 WR=68%
    'TOK_2BAR': ('TRAIL', 3.00, 0.50, 0.30),  # PF=1.66 WR=77%
    'TOK_NR4': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.47 WR=73%
    'TOK_PREVEXT': ('TRAIL', 1.50, 0.30, 0.50),  # PF=2.47 WR=55%
}

STRAT_EXITS[('crypto', 'BTCUSD')] = {
    'ALL_AO_SAUCER': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.65 WR=81%
    'D8': ('TRAIL', 1.50, 0.50, 0.30),  # PF=2.33 WR=68%
    'PO3_SWEEP': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.91 WR=86%
    'TOK_PREVEXT': ('TRAIL', 3.00, 0.75, 0.30),  # PF=1.47 WR=65%
}

STRAT_EXITS[('crypto', 'ETHUSD')] = {
    'ALL_ENGULF': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.67 WR=75%
    'D8': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.92 WR=79%
    'IDX_ENGULF': ('TRAIL', 3.00, 0.75, 0.75),  # PF=1.67 WR=75%
    'TOK_FADE': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.70 WR=83%
}

STRAT_EXITS[('crypto', 'BCHUSD')] = {
    'ALL_CCI_100': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.44 WR=58%
    'ALL_CMO_14_ZERO': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.39 WR=57%
    'ALL_MOM_14': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.39 WR=57%
    'LON_ASIAN_BRK': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.44 WR=64%
    'TOK_PREVEXT': ('TRAIL', 2.00, 0.50, 0.30),  # PF=2.02 WR=68%
}

STRAT_EXITS[('crypto', 'AVAUSD')] = {
    'ALL_DOJI_REV': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.47 WR=68%
    'ALL_MACD_HIST': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.68 WR=76%
    'D8': ('TPSL', 2.50, 0.50, 0.00),  # PF=1.85 WR=87%
    'IDX_GAP_FILL': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.39 WR=60%
}

STRAT_EXITS[('crypto', 'NEOUSD')] = {
    'ALL_HAMMER': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.60 WR=71%
    'ALL_MACD_DIV': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.53 WR=70%
    'ALL_RSI_DIV': ('TRAIL', 2.00, 0.50, 0.50),  # PF=1.52 WR=67%
    'D8': ('TPSL', 2.50, 0.25, 0.00),  # PF=8.37 WR=97%
    'IDX_GAP_FILL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.56 WR=74%
    'LON_ASIAN_BRK': ('TRAIL', 1.00, 0.30, 0.30),  # PF=1.63 WR=54%
    'NY_HMA_CROSS': ('TRAIL', 3.00, 1.00, 1.00),  # PF=1.44 WR=64%
    'TOK_2BAR': ('TRAIL', 3.00, 0.75, 0.50),  # PF=1.43 WR=70%
    'TOK_WILLR': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.59 WR=63%
}

STRAT_EXITS[('crypto', 'DOGEUSD')] = {
    'ALL_AO_SAUCER': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.80 WR=78%
    'ALL_ELDER_BEAR': ('TRAIL', 2.00, 0.30, 0.30),  # PF=1.62 WR=75%
    'ALL_FIB_618': ('TRAIL', 2.00, 0.50, 0.30),  # PF=1.59 WR=66%
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.53 WR=77%
}

STRAT_EXITS[('crypto', 'DOTUSD')] = {
    'ALL_MACD_HIST': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.58 WR=80%
    'ALL_STOCH_RSI': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.59 WR=80%
    'D8': ('TPSL', 2.00, 0.50, 0.00),  # PF=3.09 WR=89%
    'TOK_FADE': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.57 WR=78%
}

STRAT_EXITS[('crypto', 'ADAUSD')] = {
    'ALL_RSI_DIV': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.61 WR=80%
    'D8': ('TRAIL', 2.00, 0.75, 0.50),  # PF=3.99 WR=71%
    'TOK_PREVEXT': ('TRAIL', 1.50, 0.30, 0.30),  # PF=1.46 WR=60%
}

STRAT_EXITS[('crypto', 'AAVEUSD')] = {
    'D8': ('TRAIL', 1.50, 1.00, 0.50),  # PF=1.57 WR=60%
    'IDX_NY_MOM': ('TRAIL', 3.00, 0.50, 0.50),  # PF=1.57 WR=76%
    'TOK_FADE': ('TRAIL', 3.00, 0.30, 0.30),  # PF=1.66 WR=80%
}

