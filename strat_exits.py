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

# FTMO 15m — REFONTE ROBUSTESSE 2026-04-22
# Scoring: PF_trimmed x WR x (1 - outlier_share)
# Filtres: PF_trim>=1.20, median_R>0, pct>3R<=1%, m_neg<=2, test_pf>=1.0 (walk-forward 70/30)
# US100, US30, JP225 retires (US correles avec US500, JP225 trop peu de strats robustes)

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    # Combo 4 — DD FTMO -0.55%, Rend +10.2%, M+ 11/13
    'ALL_MACD_RSI': ('BE_TP', 2.50, 0.30, 1.50),
    'BOS_FVG': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_KC_BRK': ('TPSL', 3.00, 1.50, 0.00),
}

STRAT_EXITS[('ftmo', 'GER40.cash')] = {
    # Combo 3 — DD FTMO -0.39%, Rend +4.5%, M+ 13/13
    'ALL_LR_BREAK': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
    'TOK_TRIX': ('TPSL', 3.00, 0.50, 0.00),
}

STRAT_EXITS[('ftmo', 'US500.cash')] = {
    # Combo 10 — DD FTMO -0.39%, Rend +50.2%, M+ 13/13
    'TOK_2BAR': ('TPSL', 2.50, 0.75, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_PIVOT_BOUNCE': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_ENGULF': ('BE_TP', 1.50, 0.50, 1.00),
    'ALL_TRIX': ('BE_TP', 3.00, 0.50, 0.75),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_MSTAR': ('BE_TP', 3.00, 0.75, 1.50),
    'ALL_CMO_14_ZERO': ('BE_TP', 3.00, 0.50, 1.00),
    'ALL_AROON_CROSS': ('TPSL', 2.00, 0.75, 0.00),
    'LON_STOCH': ('TRAIL', 3.00, 0.50, 0.30),
}
