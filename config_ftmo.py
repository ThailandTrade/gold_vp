"""
Config FTMO 15m — REFONTE COST MODEL 2026-04-24
Portfolio refait avec cost-r 0.05R par trade (modele spread+slippage live mesure).
Tous les strats survivants conservees par instrument (pas de greedy filtering).
12 instruments testes -> 4 instruments retenus -> 9 strats au total.
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0004,
        'portfolio': [
            'IDX_TREND_DAY', 'ALL_KC_BRK', 'BOS_FVG',
        ],
        # 3 strats validees cost 0.05R
    },
    'AUS200.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'IDX_BB_REV', 'ALL_PIVOT_BRK', 'TOK_WILLR', 'ALL_CCI_100',
        ],
        # 4 strats validees cost 0.05R
    },
    'US100.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'ALL_MACD_STD_SIG',
        ],
        # 1 strat solo validee
    },
    'UK100.cash': {
        'risk_pct': 0.0004,
        'portfolio': [
            'TOK_TRIX',
        ],
        # 1 strat solo validee (marge +4.4% borderline)
    },
}

LIVE_INSTRUMENTS = ['XAUUSD', 'AUS200.cash', 'US100.cash', 'UK100.cash']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
