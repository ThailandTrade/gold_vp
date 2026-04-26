# Exit configs 15m — regenere 2026-04-09 (sim_exit_custom unifie, margin 5%)
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

# 5ers 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)

STRAT_EXITS[('5ers', 'XAUUSD')] = {
    'IDX_TREND_DAY': ('TPSL', 3.00, 4.00, 0.00),
    'ALL_BB_TIGHT': ('TPSL', 2.50, 2.50, 0.00),
}

STRAT_EXITS[('5ers', 'DAX40')] = {
    'ALL_MOM_10': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_FIB_618': ('TPSL', 2.50, 2.50, 0.00),
    'ALL_ELDER_BULL': ('TPSL', 3.00, 1.00, 0.00),
}

STRAT_EXITS[('5ers', 'SP500')] = {
    'TOK_TRIX': ('BE_TP', 2.00, 0.50, 0.75),
    'ALL_MACD_STD_SIG': ('TPSL', 2.50, 2.50, 0.00),
    'ALL_PIVOT_BOUNCE': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_MACD_ADX': ('TPSL', 2.50, 3.00, 0.00),
    'ALL_MTF_BRK': ('TPSL', 1.00, 0.75, 0.00),
    'ALL_TRIX': ('TPSL', 2.00, 0.75, 0.00),
    'TOK_2BAR': ('TPSL', 2.50, 0.75, 0.00),
}

STRAT_EXITS[('5ers', 'NAS100')] = {
    'ALL_AROON_CROSS': ('BE_TP', 3.00, 0.75, 1.00),
    'ALL_LR_BREAK': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_MSTAR': ('TPSL', 2.50, 0.75, 0.00),
    'TOK_2BAR': ('TPSL', 2.50, 0.50, 0.00),
}

STRAT_EXITS[('5ers', 'US30')] = {
    'ALL_ADX_FAST': ('TRAIL', 3.00, 0.50, 0.30),
    'TOK_NR4': ('TPSL', 1.00, 1.50, 0.00),
    'TOK_TRIX': ('TPSL', 1.20, 0.75, 0.00),
}

STRAT_EXITS[('5ers', 'UK100')] = {
    'TOK_TRIX': ('TPSL', 3.00, 1.00, 0.00),
}

STRAT_EXITS[('5ers', 'JPN225')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_FVG_BULL': ('TPSL', 3.00, 2.50, 0.00),
    'TOK_BIG': ('TPSL', 3.00, 3.00, 0.00),
}

STRAT_EXITS[('5ers', 'XAGUSD')] = {
    'ALL_KC_BRK': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_FVG_BULL': ('TPSL', 3.00, 1.50, 0.00),
    'TOK_STOCH': ('BE_TP', 2.50, 0.50, 0.75),
    'ALL_STOCH_OB': ('BE_TP', 2.50, 0.50, 0.75),
}

# FTMO 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)
# Cost-r 0.05R applique au COMBO uniquement. Strats selectionnees sans cost individuel.
# 8 instruments, 68 strats. Tous les strats passant les filtres robustesse sont gardes.

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    'IDX_TREND_DAY': ('TPSL', 3.00, 5.00, 0.00),
    'ALL_KC_BRK': ('TPSL', 3.00, 1.50, 0.00),
    'BOS_FVG': ('TPSL', 2.50, 2.00, 0.00),
    'ALL_MACD_RSI': ('TRAIL', 2.00, 0.50, 0.30),
    'ALL_INSIDE_BRK': ('TRAIL', 3.00, 0.30, 0.30),
}

STRAT_EXITS[('ftmo', 'GER40.cash')] = {
    'TOK_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_CCI_100': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_ELDER_BULL': ('TPSL', 3.00, 0.75, 0.00),
}

