"""
Config Exness multi-TF -- 1h v1 (find_winners 2026-05-13, n>=100, PF>=1.20).
Server UTC+0. Pro account (markup spread, no commission).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}
"""
BROKER = 'exness'

ALL_INSTRUMENTS = {
    'AUDUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'TOK_BIG']},
    },
    'EURUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_ADX', 'ALL_MACD_STD_SIG']},
    },
    'GBPUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_921', 'ALL_INSIDE_BRK']},
    },
    'USDCHF': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_20_ZERO']},
    },
    'USDJPY': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FVG_BULL']},
    },
    'USDCAD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_ENGULF']},
    },
    'NZDUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['IDX_VWAP_BOUNCE', 'TOK_BIG', 'TOK_WILLR']},
    },
    'XAUUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_HMA_CROSS', 'ALL_TRIX']},
    },
    'AUS200': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_PIVOT_BRK', 'TOK_BIG']},
    },
    'DE30': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_ADX', 'AVWAP_RECLAIM', 'BOS_FVG']},
    },
    'FR40': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_FISHER_9', 'ALL_HMA_CROSS', 'ALL_MACD_ADX', 'TOK_FISHER']},
    },
    'HK50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821']},
    },
    'JP225': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FISHER_9', 'ALL_TRIX']},
    },
    'STOXX50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FISHER_9', 'ALL_MACD_FAST_SIG']},
    },
    'UK100': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DOJI_REV', 'ALL_HAMMER', 'ALL_MACD_DIV', 'BOS_FVG', 'TOK_WILLR']},
    },
    'US30': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_ADX', 'IDX_PREV_HL', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
    },
    'US500': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS', 'IDX_BB_REV']},
    },
    'USTEC': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ENGULF']},
    },
    'BTCUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ICHI_TK', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['US30']['1h']['portfolio'] if 'US30' in ALL_INSTRUMENTS and '1h' in ALL_INSTRUMENTS['US30'] else []
