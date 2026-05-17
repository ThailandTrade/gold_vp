"""
Config Pepperstone -- 1h only (15m/4h supprimes 2026-05-17).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}.
LIVE_INSTRUMENTS = tous syms; live_mt5.mt5_lot_size auto-skip si min_lot_risk > target.
"""
BROKER = 'pepperstone'

ALL_INSTRUMENTS = {
    'AUDUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'ALL_DOJI_REV', 'ALL_HMA_CROSS', 'TOK_STOCH']},
    },
    'EURUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FISHER_9', 'ALL_ICHI_TK', 'ALL_MACD_ADX', 'ALL_MACD_RSI', 'ALL_MACD_STD_SIG', 'ALL_STOCH_RSI', 'AVWAP_RECLAIM', 'TOK_FISHER']},
    },
    'GBPUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CONSEC_REV', 'ALL_EMA_921', 'ALL_FISHER_9', 'AVWAP_RECLAIM']},
    },
    'USDCHF': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'IDX_VWAP_BOUNCE']},
    },
    'USDJPY': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_RSI_EXTREME', 'IDX_RSI_REV', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
    },
    'USDCAD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'ALL_PIVOT_BOUNCE', 'IDX_PREV_HL']},
    },
    'AUS200': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_BB_TIGHT', 'ALL_ELDER_BULL', 'ALL_FISHER_9', 'ALL_MACD_ADX', 'ALL_MTF_BRK', 'ALL_NR4', 'ALL_PIVOT_BOUNCE', 'ALL_WILLR_14', 'TOK_FISHER', 'TOK_STOCH']},
    },
    'EUSTX50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_PSAR_EMA', 'ALL_SUPERTREND', 'IDX_CONSEC_REV']},
    },
    'FRA40': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_STD_SIG', 'ALL_NR4', 'ALL_WILLR_14', 'AVWAP_RECLAIM', 'IDX_3SOLDIERS']},
    },
    'JPN225': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'ALL_STOCH_OB', 'BOS_FVG']},
    },
    'NAS100': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'TOK_STOCH']},
    },
    'UK100': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14_ZERO', 'ALL_ELDER_BEAR', 'ALL_MOM_14', 'IDX_BB_REV', 'IDX_CONSEC_REV']},
    },
    'US30': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MOM_10', 'ALL_NR4', 'ALL_PIVOT_BOUNCE', 'ALL_TRIX', 'IDX_PREV_HL', 'TOK_NR4']},
    },
    'US500': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS']},
    },
    'GER40': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_CMO_14', 'ALL_CMO_9', 'ALL_CONSEC_REV', 'ALL_INSIDE_BRK', 'ALL_KC_BRK', 'ALL_MACD_ADX', 'ALL_PSAR_EMA', 'ALL_RSI_DIV', 'ALL_WILLR_7']},
    },
    'SPA35': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ELDER_BULL']},
    },
    'HK50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'ALL_DPO_14', 'ALL_FVG_BULL', 'BOS_FVG', 'IDX_3SOLDIERS']},
    },
    'US2000': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_ICHI_TK', 'ALL_MACD_FAST_SIG', 'ALL_STOCH_RSI', 'IDX_VWAP_BOUNCE']},
    },
    'CA60': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50', 'ALL_ELDER_BULL', 'ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL']},
    },
    'SWI20': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['IDX_3SOLDIERS']},
    },
    'CN50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_9', 'ALL_ELDER_BULL']},
    },
    'CHINAH': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50', 'ALL_EMA_513', 'ALL_KC_BRK', 'ALL_MACD_FAST_ZERO', 'ALL_MACD_RSI', 'BOS_FVG', 'IDX_CONSEC_REV', 'TOK_STOCH']},
    },
    'SCI25': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_RSI', 'TOK_TRIX']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['AUDUSD']['1h']['portfolio']
