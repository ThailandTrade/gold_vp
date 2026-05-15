"""
Config Exness Standard multi-TF -- 1h v1 (find_winners 2026-05-14, n>=100, PF>=1.20).
Server UTC+0. Standard account (suffix 'm' sur tous les symboles).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}
"""
BROKER = 'exness_standard'

ALL_INSTRUMENTS = {
    'AUDUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['TOK_BIG']},
    },
    'EURUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_MACD_STD_SIG']},
    },
    'GBPUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_FISHER_9']},
    },
    'USDJPYm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_FVG_BULL']},
    },
    'USDCADm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ADX_FAST', 'ALL_MACD_FAST_SIG', 'ALL_MACD_HIST']},
    },
    'NZDUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['IDX_VWAP_BOUNCE', 'TOK_BIG']},
    },
    'XAUUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_HMA_CROSS', 'ALL_TRIX']},
    },
    'AUS200m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_BB_TIGHT', 'ALL_PIVOT_BRK']},
    },
    'DE30m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['BOS_FVG']},
    },
    'JP225m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FISHER_9']},
    },
    'UK100m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_DOJI_REV', 'ALL_MACD_DIV']},
    },
    'US30m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ADX_RSI50', 'ALL_MACD_ADX', 'ALL_RSI_50', 'IDX_PREV_HL', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
    },
    'US500m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_AROON_CROSS', 'ALL_HMA_CROSS', 'IDX_BB_REV']},
    },
    'USTECm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_WILLR_7', 'TOK_FISHER']},
    },
    'BTCUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ICHI_TK', 'IDX_VWAP_BOUNCE']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.01
PORTFOLIO = ALL_INSTRUMENTS['US30m']['1h']['portfolio'] if 'US30m' in ALL_INSTRUMENTS and '1h' in ALL_INSTRUMENTS['US30m'] else []
