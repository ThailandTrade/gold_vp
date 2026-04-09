# Exit configs 15m par (broker, instrument, strat) - regenere 2026-04-09.
# TRAIL: (TRAIL, sl, act, trail)
# TPSL:  (TPSL, sl, tp, 0)

DEFAULT_EXIT = ('TRAIL', 3.0, 0.5, 0.5)

STRAT_EXITS = {}

STRAT_EXITS[('ftmo', 'XAUUSD')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_BB_TIGHT': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_CMO_9': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_DC10': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DC10_EMA': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DC50': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_ELDER_BEAR': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_EMA_513': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_FVG_BULL': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_HMA_CROSS': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_KC_BRK': ('TRAIL', 3.00, 1.00, 0.75),
    'ALL_MACD_FAST_ZERO': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_MACD_HIST': ('TRAIL', 1.50, 0.50, 0.50),
    'ALL_MACD_RSI': ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_MOM_10': ('TRAIL', 2.00, 0.30, 0.30),
    'ALL_ROC_ZERO': ('TRAIL', 2.00, 0.30, 0.30),
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.50, 0.50),
    'IDX_KC_BRK': ('TRAIL', 3.00, 1.00, 0.75),
    'IDX_TREND_DAY': ('TRAIL', 3.00, 0.50, 0.50),
    'IDX_VWAP_BOUNCE': ('TRAIL', 3.00, 1.00, 0.30),
    'LON_TOKEND': ('TRAIL', 3.00, 1.00, 0.50),
    'TOK_FADE': ('TRAIL', 3.00, 1.00, 0.30),
}

STRAT_EXITS[('ftmo', 'GER40.cash')] = {
    'ALL_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_CCI_100': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.30, 1.00),
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_KB_SQUEEZE': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_MACD_DIV': ('TRAIL', 1.50, 0.50, 0.30),
    'ALL_MSTAR': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_RSI_DIV': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_RSI_EXTREME': ('TRAIL', 0.50, 0.50, 0.30),
    'ALL_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
    'IDX_3SOLDIERS': ('TRAIL', 3.00, 0.30, 0.30),
    'IDX_RSI_REV': ('TRAIL', 0.50, 0.50, 0.30),
    'TOK_PREVEXT': ('TRAIL', 2.00, 1.00, 0.30),
    'TOK_TRIX': ('TRAIL', 3.00, 0.50, 0.50),
}

STRAT_EXITS[('ftmo', 'US500.cash')] = {
    'ALL_CMO_14_ZERO': ('TRAIL', 1.00, 0.50, 0.50),
    'ALL_ELDER_BULL': ('TRAIL', 3.00, 0.75, 0.75),
    'ALL_EMA_921': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_ENGULF': ('TRAIL', 1.50, 0.50, 0.50),
    'ALL_HAMMER': ('TRAIL', 0.50, 0.75, 0.75),
    'ALL_MACD_ADX': ('TPSL', 3.00, 3.00, 0.00),
    'ALL_MOM_14': ('TRAIL', 1.00, 0.50, 0.50),
    'ALL_MSTAR': ('TPSL', 3.00, 1.50, 0.00),
    'ALL_MTF_BRK': ('TRAIL', 1.50, 0.50, 0.30),
    'IDX_ENGULF': ('TRAIL', 1.50, 0.50, 0.50),
    'LON_BIGGAP': ('TPSL', 1.50, 1.00, 0.00),
    'LON_GAP': ('TPSL', 1.50, 1.00, 0.00),
    'TOK_BIG': ('TPSL', 1.50, 2.00, 0.00),
}

STRAT_EXITS[('ftmo', 'US100.cash')] = {
    'ALL_CMO_9': ('TRAIL', 1.50, 0.30, 1.00),
    'ALL_DC10': ('TRAIL', 2.00, 0.75, 0.50),
    'ALL_DC10_EMA': ('TRAIL', 2.00, 0.75, 0.50),
    'ALL_EMA_821': ('TRAIL', 3.00, 1.00, 1.00),
    'ALL_ICHI_TK': ('TRAIL', 3.00, 1.00, 0.30),
    'ALL_MSTAR': ('TRAIL', 3.00, 0.30, 0.30),
    'ALL_PIVOT_BRK': ('TRAIL', 1.00, 0.30, 0.30),
    'ALL_RSI_50': ('TRAIL', 1.00, 0.30, 0.30),
    'D8': ('TPSL', 3.00, 0.25, 0.00),
    'IDX_3SOLDIERS': ('TRAIL', 1.50, 0.50, 0.50),
    'LON_BIGGAP': ('TRAIL', 1.50, 0.30, 0.30),
    'TOK_PREVEXT': ('TPSL', 2.50, 0.75, 0.00),
    'TOK_TRIX': ('TRAIL', 2.00, 1.00, 1.00),
}

STRAT_EXITS[('ftmo', 'US30.cash')] = {
    'ALL_KB_SQUEEZE': ('TRAIL', 1.50, 0.50, 0.50),
    'LON_TOKEND': ('TPSL', 3.00, 3.00, 0.00),
    'NY_ELDER': ('TRAIL', 3.00, 0.50, 0.50),
    'TOK_2BAR': ('TPSL', 3.00, 0.25, 0.00),
    'TOK_PREVEXT': ('TPSL', 3.00, 1.00, 0.00),
    'TOK_TRIX': ('TRAIL', 1.00, 0.50, 0.50),
}

STRAT_EXITS[('ftmo', 'JP225.cash')] = {
    'ALL_INSIDE_BRK': ('TRAIL', 2.00, 1.00, 1.00),
    'ALL_MSTAR': ('TRAIL', 1.50, 0.30, 0.30),
    'ALL_PSAR_EMA': ('TRAIL', 3.00, 0.50, 0.30),
    'ALL_SUPERTREND': ('TRAIL', 3.00, 0.50, 0.30),
    'LON_BIGGAP': ('TRAIL', 1.50, 0.30, 0.30),
    'LON_TOKEND': ('TRAIL', 1.50, 0.50, 0.30),
    'NY_LONEND': ('TRAIL', 3.00, 1.00, 0.30),
    'TOK_PREVEXT': ('TRAIL', 1.00, 0.30, 0.75),
}
