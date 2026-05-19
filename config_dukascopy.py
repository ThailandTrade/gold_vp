"""
Config Dukascopy 4h -- arsenal swing (strats_swing.py) trained 2021-2025.
Source: find_winners_swing 2026-05-19, filtres n>=100 PF>=1.20 Sharpe>=0.80.
"""
BROKER = 'dukascopy'

ALL_INSTRUMENTS = {
    'EURJPY': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['B2_MONTHLY_HL']},
    },
    'EURGBP': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['A9_LR_SLOPE_50', 'D3_ENGULF_WHL']},
    },
    'XAUUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['B6_KC_BRK_50']},
    },
    'JP225': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['A5_TSMOM_3M']},
    },
    'UK100': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['D4_PIN_LEVEL']},
    },
    'US30': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['B6_KC_BRK_50']},
    },
}

LIVE_TIMEFRAMES = ['4h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = next(iter(ALL_INSTRUMENTS.values()))['4h']['portfolio']
