"""
Config 5ers 15m — REFONTE ROBUSTESSE 2026-04-22
Portfolio refait avec scoring robustesse (PF_trimmed, outlier penalty, walk-forward).
3 instruments: DAX40 (Europe), NAS100 (USA tech), SP500 (USA broad).
Skippes: XAUUSD (lot min trop gros), US30 (correle SP500), UK100 (marginal), JPN225 (thin).
Max DD 5ers: 4% challenge
"""
BROKER = '5ers'

ALL_INSTRUMENTS = {
    'DAX40': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_MOM_10', 'TOK_NR4', 'ALL_ELDER_BULL', 'TOK_FISHER',
        ],
        # Combo 4: PF 1.36 | WR 78% | DD -0.21% | Rend +1.6% | 12/13
    },
    'NAS100': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_LR_BREAK', 'ALL_MACD_STD_SIG', 'BOS_FVG', 'ALL_MSTAR',
            'ALL_AROON_CROSS', 'ALL_FVG_BULL', 'TOK_2BAR', 'ALL_TRIX',
            'ALL_KC_BRK', 'ALL_NR4', 'ALL_BB_TIGHT',
        ],
        # Combo 11: PF 1.47 | WR 74% | DD -0.35% | Rend +11.8% | 12/13
    },
    'SP500': {
        'risk_pct': 0.0001,
        'portfolio': [
            'TOK_2BAR', 'ALL_MACD_STD_SIG', 'ALL_PIVOT_BOUNCE', 'ALL_MACD_ADX',
            'TOK_TRIX', 'LON_STOCH', 'ALL_TRIX', 'ALL_EMA_921',
            'ALL_DC10_EMA', 'ALL_FVG_BULL',
        ],
        # Combo 10: PF 1.48 | WR 74% | DD -0.27% | Rend +16.1% | 12/13
    },
}

LIVE_INSTRUMENTS = ['DAX40', 'NAS100', 'SP500']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['DAX40']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['DAX40']['portfolio']
