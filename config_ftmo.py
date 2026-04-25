"""
Config FTMO 15m — BEAM SEARCH 2026-04-25
Methode: beam search top-3 + reverse cleanup iteratif.
Cost-r 0.05R applique au COMBO. 10 instruments (skip JP225 M+8/13, EU50 M+7/13).
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0004,
        'portfolio': ['ALL_MACD_RSI', 'BOS_FVG', 'IDX_TREND_DAY'],
    },
    'GER40.cash': {
        'risk_pct': 0.0004,
        'portfolio': ['ALL_CCI_100', 'TOK_TRIX'],
    },
    'US500.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_MACD_STD_SIG', 'ALL_ENGULF', 'ALL_PIVOT_BOUNCE',
            'ALL_TRIX', 'ALL_FVG_BULL', 'TOK_2BAR',
        ],
    },
    'US100.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_AROON_CROSS', 'ALL_LR_BREAK', 'ALL_MACD_RSI', 'ALL_MSTAR',
            'TOK_2BAR', 'ALL_FVG_BULL', 'ALL_NR4',
        ],
    },
    'US30.cash': {
        'risk_pct': 0.0004,
        'portfolio': ['TOK_NR4', 'TOK_TRIX', 'ALL_MOM_10'],
    },
    'AUS200.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_RSI_DIV', 'ALL_MACD_DIV', 'ALL_CMO_14', 'ALL_STOCH_OB',
            'ALL_WILLR_14', 'ALL_CONSEC_REV', 'ALL_MOM_10',
        ],
    },
    'HK50.cash': {
        'risk_pct': 0.0004,
        'portfolio': ['ALL_ICHI_TK'],
    },
    'UK100.cash': {
        'risk_pct': 0.0004,
        'portfolio': ['ALL_HAMMER', 'ALL_LR_BREAK', 'TOK_TRIX'],
    },
    'US2000.cash': {
        'risk_pct': 0.0004,
        'portfolio': ['ALL_MSTAR'],
    },
    'XAGUSD': {
        'risk_pct': 0.0004,
        'portfolio': ['ALL_NR4', 'TOK_TRIX', 'ALL_AROON_CROSS', 'ALL_ADX_FAST'],
    },
}

# XAGUSD desactive: cout 0.01 lot $21.92 > target $18.32 a 0.04% risk
# XAUUSD reactive: $14 < $18.32 OK
LIVE_INSTRUMENTS = [k for k in ALL_INSTRUMENTS.keys() if k != 'XAGUSD']
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