STRAT_EXITS[('ftmo', 'US500.cash')] = {
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

STRAT_EXITS[('ftmo', 'US100.cash')] = {
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

STRAT_EXITS[('ftmo', 'US30.cash')] = {
    'ALL_MSTAR': ('TPSL', 3.00, 0.25, 0.00),
    'TOK_TRIX': ('TPSL', 1.20, 0.75, 0.00),
    'TOK_NR4': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_MOM_10': ('TPSL', 2.50, 1.50, 0.00),
    'ALL_NR4': ('BE_TP', 2.00, 0.75, 1.00),
    'ALL_ADX_FAST': ('BE_TP', 3.00, 0.75, 1.00),
}

STRAT_EXITS[('ftmo', 'AUS200.cash')] = {
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

STRAT_EXITS[('ftmo', 'UK100.cash')] = {
    'ALL_HAMMER': ('TRAIL', 3.00, 0.50, 0.30),
    'TOK_TRIX': ('TPSL', 2.50, 0.50, 0.00),
    'ALL_LR_BREAK': ('BE_TP', 2.50, 0.75, 1.00),
    'ALL_TRIX': ('TPSL', 2.50, 0.75, 0.00),
    'LON_ASIAN_BRK': ('TPSL', 3.00, 0.25, 0.00),
}

STRAT_EXITS[('ftmo', 'XAGUSD')] = {
    'ALL_NR4': ('TRAIL', 2.00, 0.30, 0.30),
    'TOK_NR4': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_AROON_CROSS': ('TRAIL', 3.00, 0.50, 0.50),
    'TOK_TRIX': ('TPSL', 2.00, 1.50, 0.00),
    'ALL_ADX_FAST': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 0.50, 0.00),
}

STRAT_EXITS[('ftmo', 'HK50.cash')] = {
    'ALL_ICHI_TK': ('TPSL', 3.00, 1.50, 0.00),
}

STRAT_EXITS[('ftmo', 'US2000.cash')] = {
    'ALL_MSTAR': ('TPSL', 2.00, 0.50, 0.00),
}

# ICM 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)

STRAT_EXITS[('icm', 'EURUSD')] = {
    'TOK_WILLR': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_RSI_50': ('TPSL', 2.50, 3.00, 0.00),
    'ALL_DOJI_REV': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_WILLR_14': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_STOCH_RSI': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_MACD_ADX': ('TRAIL', 3.00, 0.30, 0.30),
}

STRAT_EXITS[('icm', 'GBPUSD')] = {
    'ALL_WILLR_7': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_AROON_CROSS': ('TPSL', 1.20, 1.50, 0.00),
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_CMO_14': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_MACD_HIST': ('TPSL', 2.50, 0.75, 0.00),
}

STRAT_EXITS[('icm', 'USDCHF')] = {
    'IDX_BB_REV': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_ELDER_BULL': ('TPSL', 3.00, 2.00, 0.00),
}

STRAT_EXITS[('icm', 'USDJPY')] = {
    'LON_ASIAN_BRK': ('TRAIL', 2.00, 0.30, 0.30),
}

STRAT_EXITS[('icm', 'USDCAD')] = {
    'ALL_STOCH_PIVOT': ('TPSL', 3.00, 0.75, 0.00),
    'IDX_GAP_CONT': ('TPSL', 3.00, 2.50, 0.00),
    'ALL_HAMMER': ('TPSL', 2.00, 1.50, 0.00),
}

STRAT_EXITS[('icm', 'AUDUSD')] = {
    'ALL_PIVOT_BRK': ('TPSL', 3.00, 0.75, 0.00),
    'ALL_MACD_ADX': ('TRAIL', 3.00, 0.50, 0.50),
    'NY_ELDER': ('TPSL', 3.00, 1.00, 0.00),
}

STRAT_EXITS[('icm', 'AUS200')] = {
    'ALL_HMA_CROSS': ('TRAIL', 1.50, 0.50, 0.30),
    'TOK_WILLR': ('TPSL', 2.50, 2.00, 0.00),
    'ALL_RSI_EXTREME': ('TPSL', 2.00, 2.50, 0.00),
    'IDX_BB_REV': ('TPSL', 2.00, 1.50, 0.00),
    'ALL_CCI_100': ('TPSL', 2.50, 0.75, 0.00),
    'ALL_ENGULF': ('TPSL', 2.50, 2.50, 0.00),
    'ALL_FIB_618': ('BE_TP', 3.00, 0.50, 0.75),
}

STRAT_EXITS[('icm', 'DE40')] = {
    'ALL_CCI_100': ('TRAIL', 3.00, 0.50, 0.30),
    'TOK_FISHER': ('TPSL', 3.00, 1.50, 0.00),
    'TOK_TRIX': ('TRAIL', 3.00, 0.50, 0.30),
}

STRAT_EXITS[('icm', 'JP225')] = {
    'ALL_STOCH_RSI': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_PSAR_EMA': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_SUPERTREND': ('TPSL', 3.00, 2.50, 0.00),
    'ALL_3SOLDIERS': ('BE_TP', 2.50, 0.50, 0.75),
}

STRAT_EXITS[('icm', 'UK100')] = {
    'TOK_TRIX': ('TPSL', 2.50, 0.75, 0.00),
    'ALL_EMA_921': ('TPSL', 3.00, 2.00, 0.00),
}

STRAT_EXITS[('icm', 'US30')] = {
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_NR4': ('TPSL', 1.50, 1.50, 0.00),
    'IDX_PREV_HL': ('TPSL', 2.50, 2.50, 0.00),
    'ALL_MSTAR': ('TPSL', 3.00, 0.25, 0.00),
    'TOK_TRIX': ('TPSL', 0.80, 0.50, 0.00),
}

STRAT_EXITS[('icm', 'US500')] = {
    'ALL_MACD_STD_SIG': ('TPSL', 2.50, 3.00, 0.00),
    'ALL_PIVOT_BOUNCE': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_MACD_ADX': ('TPSL', 2.50, 2.50, 0.00),
}

STRAT_EXITS[('icm', 'USTEC')] = {
    'ALL_LR_BREAK': ('TPSL', 3.00, 0.50, 0.00),
    'ALL_DC10_EMA': ('TPSL', 1.00, 1.50, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_NR4': ('BE_TP', 2.00, 0.75, 1.00),
    'ALL_ICHI_TK': ('TPSL', 3.00, 1.00, 0.00),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.30, 0.30),
}

# ICM Vague 2 — nouveaux instruments 2026-04-26 (beam search)

STRAT_EXITS[('icm', 'ETHUSD')] = {
    'ALL_HAMMER': ('TPSL', 2.00, 2.00, 0.00),
}

STRAT_EXITS[('icm', 'SOLUSD')] = {
    'ALL_STOCH_PIVOT': ('TPSL', 1.50, 1.50, 0.00),
    'NY_ELDER': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_ELDER_BEAR': ('TPSL', 2.00, 1.00, 0.00),
    'ALL_WILLR_7': ('TPSL', 2.00, 0.75, 0.00),
}

STRAT_EXITS[('icm', 'BNBUSD')] = {
    'ALL_MSTAR': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_HAMMER': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_ADX_RSI50': ('TRAIL', 2.00, 0.30, 0.50),
}

STRAT_EXITS[('icm', 'HK50')] = {
    'ALL_ICHI_TK': ('TPSL', 2.50, 2.50, 0.00),
    'NY_HMA_CROSS': ('TPSL', 1.50, 0.50, 0.00),
    'ALL_KB_SQUEEZE': ('TPSL', 3.00, 2.50, 0.00),
    'TOK_BIG': ('TPSL', 3.00, 3.00, 0.00),
}

STRAT_EXITS[('icm', 'ES35')] = {
    'ALL_CCI_14_ZERO': ('TRAIL', 3.00, 0.30, 0.50),
    'ALL_FIB_618': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_DOJI_REV': ('TPSL', 3.00, 4.00, 0.00),
}

STRAT_EXITS[('icm', 'IT40')] = {
    'ALL_ENGULF': ('TPSL', 2.50, 2.00, 0.00),
    'ALL_KC_BRK': ('TPSL', 3.00, 4.00, 0.00),
}

STRAT_EXITS[('icm', 'CA60')] = {
    'ALL_CCI_20_ZERO': ('TPSL', 3.00, 4.00, 0.00),
    'ALL_WILLR_14': ('TPSL', 3.00, 1.50, 0.00),
}

STRAT_EXITS[('icm', 'NETH25')] = {
    'NY_HMA_CROSS': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_WILLR_7': ('TPSL', 3.00, 2.50, 0.00),
    'ALL_STOCH_OB': ('BE_TP', 2.00, 0.75, 1.50),
}

STRAT_EXITS[('icm', 'SE30')] = {
    'ALL_INSIDE_BRK': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_DC50': ('TPSL', 1.00, 1.50, 0.00),
}

STRAT_EXITS[('icm', 'SWI20')] = {
    'ALL_RSI_EXTREME': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_MACD_HIST': ('TPSL', 2.50, 3.00, 0.00),
    'IDX_RSI_REV': ('TRAIL', 3.00, 0.50, 0.30),
    'LON_STOCH': ('TPSL', 3.00, 0.75, 0.00),
}

STRAT_EXITS[('icm', 'SA40')] = {
    'ALL_ADX_FAST': ('TPSL', 2.50, 0.50, 0.00),
    'IDX_BB_REV': ('TPSL', 2.00, 3.00, 0.00),
    'LON_DC10': ('TRAIL', 1.00, 0.30, 0.30),
    'ALL_PIVOT_BRK': ('TRAIL', 1.50, 0.50, 0.30),
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_DOJI_REV': ('TRAIL', 2.00, 0.50, 0.50),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_FISHER_9': ('TRAIL', 2.00, 0.50, 0.30),
    'ALL_STOCH_OB': ('TPSL', 0.80, 0.50, 0.00),
    'LON_DC10_MOM': ('TRAIL', 1.00, 0.30, 0.30),
    'IDX_3SOLDIERS': ('BE_TP', 2.50, 0.50, 0.75),
    'ALL_CCI_100': ('BE_TP', 1.00, 0.50, 1.00),
}

STRAT_EXITS[('icm', 'NOR25')] = {
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_3SOLDIERS': ('TRAIL', 2.00, 0.50, 0.50),
}
