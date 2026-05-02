"""
Config 5ers multi-TF.
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}
"""
BROKER = '5ers'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        '15m': {'risk_pct': 0.0001, 'portfolio': ['IDX_TREND_DAY', 'ALL_BB_TIGHT']},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_HMA_CROSS', 'ALL_NR4', 'ALL_TRIX']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_ENGULF', 'IDX_3SOLDIERS', 'IDX_PREV_HL']},
    },
    'DAX40': {
        '15m': {'risk_pct': 0.0001, 'portfolio': ['ALL_MOM_10', 'ALL_FIB_618', 'ALL_ELDER_BULL']},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_MACD_HIST', 'BOS_FVG', 'IDX_VWAP_BOUNCE', 'TOK_STOCH', 'TOK_TRIX']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_ADX_RSI50', 'ALL_AROON_CROSS', 'ALL_INSIDE_BRK', 'ALL_KC_BRK', 'ALL_MACD_RSI', 'BOS_FVG']},
    },
    'SP500': {
        '15m': {'risk_pct': 0.0001, 'portfolio': [
            'TOK_TRIX', 'ALL_MACD_STD_SIG', 'ALL_PIVOT_BOUNCE',
            'ALL_MACD_ADX', 'ALL_MTF_BRK', 'TOK_2BAR',
        ]},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_FVG_BULL', 'ALL_HAMMER', 'ALL_MACD_HIST', 'ALL_PIVOT_BOUNCE', 'ALL_STOCH_RSI', 'IDX_3SOLDIERS', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_STOCH_OB', 'ALL_STOCH_RSI']},
    },
    'NAS100': {
        '15m': {'risk_pct': 0.0001, 'portfolio': [
            'ALL_AROON_CROSS', 'ALL_LR_BREAK', 'ALL_MACD_STD_SIG',
            'ALL_MSTAR', 'TOK_2BAR',
        ]},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['TOK_STOCH']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_DOJI_REV', 'ALL_EMA_921', 'ALL_KC_BRK']},
    },
    'US30': {
        '15m': {'risk_pct': 0.0001, 'portfolio': ['ALL_ADX_FAST', 'TOK_NR4', 'TOK_TRIX']},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_MACD_ADX', 'ALL_MOM_10', 'ALL_STOCH_RSI', 'IDX_3SOLDIERS', 'TOK_NR4']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_CMO_14_ZERO', 'ALL_HAMMER', 'ALL_LR_BREAK', 'ALL_MOM_10', 'ALL_MOM_14', 'ALL_PIVOT_BOUNCE', 'AVWAP_RECLAIM']},
    },
    'UK100': {
        '15m': {'risk_pct': 0.0001, 'portfolio': ['TOK_TRIX']},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_CMO_9', 'ALL_HAMMER', 'AVWAP_RECLAIM']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_FVG_BULL', 'ALL_MACD_DIV', 'ALL_MACD_FAST_SIG', 'IDX_BB_REV']},
    },
    'JPN225': {
        '15m': {'risk_pct': 0.0001, 'portfolio': ['ALL_3SOLDIERS', 'ALL_FVG_BULL', 'TOK_BIG']},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'ALL_MOM_10', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['ALL_MOM_10', 'ALL_STOCH_OB', 'ALL_STOCH_RSI', 'ALL_WILLR_14', 'IDX_PREV_HL']},
    },
    'XAGUSD': {
        '15m': {'risk_pct': 0.0001, 'portfolio': ['ALL_KC_BRK', 'ALL_FVG_BULL', 'TOK_STOCH', 'ALL_STOCH_OB']},
        '1h': {'risk_pct': 0.0001, 'portfolio': ['ALL_DC10', 'ALL_DC10_EMA', 'ALL_FVG_BULL', 'ALL_KC_BRK', 'ALL_MTF_BRK']},
        '4h': {'risk_pct': 0.0001, 'portfolio': ['TOK_NR4']},
    },
}

LIVE_TIMEFRAMES = ['1h']

# Metaux desactives (XAUUSD/XAGUSD): cout min lot 0.01 depasse le risk target 0.01%
LIVE_INSTRUMENTS = [k for k in ALL_INSTRUMENTS.keys() if k not in ('XAUUSD', 'XAGUSD')]
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['1h']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['1h']['portfolio']
