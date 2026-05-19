# Exit configs multi-TF — cle: (broker, sym, tf)
# 15m — regenere 2026-04-09 (sim_exit_custom unifie, margin 5%)
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

# 5ers 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)

# FTMO 15m — BEAM SEARCH 2026-04-25 (top-3 + reverse cleanup)
# Cost-r 0.05R applique au COMBO uniquement. Strats selectionnees sans cost individuel.
# 8 instruments, 68 strats. Tous les strats passant les filtres robustesse sont gardes.

# ==== 5ers 1h (find_winners 2026-05-01) ====

STRAT_EXITS[('5ers', 'XAUUSD', '1h')] = {
    'ALL_HMA_CROSS': ('TPSL', 3.0, 4.0, 0),
}

STRAT_EXITS[('5ers', 'XAGUSD', '1h')] = {
    'ALL_FVG_BULL': ('TPSL', 3.0, 5.0, 0),
    'ALL_KC_BRK': ('TPSL', 2.5, 2.5, 0),
}

STRAT_EXITS[('5ers', 'NAS100', '1h')] = {
    'BOS_FVG': ('BE_TP', 2.0, 0.3, 1.0),
}

STRAT_EXITS[('5ers', 'SP500', '1h')] = {
    'ALL_PIVOT_BOUNCE': ('BE_TP', 1.0, 0.75, 1.0),
}

STRAT_EXITS[('5ers', 'UK100', '1h')] = {
    'ALL_3SOLDIERS': ('TRAIL', 1.0, 0.3, 0.3),
    'ALL_CMO_9': ('TPSL', 2.5, 2.0, 0),
    'ALL_ELDER_BULL': ('TPSL', 1.25, 1.5, 0),
    'ALL_HAMMER': ('TPSL', 1.5, 2.0, 0),
    'ALL_MACD_DIV': ('TPSL', 1.5, 1.0, 0),
}

STRAT_EXITS[('5ers', 'JPN225', '1h')] = {
    'ALL_EMA_821': ('BE_TP', 2.0, 0.75, 1.0),
    'ALL_FVG_BULL': ('BE_TP', 2.0, 0.5, 1.5),
    'BOS_FVG': ('BE_TP', 2.5, 0.75, 1.5),
    'TOK_NR4': ('TPSL', 1.25, 0.75, 0),
}

STRAT_EXITS[('5ers', 'US30', '1h')] = {
    'ALL_ADX_RSI50': ('BE_TP', 3.0, 0.3, 0.75),
    'ALL_CMO_9': ('TPSL', 2.5, 2.0, 0),
    'ALL_MACD_ADX': ('TPSL', 2.5, 2.5, 0),
    'ALL_RSI_50': ('BE_TP', 3.0, 0.3, 0.75),
    'TOK_NR4': ('TPSL', 1.25, 0.5, 0),
}

STRAT_EXITS[('5ers', 'DAX40', '1h')] = {
    'ALL_CCI_100': ('TPSL', 2.0, 2.5, 0),
    'ALL_MACD_HIST': ('TPSL', 2.5, 3.0, 0),
    'BOS_FVG': ('TPSL', 3.0, 3.0, 0),
}

# ==== FTMO 1h (find_winners 2026-05-01) ====

# ==== 5ers 4h (find_winners 2026-05-02) ====

# ==== Pepperstone multi-TF (find_winners 2026-05-03) ====

# ==== Pepperstone 1h v3 (find_winners 2026-04-30, 33 syms) ====

