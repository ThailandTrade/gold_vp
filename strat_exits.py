# Exit configs multi-TF — cle: (broker, sym, tf)
# 15m — regenere 2026-04-09 (sim_exit_custom unifie, margin 5%)
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

# 5ers 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)

STRAT_EXITS[('5ers', 'XAUUSD', '15m')] = {
    'IDX_TREND_DAY': ('TPSL', 3.00, 4.00, 0.00),
    'ALL_BB_TIGHT': ('TPSL', 2.50, 2.50, 0.00),
}

STRAT_EXITS[('5ers', 'DAX40', '15m')] = {
    'ALL_MOM_10': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_FIB_618': ('TPSL', 2.50, 2.50, 0.00),
    'ALL_ELDER_BULL': ('TPSL', 3.00, 1.00, 0.00),
}

STRAT_EXITS[('5ers', 'SP500', '15m')] = {
    'TOK_TRIX': ('BE_TP', 2.00, 0.50, 0.75),
    'ALL_MACD_STD_SIG': ('TPSL', 2.50, 2.50, 0.00),
    'ALL_PIVOT_BOUNCE': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_MACD_ADX': ('TPSL', 2.50, 3.00, 0.00),
    'ALL_MTF_BRK': ('TPSL', 1.00, 0.75, 0.00),
    'ALL_TRIX': ('TPSL', 2.00, 0.75, 0.00),
    'TOK_2BAR': ('TPSL', 2.50, 0.75, 0.00),
}

STRAT_EXITS[('5ers', 'NAS100', '15m')] = {
    'ALL_AROON_CROSS': ('BE_TP', 3.00, 0.75, 1.00),
    'ALL_LR_BREAK': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_MSTAR': ('TPSL', 2.50, 0.75, 0.00),
    'TOK_2BAR': ('TPSL', 2.50, 0.50, 0.00),
}

STRAT_EXITS[('5ers', 'US30', '15m')] = {
    'ALL_ADX_FAST': ('TRAIL', 3.00, 0.50, 0.30),
    'TOK_NR4': ('TPSL', 1.00, 1.50, 0.00),
    'TOK_TRIX': ('TPSL', 1.20, 0.75, 0.00),
}

STRAT_EXITS[('5ers', 'UK100', '15m')] = {
    'TOK_TRIX': ('TPSL', 3.00, 1.00, 0.00),
}

STRAT_EXITS[('5ers', 'JPN225', '15m')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_FVG_BULL': ('TPSL', 3.00, 2.50, 0.00),
    'TOK_BIG': ('TPSL', 3.00, 3.00, 0.00),
}

STRAT_EXITS[('5ers', 'XAGUSD', '15m')] = {
    'ALL_KC_BRK': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_FVG_BULL': ('TPSL', 3.00, 1.50, 0.00),
    'TOK_STOCH': ('BE_TP', 2.50, 0.50, 0.75),
    'ALL_STOCH_OB': ('BE_TP', 2.50, 0.50, 0.75),
}

# FTMO 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)
# Cost-r 0.05R applique au COMBO uniquement. Strats selectionnees sans cost individuel.
# 8 instruments, 68 strats. Tous les strats passant les filtres robustesse sont gardes.

STRAT_EXITS[('ftmo', 'XAUUSD', '15m')] = {
    'IDX_TREND_DAY': ('TPSL', 3.00, 5.00, 0.00),
    'ALL_KC_BRK': ('TPSL', 3.00, 1.50, 0.00),
    'BOS_FVG': ('TPSL', 2.50, 2.00, 0.00),
    'ALL_MACD_RSI': ('TRAIL', 2.00, 0.50, 0.30),
    'ALL_INSIDE_BRK': ('TRAIL', 3.00, 0.30, 0.30),
}

STRAT_EXITS[('ftmo', 'GER40.cash', '15m')] = {
    'TOK_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_CCI_100': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_ELDER_BULL': ('TPSL', 3.00, 0.75, 0.00),
}

