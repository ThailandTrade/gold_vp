# Exit configs 15m — regenere 2026-04-09 (sim_exit_custom unifie, margin 5%)
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

# 5ers 15m — REFONTE ROBUSTESSE 2026-04-22
# Scoring: PF_trimmed x WR x (1 - outlier_share)
# Filtres: PF_trim>=1.20, median_R>0, pct>3R<=1%, m_neg<=2, test_pf>=1.0 (walk-forward 70/30)
# XAUUSD skippe (lot min), US30/UK100/JPN225 retires (correlation / rend marginal)

STRAT_EXITS[('5ers', 'DAX40')] = {
    # Combo 4 — DD 5ers -0.21%, Rend +1.6%, M+ 12/13
    'ALL_MOM_10': ('TRAIL', 3.00, 0.30, 0.30),
    'TOK_NR4': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_ELDER_BULL': ('TPSL', 2.50, 1.00, 0.00),
    'TOK_FISHER': ('TPSL', 3.00, 1.00, 0.00),
}

STRAT_EXITS[('5ers', 'NAS100')] = {
    # Combo 11 — DD 5ers -0.35%, Rend +11.8%, M+ 12/13
    'ALL_LR_BREAK': ('TRAIL', 3.00, 0.30, 0.50),
    'ALL_MACD_STD_SIG': ('TPSL', 3.00, 3.00, 0.00),
    'BOS_FVG': ('BE_TP', 3.00, 0.30, 1.00),
    'ALL_MSTAR': ('BE_TP', 2.00, 0.30, 1.00),
    'ALL_AROON_CROSS': ('TPSL', 3.00, 0.50, 0.00),
    'ALL_FVG_BULL': ('BE_TP', 3.00, 0.50, 0.75),
    'TOK_2BAR': ('TPSL', 2.50, 1.00, 0.00),
    'ALL_TRIX': ('BE_TP', 3.00, 0.75, 1.50),
    'ALL_KC_BRK': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_NR4': ('TPSL', 2.00, 1.50, 0.00),
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.50),
}

STRAT_EXITS[('5ers', 'SP500')] = {
    # Combo 10 — DD 5ers -0.27%, Rend +16.1%, M+ 12/13
    'TOK_2BAR': ('TPSL', 2.50, 0.75, 0.00),
    'ALL_MACD_STD_SIG': ('TPSL', 2.50, 3.00, 0.00),
    'ALL_PIVOT_BOUNCE': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_MACD_ADX': ('TPSL', 3.00, 3.00, 0.00),
    'TOK_TRIX': ('BE_TP', 3.00, 0.50, 0.75),
    'LON_STOCH': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_TRIX': ('BE_TP', 3.00, 0.50, 0.75),
    'ALL_EMA_921': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DC10_EMA': ('TPSL', 1.00, 0.75, 0.00),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 0.50, 0.30),
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