STRAT_EXITS[('pepperstone', 'AUDUSD', '1h')] = {
    'ALL_3SOLDIERS': ('TPSL', 2.5, 2.0, 0.0),
    'ALL_DC50': ('TPSL', 3.0, 2.0, 0.0),
    'ALL_DOJI_REV': ('TPSL', 2.5, 1.5, 0.0),
    'ALL_HMA_CROSS': ('TPSL', 3.0, 2.5, 0.0),
    'TOK_STOCH': ('TPSL', 2.5, 2.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'EURUSD', '1h')] = {
    'ALL_FISHER_9': ('TPSL', 2.5, 3.0, 0.0),
    'ALL_ICHI_TK': ('TPSL', 3.0, 3.0, 0.0),
    'ALL_MACD_ADX': ('TPSL', 0.75, 1.0, 0.0),
    'ALL_MACD_RSI': ('TPSL', 3.0, 2.5, 0.0),
    'ALL_MACD_STD_SIG': ('TPSL', 1.25, 1.0, 0.0),
    'ALL_STOCH_RSI': ('TPSL', 3.0, 3.0, 0.0),
    'AVWAP_RECLAIM': ('TPSL', 1.25, 1.0, 0.0),
    'TOK_FISHER': ('TPSL', 2.5, 3.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'GBPUSD', '1h')] = {
    'ALL_CONSEC_REV': ('TPSL', 2.5, 2.0, 0.0),
    'ALL_EMA_921': ('BE_TP', 2.0, 0.3, 1.0),
    'ALL_FISHER_9': ('TPSL', 1.25, 0.75, 0.0),
    'AVWAP_RECLAIM': ('TPSL', 2.0, 0.75, 0.0),
}

STRAT_EXITS[('pepperstone', 'USDCHF', '1h')] = {
    'ALL_MACD_HIST': ('TPSL', 2.0, 2.5, 0.0),
    'IDX_VWAP_BOUNCE': ('TPSL', 3.0, 1.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'USDJPY', '1h')] = {
    'ALL_RSI_EXTREME': ('TPSL', 3.0, 4.0, 0.0),
    'IDX_RSI_REV': ('TPSL', 3.0, 4.0, 0.0),
    'IDX_VWAP_BOUNCE': ('TPSL', 2.5, 1.0, 0.0),
    'TOK_NR4': ('TPSL', 1.25, 1.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'USDCAD', '1h')] = {
    'ALL_MACD_HIST': ('TPSL', 2.5, 2.0, 0.0),
    'ALL_PIVOT_BOUNCE': ('TPSL', 1.5, 1.5, 0.0),
    'IDX_PREV_HL': ('TPSL', 3.0, 2.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'AUS200', '1h')] = {
    'ALL_ADX_RSI50': ('TPSL', 3.0, 4.0, 0.0),
    'ALL_BB_TIGHT': ('TPSL', 3.0, 4.0, 0.0),
    'ALL_ELDER_BULL': ('TPSL', 1.5, 1.5, 0.0),
    'ALL_FISHER_9': ('TPSL', 2.0, 1.5, 0.0),
    'ALL_MACD_ADX': ('TPSL', 3.0, 3.0, 0.0),
    'ALL_MTF_BRK': ('TPSL', 2.5, 2.5, 0.0),
    'ALL_NR4': ('TPSL', 1.0, 1.0, 0.0),
    'ALL_PIVOT_BOUNCE': ('BE_TP', 2.5, 0.5, 1.5),
    'ALL_WILLR_14': ('TPSL', 2.0, 1.5, 0.0),
    'TOK_FISHER': ('TPSL', 2.0, 1.5, 0.0),
    'TOK_STOCH': ('BE_TP', 1.5, 0.75, 1.5),
}

STRAT_EXITS[('pepperstone', 'EUSTX50', '1h')] = {
    'ALL_PSAR_EMA': ('TPSL', 3.0, 2.5, 0.0),
    'ALL_SUPERTREND': ('TPSL', 2.5, 2.0, 0.0),
    'IDX_CONSEC_REV': ('TPSL', 3.0, 3.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'FRA40', '1h')] = {
    'ALL_MACD_STD_SIG': ('TPSL', 1.5, 2.0, 0.0),
    'ALL_NR4': ('TPSL', 2.5, 3.0, 0.0),
    'ALL_WILLR_14': ('TPSL', 3.0, 3.0, 0.0),
    'AVWAP_RECLAIM': ('TPSL', 2.5, 1.5, 0.0),
    'IDX_3SOLDIERS': ('TRAIL', 3.0, 1.0, 0.75),
}

