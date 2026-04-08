"""
Config 5ers — Multi-instrument (re-optimise 2026-04-06, pipeline unifie backtest_engine)
Max DD 5ers: 4% challenge
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
REGLE: Marge WR >= 8% obligatoire (WR_reel - WR_breakeven)
"""
BROKER = '5ers'

# Tous les instruments optimises (pour backtest)
ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0002,
        'portfolio': [
            'IDX_VWAP_BOUNCE','ALL_FVG_BULL','PO3_SWEEP','ALL_PIVOT_BRK',
            'D8','IDX_PREV_HL','ALL_BB_TIGHT','IDX_ORB30',
        ],
        # Sharpe 8: PF 1.50 | WR 70% | DD -0.7% | Rend +11% | 13/13
    },
    'JPN225': {
        'risk_pct': 0.0002,
        'portfolio': [
            'ALL_NR4','ALL_STOCH_PIVOT','TOK_NR4',
        ],
        # Calmar 3: PF 1.59 | WR 79% | DD -0.6% | Rend +5% | 11/13
    },
    'DAX40': {
        'risk_pct': 0.0002,
        'portfolio': [
            'ALL_MACD_HIST','ALL_CCI_20_ZERO','ALL_ELDER_BULL','IDX_TREND_DAY',
            'ALL_FIB_618','ALL_RSI_DIV','TOK_FISHER','TOK_STOCH','IDX_ENGULF',
        ],
        # Sharpe 9: PF 1.70 | WR 74% | DD -0.7% | Rend +19% | 13/13
    },
    'NAS100': {
        'risk_pct': 0.0002,
        'portfolio': [
            'D8','ALL_STOCH_RSI','LON_STOCH','ALL_CCI_100',
            'ALL_WILLR_7','ALL_RSI_50','ALL_DOJI_REV','ALL_ADX_RSI50',
        ],
        # Calmar 8: PF 1.39 | WR 67% | DD -1.4% | Rend +13% | 13/13
    },
    'SP500': {
        'risk_pct': 0.0002,
        'portfolio': [
            'TOK_FISHER','IDX_CONSEC_REV','IDX_RSI_REV',
            'ALL_ENGULF','ALL_HAMMER','ALL_RSI_EXTREME',
        ],
        # Sharpe 6: PF 1.49 | WR 66% | DD -0.8% | Rend +13% | 12/13
    },
    'UK100': {
        'risk_pct': 0.0002,
        'portfolio': [
            'ALL_MACD_HIST','IDX_LATE_REV','ALL_CONSEC_REV',
        ],
        # Calmar 3: PF 1.51 | WR 83% | DD -0.3% | Rend +4% | 12/13
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
