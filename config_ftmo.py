"""
Config FTMO 15m — REDESIGN 2026-04-24
Cost-r applique au COMBO uniquement (pas par strat). Toutes les strats validees
individuellement par pf_trim/median_R/m_neg/test_pf/marge_wr sont conservees.
8 instruments, 68 strats. Skip JP225/EU50/HK50/US2000 (M+ insuffisant).
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0004,
        'portfolio': [
            'IDX_TREND_DAY', 'ALL_KC_BRK', 'BOS_FVG', 'ALL_MACD_RSI', 'ALL_INSIDE_BRK',
        ],
    },
    'GER40.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'TOK_TRIX', 'ALL_CCI_100', 'ALL_TRIX',
        ],
    },
    'US500.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'TOK_2BAR', 'ALL_MACD_STD_SIG', 'ALL_PIVOT_BOUNCE', 'ALL_ENGULF',
            'ALL_FVG_BULL', 'ALL_TRIX', 'TOK_TRIX', 'ALL_AROON_CROSS',
            'LON_STOCH', 'ALL_EMA_921', 'ALL_3SOLDIERS', 'ALL_MACD_ADX',
        ],
    },
    'US100.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_AROON_CROSS', 'ALL_LR_BREAK', 'ALL_MACD_RSI', 'ALL_MSTAR',
            'TOK_2BAR', 'ALL_BB_TIGHT', 'ALL_MACD_ADX',
            'ALL_MACD_STD_SIG', 'ALL_NR4', 'TOK_NR4',
        ],
    },
    'US30.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'TOK_TRIX', 'TOK_NR4', 'ALL_MOM_10', 'ALL_NR4',
        ],
    },
    'AUS200.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_CMO_14', 'ALL_WILLR_14', 'ALL_CCI_20_ZERO', 'ALL_CONSEC_REV',
            'ALL_STOCH_OB', 'TOK_WILLR', 'ALL_MOM_10',
            'ALL_MACD_DIV', 'IDX_3SOLDIERS',
            'ALL_MACD_HIST', 'ALL_CCI_14_ZERO',
            'ALL_HMA_CROSS',
        ],
    },
    'UK100.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_HAMMER', 'TOK_TRIX', 'ALL_LR_BREAK', 'ALL_TRIX',
        ],
    },
    'XAGUSD': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_NR4', 'TOK_NR4', 'ALL_AROON_CROSS', 'TOK_TRIX', 'ALL_ADX_FAST',
        ],
    },
}

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