STRAT_EXITS[('pepperstone', 'JPN225', '1h')] = {
    'ALL_EMA_821': ('TPSL', 1.5, 1.0, 0.0),
    'ALL_EMA_921': ('TPSL', 1.5, 1.0, 0.0),
    'ALL_FVG_BULL': ('TPSL', 2.0, 1.5, 0.0),
    'ALL_STOCH_OB': ('TPSL', 2.5, 3.0, 0.0),
    'BOS_FVG': ('TPSL', 2.5, 1.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'NAS100', '1h')] = {
    'ALL_MACD_HIST': ('TPSL', 1.25, 1.5, 0.0),
    'TOK_STOCH': ('TPSL', 1.25, 1.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'UK100', '1h')] = {
    'ALL_CMO_14_ZERO': ('TPSL', 0.75, 0.75, 0.0),
    'ALL_ELDER_BEAR': ('TPSL', 1.0, 1.0, 0.0),
    'ALL_MOM_14': ('TPSL', 0.75, 0.75, 0.0),
    'IDX_BB_REV': ('TPSL', 2.0, 2.0, 0.0),
    'IDX_CONSEC_REV': ('TPSL', 2.5, 2.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'US30', '1h')] = {
    'ALL_MOM_10': ('TPSL', 2.5, 2.5, 0.0),
    'ALL_NR4': ('TPSL', 1.25, 1.5, 0.0),
    'ALL_PIVOT_BOUNCE': ('TPSL', 1.0, 0.5, 0.0),
    'ALL_TRIX': ('TPSL', 2.5, 2.5, 0.0),
    'IDX_PREV_HL': ('BE_TP', 1.5, 0.5, 1.0),
    'TOK_NR4': ('TPSL', 1.25, 0.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'US500', '1h')] = {
    'ALL_AROON_CROSS': ('BE_TP', 2.5, 0.75, 1.5),
}

STRAT_EXITS[('pepperstone', 'GER40', '1h')] = {
    'ALL_CCI_100': ('TPSL', 2.5, 3.0, 0.0),
    'ALL_CMO_14': ('TPSL', 2.5, 3.0, 0.0),
    'ALL_CMO_9': ('TPSL', 2.0, 2.5, 0.0),
    'ALL_CONSEC_REV': ('TPSL', 1.5, 0.5, 0.0),
    'ALL_INSIDE_BRK': ('TPSL', 3.0, 2.5, 0.0),
    'ALL_KC_BRK': ('TPSL', 1.25, 1.0, 0.0),
    'ALL_MACD_ADX': ('TPSL', 3.0, 2.0, 0.0),
    'ALL_PSAR_EMA': ('TPSL', 2.0, 2.5, 0.0),
    'ALL_RSI_DIV': ('TPSL', 1.25, 1.5, 0.0),
    'ALL_WILLR_7': ('TPSL', 3.0, 2.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'SPA35', '1h')] = {
    'ALL_ELDER_BULL': ('TPSL', 2.5, 4.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'HK50', '1h')] = {
    'ALL_3SOLDIERS': ('BE_TP', 2.0, 0.75, 1.5),
    'ALL_DC50': ('TPSL', 3.0, 2.0, 0.0),
    'ALL_DPO_14': ('TPSL', 2.0, 1.0, 0.0),
    'ALL_FVG_BULL': ('TPSL', 1.5, 1.5, 0.0),
    'BOS_FVG': ('TPSL', 3.0, 2.0, 0.0),
    'IDX_3SOLDIERS': ('TPSL', 2.0, 1.5, 0.0),
}

STRAT_EXITS[('pepperstone', 'US2000', '1h')] = {
    'ALL_EMA_821': ('BE_TP', 1.5, 0.75, 1.0),
    'ALL_ICHI_TK': ('TRAIL', 2.0, 1.0, 0.5),
    'ALL_MACD_FAST_SIG': ('TPSL', 1.5, 1.5, 0.0),
    'ALL_STOCH_RSI': ('TPSL', 2.0, 2.5, 0.0),
    'IDX_VWAP_BOUNCE': ('TPSL', 3.0, 4.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'CA60', '1h')] = {
    'ALL_DC50': ('TRAIL', 1.5, 0.3, 0.3),
    'ALL_ELDER_BULL': ('TPSL', 2.5, 5.0, 0.0),
    'ALL_EMA_821': ('TPSL', 2.0, 2.5, 0.0),
    'ALL_EMA_921': ('TPSL', 2.0, 2.0, 0.0),
    'ALL_FVG_BULL': ('TPSL', 2.5, 5.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'SWI20', '1h')] = {
    'IDX_3SOLDIERS': ('BE_TP', 1.5, 0.75, 1.5),
}

