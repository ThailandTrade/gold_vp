"""
Config Exness Standard multi-TF -- 1h v1 (find_winners 2026-05-14, n>=100, PF>=1.20).
Server UTC+0. Standard account (suffix 'm' sur tous les symboles).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}
"""
BROKER = 'exness_standard'

ALL_INSTRUMENTS = {
    'AUDUSDm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_ADX_FAST', 'ALL_MACD_ADX']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['TOK_BIG']},
    },
    'EURUSDm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_3SOLDIERS']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_MACD_STD_SIG']},
    },
    'GBPUSDm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_STOCH_OB', 'TOK_BIG']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_FISHER_9']},
    },
    'USDJPYm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_FVG_BULL']},
    },
    'USDCADm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_FIB_618', 'ALL_TRIX', 'TOK_TRIX']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ADX_FAST', 'ALL_MACD_FAST_SIG', 'ALL_MACD_HIST']},
    },
    'USDCHFm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_WILLR_7']},
    },
    'NZDUSDm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['IDX_VWAP_BOUNCE', 'TOK_BIG']},
    },
    'EURJPYm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_DC50', 'ALL_WILLR_14']},
    },
    'EURGBPm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ELDER_BULL', 'ALL_HAMMER', 'IDX_BB_REV']},
    },
    'GBPJPYm': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_MACD_DIV', 'ALL_RSI_DIV']},
    },
    'XAUUSDm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_MACD_STD_SIG']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_HMA_CROSS', 'ALL_TRIX']},
    },
    'USOILm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_HAMMER', 'IDX_VWAP_BOUNCE']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ELDER_BULL', 'ALL_FISHER_9', 'TOK_FISHER']},
    },
    'AUS200m': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_CMO_9', 'ALL_CONSEC_REV', 'ALL_MACD_DIV', 'ALL_RSI_DIV', 'ALL_RSI_EXTREME', 'ALL_STOCH_PIVOT', 'IDX_RSI_REV']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_BB_TIGHT', 'ALL_PIVOT_BRK']},
    },
    'DE30m': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_ENGULF']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['BOS_FVG']},
    },
    'JP225m': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_PSAR_EMA', 'ALL_SUPERTREND']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FISHER_9']},
    },
    'UK100m': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_HAMMER']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_DOJI_REV', 'ALL_MACD_DIV']},
    },
    'US30m': {
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ADX_RSI50', 'ALL_MACD_ADX', 'ALL_RSI_50', 'IDX_PREV_HL', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
    },
    'US500m': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_DC10_EMA', 'ALL_LR_BREAK', 'ALL_MOM_10', 'ALL_MSTAR']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_AROON_CROSS', 'ALL_HMA_CROSS', 'IDX_BB_REV']},
    },
    'USTECm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_ICHI_TK']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_WILLR_7', 'TOK_FISHER']},
    },
    'BTCUSDm': {
        '15m': {'risk_pct': 0.01, 'portfolio': ['ALL_MACD_ADX', 'ALL_PSAR_EMA', 'ALL_SUPERTREND']},
        '1h': {'risk_pct': 0.01, 'portfolio': ['ALL_ICHI_TK', 'IDX_VWAP_BOUNCE']},
    },
}

LIVE_TIMEFRAMES = ['15m', '1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.01
PORTFOLIO = ALL_INSTRUMENTS['US30m']['1h']['portfolio'] if 'US30m' in ALL_INSTRUMENTS and '1h' in ALL_INSTRUMENTS['US30m'] else []
