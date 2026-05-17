"""
Config FTMO -- 1h only (15m/4h supprimes 2026-05-17).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}.
LIVE_INSTRUMENTS = tous syms; live_mt5.mt5_lot_size auto-skip si min_lot_risk > target.
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_HMA_CROSS']},
    },
    'GER40.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_ELDER_BEAR', 'ALL_INSIDE_BRK', 'ALL_MACD_ADX', 'BOS_FVG', 'IDX_CONSEC_REV']},
    },
    'US500.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_HMA_CROSS', 'ALL_PIVOT_BOUNCE']},
    },
    'US100.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_MACD_FAST_SIG']},
    },
    'US30.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_3SOLDIERS', 'ALL_CMO_9', 'ALL_DPO_14', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
    },
    'AUS200.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_BB_TIGHT', 'ALL_ELDER_BULL', 'ALL_FISHER_9', 'ALL_HAMMER', 'TOK_FISHER']},
    },
    'HK50.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_DC50', 'ALL_FVG_BULL', 'BOS_FVG']},
    },
    'UK100.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_ELDER_BULL', 'ALL_HAMMER', 'ALL_MACD_DIV', 'IDX_BB_REV']},
    },
    'US2000.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['AVWAP_RECLAIM']},
    },
    'JP225.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'TOK_STOCH']},
    },
    'EU50.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_PIVOT_BOUNCE']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.0004
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['1h']['portfolio']