STRAT_EXITS[('pepperstone', 'CN50', '1h')] = {
    'ALL_CMO_9': ('TPSL', 3.0, 3.0, 0.0),
    'ALL_ELDER_BULL': ('TPSL', 3.0, 3.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'CHINAH', '1h')] = {
    'ALL_DC50': ('TPSL', 1.5, 2.0, 0.0),
    'ALL_EMA_513': ('BE_TP', 2.0, 0.5, 1.5),
    'ALL_KC_BRK': ('TPSL', 1.5, 2.0, 0.0),
    'ALL_MACD_FAST_ZERO': ('BE_TP', 2.0, 0.5, 1.5),
    'ALL_MACD_RSI': ('TPSL', 1.5, 1.5, 0.0),
    'BOS_FVG': ('TPSL', 1.5, 2.0, 0.0),
    'IDX_CONSEC_REV': ('TPSL', 3.0, 1.5, 0.0),
    'TOK_STOCH': ('TPSL', 3.0, 2.0, 0.0),
}

STRAT_EXITS[('pepperstone', 'SCI25', '1h')] = {
    'ALL_MACD_RSI': ('BE_TP', 3.0, 0.75, 2.0),
    'TOK_TRIX': ('TPSL', 2.5, 1.0, 0.0),
}

# ==== Pepperstone 15m v4 (find_winners 2026-05-11, 1y glissant, PF>=1.2, n>=100, 16 syms / 44 strats) ====

# ==== FTMO 1h v4 (find_winners 2026-05-13, n>=100 PF>=1.15, 11 syms / 40 strats) ====

# ==== FTMO 1h v4 (find_winners 2026-05-13, n>=100 PF>=1.20, 11 syms / 32 strats) ====

# ==== FTMO 1h v4 (find_winners 2026-05-13, n>=100 PF>=1.15, 11 syms / 40 strats) ====

# ==== FTMO 1h v4 (find_winners 2026-05-13, n>=100 PF>=1.25, 7 syms / 21 strats) ====

# ==== FTMO 1h v4 (find_winners 2026-05-13, n>=100 PF>=1.15, 11 syms / 40 strats) ====

# ==== FTMO 1h v4 (find_winners 2026-05-13, n>=100 PF>=1.20, 11 syms / 32 strats) ====

STRAT_EXITS[('ftmo', 'XAUUSD', '1h')] = {
    'ALL_HMA_CROSS': ('TPSL', 3.0, 4.0, 0.0),
}

STRAT_EXITS[('ftmo', 'GER40.cash', '1h')] = {
    'ALL_ELDER_BEAR': ('TPSL', 2.5, 2.5, 0.0),
    'ALL_INSIDE_BRK': ('TPSL', 3.0, 2.5, 0.0),
    'ALL_MACD_ADX': ('TPSL', 2.0, 2.5, 0.0),
    'BOS_FVG': ('TPSL', 3.0, 3.0, 0.0),
    'IDX_CONSEC_REV': ('TPSL', 2.5, 4.0, 0.0),
}

STRAT_EXITS[('ftmo', 'AUS200.cash', '1h')] = {
    'ALL_BB_TIGHT': ('TPSL', 3.0, 4.0, 0.0),
    'ALL_ELDER_BULL': ('TPSL', 1.5, 1.5, 0.0),
    'ALL_FISHER_9': ('TPSL', 2.0, 1.5, 0.0),
    'ALL_HAMMER': ('TPSL', 2.0, 2.5, 0.0),
    'TOK_FISHER': ('TPSL', 2.0, 1.5, 0.0),
}

STRAT_EXITS[('ftmo', 'EU50.cash', '1h')] = {
    'ALL_PIVOT_BOUNCE': ('TPSL', 1.25, 1.0, 0.0),
}