STRAT_EXITS[('ftmo', 'US500.cash', '15m')] = {
    'TOK_2BAR': ('TPSL', 2.50, 0.75, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_PIVOT_BOUNCE': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_ENGULF': ('TPSL', 1.50, 1.00, 0.00),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_TRIX': ('TRAIL', 2.00, 0.30, 0.30),
    'TOK_TRIX': ('BE_TP', 2.00, 0.50, 0.75),
    'ALL_AROON_CROSS': ('TPSL', 2.00, 0.75, 0.00),
    'LON_STOCH': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_EMA_921': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_3SOLDIERS': ('TPSL', 2.00, 2.00, 0.00),
    'ALL_MACD_ADX': ('TPSL', 3.00, 3.00, 0.00),
}

STRAT_EXITS[('ftmo', 'US100.cash', '15m')] = {
    'ALL_AROON_CROSS': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_LR_BREAK': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_MACD_RSI': ('TPSL', 3.00, 2.50, 0.00),
    'ALL_MSTAR': ('TPSL', 2.50, 0.75, 0.00),
    'TOK_2BAR': ('TPSL', 2.50, 1.00, 0.00),
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_FVG_BULL': ('TPSL', 3.00, 0.50, 0.00),
    'ALL_MACD_ADX': ('TPSL', 2.50, 3.00, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_NR4': ('TPSL', 2.00, 1.50, 0.00),
    'TOK_NR4': ('TPSL', 2.00, 2.50, 0.00),
}

STRAT_EXITS[('ftmo', 'US30.cash', '15m')] = {
    'ALL_MSTAR': ('TPSL', 3.00, 0.25, 0.00),
    'TOK_TRIX': ('TPSL', 1.20, 0.75, 0.00),
    'TOK_NR4': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_MOM_10': ('TPSL', 2.50, 1.50, 0.00),
    'ALL_NR4': ('BE_TP', 2.00, 0.75, 1.00),
    'ALL_ADX_FAST': ('BE_TP', 3.00, 0.75, 1.00),
}

STRAT_EXITS[('ftmo', 'AUS200.cash', '15m')] = {
    'ALL_CMO_14': ('TPSL', 2.50, 1.50, 0.00),
    'ALL_WILLR_14': ('TPSL', 2.50, 1.50, 0.00),
    'ALL_CCI_20_ZERO': ('TPSL', 2.50, 1.50, 0.00),
    'ALL_CONSEC_REV': ('TPSL', 1.50, 1.00, 0.00),
    'ALL_STOCH_OB': ('TRAIL', 3.00, 0.30, 0.30),
    'TOK_WILLR': ('TPSL', 2.50, 1.50, 0.00),
    'ALL_MOM_10': ('TPSL', 2.00, 1.50, 0.00),
    'ALL_CCI_100': ('TPSL', 3.00, 0.50, 0.00),
    'NY_HMA_CROSS': ('TPSL', 3.00, 0.25, 0.00),
    'ALL_RSI_DIV': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_MACD_DIV': ('TRAIL', 2.00, 0.30, 0.30),
    'IDX_3SOLDIERS': ('TRAIL', 1.50, 0.50, 0.30),
    'IDX_BB_REV': ('TPSL', 2.50, 0.75, 0.00),
    'ALL_PIVOT_BRK': ('TPSL', 3.00, 0.25, 0.00),
    'ALL_MACD_HIST': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_CCI_14_ZERO': ('TPSL', 2.00, 2.00, 0.00),
    'ALL_FVG_BULL': ('BE_TP', 2.50, 0.50, 0.75),
    'ALL_HMA_CROSS': ('TPSL', 1.50, 1.50, 0.00),
    'TOK_BIG': ('TPSL', 2.50, 0.75, 0.00),
}

STRAT_EXITS[('ftmo', 'UK100.cash', '15m')] = {
    'ALL_HAMMER': ('TRAIL', 3.00, 0.50, 0.30),
    'TOK_TRIX': ('TPSL', 2.50, 0.50, 0.00),
    'ALL_LR_BREAK': ('BE_TP', 2.50, 0.75, 1.00),
    'ALL_TRIX': ('TPSL', 2.50, 0.75, 0.00),
    'LON_ASIAN_BRK': ('TPSL', 3.00, 0.25, 0.00),
}

STRAT_EXITS[('ftmo', 'XAGUSD', '15m')] = {
    'ALL_NR4': ('TRAIL', 2.00, 0.30, 0.30),
    'TOK_NR4': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_AROON_CROSS': ('TRAIL', 3.00, 0.50, 0.50),
    'TOK_TRIX': ('TPSL', 2.00, 1.50, 0.00),
    'ALL_ADX_FAST': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 0.50, 0.00),
}

STRAT_EXITS[('ftmo', 'HK50.cash', '15m')] = {
    'ALL_ICHI_TK': ('TPSL', 3.00, 1.50, 0.00),
}

STRAT_EXITS[('ftmo', 'US2000.cash', '15m')] = {
    'ALL_MSTAR': ('TPSL', 2.00, 0.50, 0.00),
}

# ==== Pepperstone (2026-04-29) ====

# ==== Pepperstone (2026-04-30 find_winners) ====

STRAT_EXITS[('pepperstone', 'AUDUSD', '15m')] = {
'ALL_CONSEC_REV': ('TPSL', 3.0, 2.0, 0),
    'ALL_ENGULF': ('TPSL', 1.5, 1.5, 0),
    'ALL_FVG_BULL': ('TPSL', 2.0, 2.0, 0),
    'ALL_PIVOT_BRK': ('TPSL', 2.5, 2.0, 0),
}

STRAT_EXITS[('pepperstone', 'EURUSD', '15m')] = {
'ALL_MACD_STD_SIG': ('TPSL', 1.5, 2.0, 0),
    'ALL_WILLR_14': ('TPSL', 2.5, 3.0, 0),
    'TOK_WILLR': ('TPSL', 2.5, 3.0, 0),
}

STRAT_EXITS[('pepperstone', 'GBPUSD', '15m')] = {
'ALL_ELDER_BULL': ('TPSL', 3.0, 1.5, 0),
}

STRAT_EXITS[('pepperstone', 'USDCAD', '15m')] = {
'ALL_CCI_100': ('TPSL', 1.5, 1.5, 0),
    'ALL_MACD_DIV': ('TPSL', 2.5, 1.5, 0),
    'ALL_WILLR_14': ('TPSL', 2.5, 2.0, 0),
    'IDX_GAP_CONT': ('TPSL', 3.0, 2.5, 0),
    'TOK_STOCH': ('BE_TP', 1.5, 0.5, 0.75),
    'TOK_TRIX': ('BE_TP', 2.0, 0.3, 1.0),
    'TOK_WILLR': ('TPSL', 2.0, 2.0, 0),
}

STRAT_EXITS[('pepperstone', 'USDCHF', '15m')] = {
'ALL_FIB_618': ('TPSL', 2.5, 2.0, 0),
}

STRAT_EXITS[('pepperstone', 'USDJPY', '15m')] = {
'ALL_ADX_FAST': ('TPSL', 3.0, 2.5, 0),
    'ALL_MSTAR': ('TPSL', 2.0, 3.0, 0),
    'ALL_PIVOT_BOUNCE': ('TPSL', 2.5, 3.0, 0),
    'TOK_BIG': ('TPSL', 3.0, 2.5, 0),
}

STRAT_EXITS[('pepperstone', 'AUS200', '15m')] = {
'ALL_ADX_RSI50': ('TPSL', 2.5, 1.5, 0),
    'ALL_CCI_100': ('TPSL', 2.5, 3.0, 0),
    'ALL_CCI_14_ZERO': ('TPSL', 2.0, 1.5, 0),
    'ALL_DPO_14': ('TPSL', 2.5, 1.5, 0),
    'ALL_ELDER_BULL': ('TPSL', 3.0, 2.0, 0),
    'ALL_HMA_CROSS': ('TPSL', 2.5, 2.5, 0),
    'ALL_MACD_FAST_SIG': ('TPSL', 2.5, 3.0, 0),
    'ALL_MACD_HIST': ('TPSL', 2.5, 3.0, 0),
    'ALL_RSI_50': ('TPSL', 2.5, 1.5, 0),
    'ALL_RSI_EXTREME': ('TPSL', 1.5, 1.5, 0),
    'ALL_WILLR_14': ('TPSL', 2.0, 2.0, 0),
    'ALL_WILLR_7': ('TPSL', 2.0, 2.0, 0),
    'IDX_CONSEC_REV': ('TRAIL', 2.5, 1.0, 0.75),
    'IDX_RSI_REV': ('TPSL', 1.5, 1.5, 0),
    'TOK_2BAR': ('TPSL', 1.25, 2.0, 0),
    'TOK_WILLR': ('TPSL', 2.0, 2.0, 0),
}

STRAT_EXITS[('pepperstone', 'EUSTX50', '15m')] = {
'ALL_DOJI_REV': ('TRAIL', 1.0, 1.0, 0.3),
    'ALL_EMA_921': ('TRAIL', 2.5, 1.0, 0.3),
    'ALL_MACD_HIST': ('TPSL', 1.5, 1.5, 0),
}

STRAT_EXITS[('pepperstone', 'FRA40', '15m')] = {
'ALL_MACD_HIST': ('TPSL', 2.0, 2.5, 0),
}

STRAT_EXITS[('pepperstone', 'JPN225', '15m')] = {
'ALL_DC50': ('TPSL', 3.0, 2.0, 0),
}

STRAT_EXITS[('pepperstone', 'NAS100', '15m')] = {
'ALL_CCI_14_ZERO': ('TPSL', 3.0, 4.0, 0),
    'ALL_EMA_821': ('TPSL', 1.25, 1.5, 0),
    'ALL_LR_BREAK': ('TPSL', 2.0, 2.0, 0),
    'ALL_MACD_STD_SIG': ('TPSL', 3.0, 4.0, 0),
    'ALL_NR4': ('TPSL', 2.0, 2.0, 0),
}

STRAT_EXITS[('pepperstone', 'UK100', '15m')] = {
'ALL_CCI_100': ('TPSL', 1.5, 1.0, 0),
    'ALL_CMO_14': ('TPSL', 3.0, 3.0, 0),
    'ALL_CMO_9': ('TPSL', 2.5, 3.0, 0),
    'ALL_DOJI_REV': ('TPSL', 2.0, 3.0, 0),
    'ALL_ELDER_BULL': ('TPSL', 1.25, 1.5, 0),
    'ALL_MSTAR': ('TPSL', 3.0, 3.0, 0),
    'ALL_NR4': ('TPSL', 1.5, 1.0, 0),
    'ALL_STOCH_RSI': ('TPSL', 1.5, 1.5, 0),
    'TOK_NR4': ('TPSL', 1.5, 1.0, 0),
}

STRAT_EXITS[('pepperstone', 'US30', '15m')] = {
'ALL_ADX_FAST': ('TPSL', 3.0, 2.0, 0),
    'ALL_MSTAR': ('TPSL', 0.75, 0.5, 0),
    'ALL_NR4': ('TPSL', 1.25, 1.5, 0),
    'TOK_NR4': ('TPSL', 1.0, 1.5, 0),
}

STRAT_EXITS[('pepperstone', 'US500', '15m')] = {
'ALL_DC10': ('TPSL', 1.0, 0.75, 0),
    'ALL_ENGULF': ('TPSL', 1.0, 1.0, 0),
    'ALL_STOCH_OB': ('TPSL', 2.5, 3.0, 0),
    'BOS_FVG': ('BE_TP', 1.5, 0.5, 1.0),
    'IDX_PREV_HL': ('TPSL', 1.5, 1.5, 0),
}

STRAT_EXITS[('pepperstone', 'GER40', '15m')] = {
'ALL_ADX_RSI50': ('TPSL', 3.0, 2.5, 0),
    'ALL_CMO_14_ZERO': ('TPSL', 3.0, 3.0, 0),
    'ALL_EMA_513': ('TPSL', 3.0, 2.5, 0),
    'ALL_EMA_821': ('TRAIL', 2.5, 1.0, 0.3),
    'ALL_MACD_FAST_ZERO': ('TPSL', 3.0, 2.5, 0),
    'ALL_MOM_14': ('TPSL', 3.0, 3.0, 0),
    'ALL_MTF_BRK': ('TRAIL', 2.0, 0.75, 0.3),
}

STRAT_EXITS[('pepperstone', 'SPA35', '15m')] = {
'ALL_ICHI_TK': ('TRAIL', 2.5, 0.75, 0.75),
}

STRAT_EXITS[('pepperstone', 'HK50', '15m')] = {
'ALL_3SOLDIERS': ('TPSL', 2.0, 1.5, 0),
    'IDX_ORB30': ('TPSL', 2.0, 2.5, 0),
}

STRAT_EXITS[('pepperstone', 'US2000', '15m')] = {
'ALL_EMA_821': ('TPSL', 2.5, 2.5, 0),
}

STRAT_EXITS[('pepperstone', 'CA60', '15m')] = {
'ALL_3SOLDIERS': ('TRAIL', 3.0, 1.0, 0.75),
}

STRAT_EXITS[('pepperstone', 'SWI20', '15m')] = {
'ALL_MACD_HIST': ('TPSL', 3.0, 4.0, 0),
    'ALL_STOCH_OB': ('TPSL', 2.5, 3.0, 0),
}
