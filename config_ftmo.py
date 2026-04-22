"""
Config FTMO 15m — REFONTE ROBUSTESSE 2026-04-22
Portfolio refait apres decouverte de l'edge concentre dans la queue droite.
Scoring nouveau: PF_trimmed x WR x (1 - outlier_share), walk-forward 70/30 valide.
3 instruments decorreles: XAUUSD (matiere), GER40 (Europe), US500 (USA).
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_MACD_RSI', 'BOS_FVG', 'ALL_BB_TIGHT', 'ALL_KC_BRK',
        ],
        # Combo 4: PF 1.50 | WR 70% | DD -0.55% | Rend +10.2% | 11/13
    },
    'GER40.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_LR_BREAK', 'ALL_TRIX', 'TOK_TRIX',
        ],
        # Combo 3: PF 1.50 | WR 82% | DD -0.39% | Rend +4.5% | 13/13
    },
    'US500.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'TOK_2BAR', 'ALL_MACD_STD_SIG', 'ALL_PIVOT_BOUNCE', 'ALL_ENGULF',
            'ALL_TRIX', 'ALL_FVG_BULL', 'ALL_MSTAR', 'ALL_CMO_14_ZERO',
            'ALL_AROON_CROSS', 'LON_STOCH',
        ],
        # Combo 10: PF 1.70 | WR 75% | DD -0.39% | Rend +50.2% | 13/13
    },
}

LIVE_INSTRUMENTS = ['XAUUSD', 'GER40.cash', 'US500.cash']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