STRAT_EXITS[('ftmo', 'HK50.cash', '1h')] = {
    'ALL_DC50': ('TPSL', 3.0, 2.0, 0.0),
    'ALL_FVG_BULL': ('TPSL', 1.5, 1.5, 0.0),
    'BOS_FVG': ('TPSL', 2.5, 2.0, 0.0),
}

STRAT_EXITS[('ftmo', 'UK100.cash', '1h')] = {
    'ALL_ELDER_BULL': ('TPSL', 1.5, 1.5, 0.0),
    'ALL_HAMMER': ('TPSL', 1.5, 2.0, 0.0),
    'ALL_MACD_DIV': ('TPSL', 1.0, 1.0, 0.0),
    'IDX_BB_REV': ('TPSL', 3.0, 3.0, 0.0),
}

STRAT_EXITS[('ftmo', 'US100.cash', '1h')] = {
    'ALL_MACD_FAST_SIG': ('TPSL', 1.25, 1.5, 0.0),
}

STRAT_EXITS[('ftmo', 'US2000.cash', '1h')] = {
    'AVWAP_RECLAIM': ('TPSL', 1.25, 1.5, 0.0),
}

STRAT_EXITS[('ftmo', 'US30.cash', '1h')] = {
    'ALL_3SOLDIERS': ('TPSL', 1.5, 1.5, 0.0),
    'ALL_CMO_9': ('TPSL', 2.5, 2.5, 0.0),
    'ALL_DPO_14': ('TPSL', 1.25, 1.5, 0.0),
    'IDX_VWAP_BOUNCE': ('TPSL', 2.0, 1.0, 0.0),
    'TOK_NR4': ('TPSL', 1.25, 0.5, 0.0),
}

STRAT_EXITS[('ftmo', 'US500.cash', '1h')] = {
    'ALL_HMA_CROSS': ('TPSL', 0.75, 0.75, 0.0),
    'ALL_PIVOT_BOUNCE': ('BE_TP', 1.0, 0.75, 1.0),
}

STRAT_EXITS[('ftmo', 'JP225.cash', '1h')] = {
    'ALL_EMA_821': ('BE_TP', 1.5, 0.75, 1.0),
    'ALL_EMA_921': ('TPSL', 1.5, 1.0, 0.0),
    'ALL_FVG_BULL': ('TPSL', 1.25, 1.5, 0.0),
    'TOK_STOCH': ('TPSL', 3.0, 3.0, 0.0),
}

# ==== Exness 1h v1 (find_winners 2026-05-13, n>=100 PF>=1.20, 19 syms / 47 strats) ====

STRAT_EXITS[('exness', 'AUDUSD', '1h')] = {
    'ALL_ADX_RSI50': ('TPSL', 2.5, 0.75, 0.0),
    'TOK_BIG': ('BE_TP', 3.0, 0.75, 2.0),
}

STRAT_EXITS[('exness', 'EURUSD', '1h')] = {
    'ALL_MACD_ADX': ('TPSL', 1.0, 1.0, 0.0),
    'ALL_MACD_STD_SIG': ('TPSL', 0.75, 1.0, 0.0),
}

STRAT_EXITS[('exness', 'GBPUSD', '1h')] = {
    'ALL_EMA_921': ('BE_TP', 2.5, 0.5, 1.0),
    'ALL_INSIDE_BRK': ('TPSL', 3.0, 4.0, 0.0),
}

STRAT_EXITS[('exness', 'USDCHF', '1h')] = {
    'ALL_CCI_20_ZERO': ('TPSL', 1.0, 1.0, 0.0),
}

STRAT_EXITS[('exness', 'USDJPY', '1h')] = {
    'ALL_FVG_BULL': ('TPSL', 3.0, 4.0, 0.0),
}

STRAT_EXITS[('exness', 'USDCAD', '1h')] = {
    'ALL_ADX_FAST': ('TPSL', 2.0, 2.0, 0.0),
    'ALL_ENGULF': ('TPSL', 3.0, 2.0, 0.0),
}

