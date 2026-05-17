"""
Config 5ers -- 1h only (15m/4h supprimes 2026-05-17).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}.
LIVE_INSTRUMENTS = tous syms; live_mt5.mt5_lot_size auto-skip si min_lot_risk > target.
"""
BROKER = '5ers'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_HMA_CROSS']},
    },
    'DAX40': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_CCI_100', 'ALL_MACD_HIST', 'BOS_FVG']},
    },
    'SP500': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_PIVOT_BOUNCE']},
    },
    'NAS100': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['BOS_FVG']},
    },
    'US30': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_9', 'ALL_MACD_ADX', 'ALL_RSI_50', 'TOK_NR4']},
    },
    'UK100': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_3SOLDIERS', 'ALL_CMO_9', 'ALL_ELDER_BULL', 'ALL_HAMMER', 'ALL_MACD_DIV']},
    },
    'JPN225': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_EMA_821', 'ALL_FVG_BULL', 'BOS_FVG', 'TOK_NR4']},
    },
    'XAGUSD': {
        '1h': {'risk_pct': 0.00015, 'portfolio': ['ALL_FVG_BULL', 'ALL_KC_BRK']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.00015
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['1h']['portfolio']
