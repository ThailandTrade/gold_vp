# Exit configs 15m — regenere 2026-04-09 (sim_exit_custom unifie, margin 5%)
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

STRAT_EXITS[('5ers', 'XAUUSD')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_CMO_14': ('TPSL', 3.00, 0.50, 0.00),
    'ALL_CMO_9': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_DC10': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DC50': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DPO_14': ('TRAIL', 2.00, 0.50, 0.30),
    'ALL_ELDER_BEAR': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_ENGULF': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_ICHI_TK': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_KC_BRK': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_LR_BREAK': ('TRAIL', 2.00, 0.75, 0.75),
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.50, 0.50),
    'ALL_MACD_RSI': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_MOM_10': ('TPSL', 2.00, 0.50, 0.00),
    'ALL_MTF_BRK': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_PIVOT_BOUNCE': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_PIVOT_BRK': ('TPSL', 3.00, 0.25, 0.00),
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_ROC_ZERO': ('TPSL', 2.00, 0.50, 0.00),
    'ALL_SUPERTREND': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_TRIX': ('TRAIL', 1.00, 0.30, 0.30),
    'ALL_WILLR_7': ('TRAIL', 3.00, 0.30, 0.30),
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 1.00, 0.75),
    'IDX_ENGULF': ('TRAIL', 3.00, 0.50, 0.50),
    'IDX_GAP_CONT': ('TPSL', 3.00, 0.25, 0.00),
    'IDX_KC_BRK': ('TRAIL', 3.00, 0.30, 0.30),
    'IDX_PREV_HL': ('TRAIL', 3.00, 0.30, 0.30),
    'IDX_TREND_DAY': ('TRAIL', 3.00, 0.50, 0.50),
    'IDX_VWAP_BOUNCE': ('TRAIL', 3.00, 1.00, 0.30),
    'LON_STOCH': ('TPSL', 3.00, 0.50, 0.00),
    'TOK_STOCH': ('TRAIL', 1.00, 0.30, 0.30),
    'TOK_TRIX': ('TRAIL', 1.00, 0.30, 0.30),
}

STRAT_EXITS[('5ers', 'DAX40')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_ADX_RSI50': ('TRAIL', 2.00, 0.75, 1.00),
    'ALL_EMA_821': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_EMA_921': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_FVG_BULL': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_ICHI_TK': ('TRAIL', 3.00, 0.75, 0.30),
    'ALL_KB_SQUEEZE': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_KC_BRK': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_LR_BREAK': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_MSTAR': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_MTF_BRK': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_PIVOT_BRK': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_PSAR_EMA': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_RSI_50': ('TRAIL', 2.00, 0.50, 1.00),
    'ALL_SUPERTREND': ('TRAIL', 2.00, 0.50, 0.50),
    'ALL_TRIX': ('TRAIL', 3.00, 0.75, 0.50),
    'IDX_CONSEC_REV': ('TRAIL', 1.50, 1.00, 1.00),
    'IDX_GAP_CONT': ('TRAIL', 3.00, 1.00, 0.75),
    'IDX_KC_BRK': ('TRAIL', 3.00, 0.75, 0.75),
    'IDX_PREV_HL': ('TPSL', 3.00, 1.00, 0.00),
    'IDX_TREND_DAY': ('TRAIL', 2.00, 1.00, 0.30),
    'IDX_VWAP_BOUNCE': ('TRAIL', 3.00, 1.00, 0.30),
    'TOK_2BAR': ('TRAIL', 3.00, 0.75, 0.75),
    'TOK_FISHER': ('TRAIL', 3.00, 1.00, 0.30),
}

STRAT_EXITS[('5ers', 'NAS100')] = {
    'ALL_CMO_14_ZERO': ('TRAIL', 1.00, 0.30, 0.30),
    'ALL_CMO_9': ('TRAIL', 1.50, 0.50, 0.30),
    'ALL_DC10': ('TRAIL', 2.00, 0.75, 0.75),
    'ALL_DC10_EMA': ('TRAIL', 2.00, 0.75, 0.75),
    'ALL_DOJI_REV': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_EMA_821': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_EMA_921': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_ICHI_TK': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_LR_BREAK': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_MACD_ADX': ('TRAIL', 1.00, 0.30, 0.50),
    'ALL_MACD_STD_SIG': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_MOM_14': ('TRAIL', 1.00, 0.30, 0.30),
    'ALL_MSTAR': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_MTF_BRK': ('TPSL', 2.00, 1.00, 0.00),
    'ALL_NR4': ('TRAIL', 2.00, 1.00, 1.00),
    'ALL_RSI_50': ('TRAIL', 1.00, 0.30, 0.30),
    'D8': ('TPSL', 2.50, 0.25, 0.00),
    'IDX_3SOLDIERS': ('TRAIL', 1.50, 0.50, 0.50),
    'IDX_GAP_CONT': ('TPSL', 2.50, 3.00, 0.00),
    'IDX_NR4': ('TRAIL', 2.00, 1.00, 1.00),
    'IDX_VWAP_BOUNCE': ('TRAIL', 3.00, 0.50, 0.50),
    'LON_STOCH': ('TPSL', 3.00, 2.00, 0.00),
    'NY_HMA_CROSS': ('TRAIL', 3.00, 0.30, 0.30),
    'TOK_BIG': ('TRAIL', 2.00, 0.30, 0.30),
    'TOK_TRIX': ('TRAIL', 2.00, 0.75, 0.75),
}

STRAT_EXITS[('5ers', 'SP500')] = {
    'ALL_ADX_RSI50': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_CMO_14_ZERO': ('TRAIL', 1.00, 0.50, 0.50),
    'ALL_DPO_14': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_EMA_513': ('TRAIL', 2.00, 0.50, 0.30),
    'ALL_EMA_821': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_EMA_921': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_ICHI_TK': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_KC_BRK': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_LR_BREAK': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_MACD_ADX': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_MACD_FAST_ZERO': ('TRAIL', 2.00, 0.50, 0.30),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 2.00, 0.00),
    'ALL_MOM_14': ('TRAIL', 1.00, 0.50, 0.50),
    'ALL_MSTAR': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_PIVOT_BOUNCE': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_PIVOT_BRK': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_STOCH_PIVOT': ('TRAIL', 0.50, 0.50, 0.50),
    'ALL_TRIX': ('TRAIL', 2.00, 0.50, 0.50),
    'IDX_3SOLDIERS': ('TRAIL', 2.00, 0.30, 0.30),
    'IDX_KC_BRK': ('TRAIL', 2.00, 0.30, 0.30),
    'IDX_VWAP_BOUNCE': ('TRAIL', 2.00, 0.30, 0.30),
    'LON_STOCH': ('TRAIL', 3.00, 0.50, 0.50),
    'NY_ELDER': ('TRAIL', 3.00, 0.30, 0.30),
    'TOK_2BAR': ('TPSL', 2.50, 0.25, 0.00),
    'TOK_BIG': ('TPSL', 2.00, 3.00, 0.00),
}

# FTMO 15m — REDESIGN 2026-04-24
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