STRAT_EXITS[('exness', 'NZDUSD', '1h')] = {
    'IDX_VWAP_BOUNCE': ('TPSL', 2.0, 2.5, 0.0),
    'TOK_BIG': ('TPSL', 1.0, 1.0, 0.0),
    'TOK_WILLR': ('TPSL', 2.5, 3.0, 0.0),
}

STRAT_EXITS[('exness', 'XAUUSD', '1h')] = {
    'ALL_HMA_CROSS': ('TPSL', 3.0, 4.0, 0.0),
    'ALL_TRIX': ('TPSL', 3.0, 3.0, 0.0),
}

STRAT_EXITS[('exness', 'AUS200', '1h')] = {
    'ALL_PIVOT_BRK': ('TPSL', 2.0, 2.0, 0.0),
    'TOK_BIG': ('TPSL', 2.0, 2.5, 0.0),
}

STRAT_EXITS[('exness', 'DE30', '1h')] = {
    'ALL_MACD_ADX': ('TPSL', 2.5, 3.0, 0.0),
    'AVWAP_RECLAIM': ('TPSL', 2.5, 3.0, 0.0),
    'BOS_FVG': ('TPSL', 3.0, 1.0, 0.0),
}

STRAT_EXITS[('exness', 'FR40', '1h')] = {
    'ALL_CCI_100': ('TPSL', 2.5, 2.0, 0.0),
    'ALL_FISHER_9': ('TPSL', 3.0, 2.5, 0.0),
    'ALL_HMA_CROSS': ('TPSL', 2.5, 1.5, 0.0),
    'ALL_MACD_ADX': ('TPSL', 2.0, 1.5, 0.0),
    'TOK_FISHER': ('TPSL', 3.0, 2.5, 0.0),
}

STRAT_EXITS[('exness', 'HK50', '1h')] = {
    'ALL_EMA_821': ('TPSL', 3.0, 3.0, 0.0),
}

STRAT_EXITS[('exness', 'JP225', '1h')] = {
    'ALL_EMA_821': ('TPSL', 2.0, 1.0, 0.0),
    'ALL_EMA_921': ('TPSL', 2.0, 1.0, 0.0),
    'ALL_FISHER_9': ('TPSL', 3.0, 4.0, 0.0),
    'ALL_TRIX': ('TPSL', 2.0, 2.5, 0.0),
}

STRAT_EXITS[('exness', 'STOXX50', '1h')] = {
    'ALL_FISHER_9': ('TPSL', 1.5, 1.5, 0.0),
    'ALL_MACD_FAST_SIG': ('TPSL', 2.0, 2.5, 0.0),
}

STRAT_EXITS[('exness', 'UK100', '1h')] = {
    'ALL_DOJI_REV': ('TPSL', 1.5, 2.5, 0.0),
    'ALL_HAMMER': ('TPSL', 2.0, 2.5, 0.0),
    'ALL_MACD_DIV': ('TPSL', 1.5, 1.5, 0.0),
    'BOS_FVG': ('BE_TP', 2.5, 0.5, 1.5),
    'TOK_WILLR': ('TPSL', 2.0, 1.0, 0.0),
}

STRAT_EXITS[('exness', 'US30', '1h')] = {
    'ALL_MACD_ADX': ('TPSL', 2.5, 2.5, 0.0),
    'IDX_PREV_HL': ('BE_TP', 1.0, 0.5, 1.0),
    'IDX_VWAP_BOUNCE': ('BE_TP', 1.5, 0.5, 1.0),
    'TOK_NR4': ('TPSL', 1.25, 0.5, 0.0),
}

STRAT_EXITS[('exness', 'US500', '1h')] = {
    'ALL_AROON_CROSS': ('TPSL', 2.0, 1.5, 0.0),
    'IDX_BB_REV': ('TPSL', 3.0, 4.0, 0.0),
}

STRAT_EXITS[('exness', 'USTEC', '1h')] = {
    'ALL_ENGULF': ('TPSL', 1.5, 1.0, 0.0),
}

STRAT_EXITS[('exness', 'BTCUSD', '1h')] = {
    'ALL_ICHI_TK': ('TPSL', 3.0, 5.0, 0.0),
    'IDX_VWAP_BOUNCE': ('BE_TP', 1.0, 0.3, 1.0),
    'TOK_NR4': ('TPSL', 1.5, 2.0, 0.0),
}

