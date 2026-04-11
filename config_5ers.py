"""
Config 5ers 15m — 4 instruments (2026-04-09, sim_exit unifie, margin 5%)
Max DD 5ers: 4% challenge
"""
BROKER = '5ers'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0002,
        'portfolio': [
            'ALL_PIVOT_BRK','ALL_MACD_RSI','IDX_TREND_DAY','IDX_3SOLDIERS',
            'IDX_KC_BRK','ALL_MACD_HIST','ALL_BB_TIGHT','ALL_ELDER_BEAR',
            'ALL_SUPERTREND','ALL_KC_BRK','TOK_STOCH','IDX_VWAP_BOUNCE','ALL_FVG_BULL',
        ],
        # Calmar 13: PF 1.71 | WR 78% | DD -0.2% | Rend +4% | 13/13
    },
    'DAX40': {
        'risk_pct': 0.0002,
        'portfolio': [
            'ALL_MSTAR','ALL_TRIX',
        ],
        # Calmar 2: PF 1.75 | WR 75% | DD -0.1% | Rend +1% | 12/13
    },
    'NAS100': {
        'risk_pct': 0.0002,
        'portfolio': [
            'D8','ALL_EMA_921','ALL_ICHI_TK','ALL_DC10_EMA','ALL_CMO_9',
        ],
        # Calmar 5: PF 1.51 | WR 73% | DD -0.1% | Rend +1% | 13/13
    },
    'SP500': {
        'risk_pct': 0.0002,
        'portfolio': [
            'TOK_BIG','ALL_EMA_921','ALL_MSTAR','ALL_ELDER_BULL',
        ],
        # Calmar 4: PF 1.85 | WR 74% | DD -0.1% | Rend +1% | 12/13
    },
}

# Skip: JPN225 (+0%, 260 trades), UK100 (+0%, 430 trades)

LIVE_INSTRUMENTS = ['DAX40', 'NAS100', 'SP500']  # XAUUSD desactive (lot min trop gros pour petit risque)

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
