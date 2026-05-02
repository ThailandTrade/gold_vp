"""
Config FTMO multi-TF.
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}
LIVE_TIMEFRAMES: TFs trades en live/BT.
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_MACD_RSI', 'BOS_FVG', 'IDX_TREND_DAY']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_HMA_CROSS']},
    },
    'GER40.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_CCI_100', 'TOK_TRIX']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_CMO_9', 'ALL_ELDER_BEAR', 'ALL_INSIDE_BRK', 'ALL_STOCH_RSI', 'BOS_FVG', 'IDX_CONSEC_REV']},
    },
    'US500.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': [
            'ALL_MACD_STD_SIG', 'ALL_ENGULF', 'ALL_PIVOT_BOUNCE',
            'ALL_TRIX', 'ALL_FVG_BULL', 'TOK_2BAR',
        ]},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_FVG_BULL', 'ALL_HAMMER', 'ALL_MACD_RSI', 'ALL_PIVOT_BOUNCE', 'ALL_STOCH_RSI', 'TOK_STOCH']},
    },
    'US100.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': [
            'ALL_AROON_CROSS', 'ALL_LR_BREAK', 'ALL_MACD_RSI', 'ALL_MSTAR',
            'TOK_2BAR', 'ALL_FVG_BULL', 'ALL_NR4',
        ]},
    },
    'US30.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['TOK_NR4', 'TOK_TRIX', 'ALL_MOM_10']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_3SOLDIERS', 'ALL_CMO_14', 'ALL_CMO_9', 'ALL_DPO_14', 'ALL_ICHI_TK', 'ALL_MACD_ADX', 'ALL_MOM_10']},
    },
    'AUS200.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': [
            'ALL_RSI_DIV', 'ALL_MACD_DIV', 'ALL_CMO_14', 'ALL_STOCH_OB',
            'ALL_WILLR_14', 'ALL_CONSEC_REV', 'ALL_MOM_10',
        ]},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_BB_TIGHT', 'ALL_FISHER_9', 'ALL_MACD_ADX', 'ALL_PIVOT_BOUNCE', 'ALL_WILLR_14', 'ALL_WILLR_7', 'TOK_FISHER']},
    },
    'HK50.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_ICHI_TK']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_DC50', 'BOS_FVG']},
    },
    'UK100.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_HAMMER', 'ALL_LR_BREAK', 'TOK_TRIX']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_HAMMER', 'ALL_MACD_DIV', 'ALL_STOCH_OB', 'AVWAP_RECLAIM', 'IDX_BB_REV']},
    },
    'US2000.cash': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_MSTAR']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_ICHI_TK', 'AVWAP_RECLAIM', 'IDX_VWAP_BOUNCE', 'TOK_NR4', 'TOK_STOCH']},
    },
    'XAGUSD': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_NR4', 'TOK_TRIX', 'ALL_AROON_CROSS', 'ALL_ADX_FAST']},
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_MTF_BRK', 'TOK_TRIX']},
    },
    'EU50.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_CONSEC_REV', 'ALL_HAMMER', 'ALL_PIVOT_BRK']},
    },
    'JP225.cash': {
        '1h': {'risk_pct': 0.0004, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'ALL_MOM_10', 'BOS_FVG']},
    },
}

LIVE_TIMEFRAMES = ['15m']

# XAGUSD desactive: cout 0.01 lot $21.92 > target $18.32 a 0.04% risk
LIVE_INSTRUMENTS = [k for k in ALL_INSTRUMENTS.keys() if k != 'XAGUSD']
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['15m']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['15m']['portfolio']