# ==== Exness Standard 1h v1 (find_winners 2026-05-14, n>=100 PF>=1.20, 17 syms / 36 strats) ====

# ==== Exness Standard 15m (find_winners 2026-05-18, n>=100, PF>=1.20) ====

# ==== Exness Standard holdout Apr+May (find_winners 2026-05-18, < 2026-04-01) ====

# ==== Exness Standard holdout May (find_winners 2026-05-18, < 2026-05-01) ====

# ==== Exness Standard 1h PF>=1.30 holdout AprMay (find_winners 2026-05-19) ====

# ==== Exness Standard 1h PF>=1.30 holdout May (find_winners 2026-05-19) ====

STRAT_EXITS[('exness_standard', 'NZDUSDm', '1h')] = {
    'TOK_BIG': ('TPSL', 1.0, 1.5, 0),
}

STRAT_EXITS[('exness_standard', 'EURGBPm', '1h')] = {
    'IDX_BB_REV': ('BE_TP', 2.0, 0.5, 1.5),
}

STRAT_EXITS[('exness_standard', 'XAUUSDm', '1h')] = {
    'ALL_HMA_CROSS': ('TPSL', 3.0, 4.0, 0),
}

STRAT_EXITS[('exness_standard', 'USOILm', '1h')] = {
    'ALL_ELDER_BULL': ('TPSL', 1.5, 2.0, 0),
}

STRAT_EXITS[('exness_standard', 'DE30m', '1h')] = {
    'ALL_ELDER_BEAR': ('TPSL', 2.5, 2.5, 0),
}

STRAT_EXITS[('exness_standard', 'JP225m', '1h')] = {
    'ALL_AROON_CROSS': ('TPSL', 2.0, 1.5, 0),
    'ALL_EMA_821': ('TPSL', 2.0, 1.0, 0),
}

STRAT_EXITS[('exness_standard', 'UK100m', '1h')] = {
    'ALL_DOJI_REV': ('TPSL', 1.5, 2.5, 0),
    'ALL_HAMMER': ('TPSL', 2.0, 2.5, 0),
    'BOS_FVG': ('TRAIL', 2.5, 1.0, 0.5),
}

STRAT_EXITS[('exness_standard', 'US30m', '1h')] = {
    'ALL_ADX_RSI50': ('BE_TP', 3.0, 0.3, 0.75),
    'ALL_RSI_50': ('BE_TP', 3.0, 0.3, 0.75),
    'TOK_NR4': ('TPSL', 1.25, 0.5, 0),
}

STRAT_EXITS[('exness_standard', 'BTCUSDm', '1h')] = {
    'IDX_VWAP_BOUNCE': ('BE_TP', 1.0, 0.3, 1.0),
}

# ==== Dukascopy 4h (find_winners 2026-05-19, 2021-2025) ====

# ==== Dukascopy 4h swing (strats_swing, find_winners 2026-05-19, 2021-2025) ====

STRAT_EXITS[('dukascopy', 'EURJPY', '4h')] = {
    'B2_MONTHLY_HL': ('TPSL', 2.0, 2.0, 0),
}

STRAT_EXITS[('dukascopy', 'EURGBP', '4h')] = {
    'A9_LR_SLOPE_50': ('TPSL', 2.0, 1.0, 0),
    'D3_ENGULF_WHL': ('TPSL', 2.5, 1.0, 0),
}

STRAT_EXITS[('dukascopy', 'XAUUSD', '4h')] = {
    'B6_KC_BRK_50': ('TPSL', 2.0, 2.5, 0),
}

STRAT_EXITS[('dukascopy', 'JP225', '4h')] = {
    'A5_TSMOM_3M': ('TPSL', 0.75, 1.0, 0),
}

STRAT_EXITS[('dukascopy', 'UK100', '4h')] = {
    'D4_PIN_LEVEL': ('TPSL', 3.0, 1.5, 0),
}

STRAT_EXITS[('dukascopy', 'US30', '4h')] = {
    'B6_KC_BRK_50': ('TPSL', 2.5, 1.5, 0),
}
