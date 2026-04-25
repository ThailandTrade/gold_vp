"""
Config 5ers 15m — BEAM SEARCH 2026-04-25
Methode: beam search top-3 + reverse cleanup iteratif (cost 0.05R combo).
8 instruments, 28 strats.
Max DD 5ers: 4% challenge
"""
BROKER = '5ers'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0001,
        'portfolio': ['IDX_TREND_DAY', 'ALL_BB_TIGHT'],
    },
    'DAX40': {
        'risk_pct': 0.0001,
        'portfolio': ['ALL_MOM_10', 'ALL_FIB_618', 'ALL_ELDER_BULL'],
    },
    'SP500': {
        'risk_pct': 0.0001,
        'portfolio': [
            'TOK_TRIX', 'ALL_MACD_STD_SIG', 'ALL_PIVOT_BOUNCE',
            'ALL_MACD_ADX', 'ALL_MTF_BRK', 'ALL_TRIX', 'TOK_2BAR',
        ],
    },
    'NAS100': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_AROON_CROSS', 'ALL_LR_BREAK', 'ALL_MACD_STD_SIG',
            'ALL_MSTAR', 'TOK_2BAR',
        ],
    },
    'US30': {
        'risk_pct': 0.0001,
        'portfolio': ['ALL_ADX_FAST', 'TOK_NR4', 'TOK_TRIX'],
    },
    'UK100': {
        'risk_pct': 0.0001,
        'portfolio': ['TOK_TRIX'],
    },
    'JPN225': {
        'risk_pct': 0.0001,
        'portfolio': ['ALL_3SOLDIERS', 'ALL_FVG_BULL', 'TOK_BIG'],
    },
    'XAGUSD': {
        'risk_pct': 0.0001,
        'portfolio': ['ALL_KC_BRK', 'ALL_FVG_BULL', 'TOK_STOCH', 'ALL_STOCH_OB'],
    },
}

# Metaux desactives (XAUUSD/XAGUSD): cout min lot 0.01 depasse le risk target 0.01%
LIVE_INSTRUMENTS = [k for k in ALL_INSTRUMENTS.keys() if k not in ('XAUUSD', 'XAGUSD')]
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
