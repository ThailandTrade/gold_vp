"""
Config 5ers — Multi-instrument (re-optimise 2026-03-30 close-only, marge>=8%)
Max DD 5ers: 4% challenge
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
REGLE: Marge WR >= 8% obligatoire (WR_reel - WR_breakeven)
"""
BROKER = '5ers'

# Tous les instruments optimises (pour backtest)
ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_VWAP_BOUNCE',   # PF 16 — score 0.94
            'PO3_SWEEP',
            'D8',
            'ALL_PIVOT_BRK',
            'ALL_FIB_618',
            'ALL_DC10',
            'ALL_FVG_BULL',
            'TOK_FISHER',
            'IDX_NR4',
            'ALL_NR4',
            'ALL_ELDER_BULL',
            'ALL_BB_TIGHT',
            'IDX_TREND_DAY',
            'IDX_ORB30',
            'ALL_AROON_CROSS',
            'ALL_STOCH_OB',
        ],
        # PF 16: PF 1.43 | WR 70% | DD -1.1% | Rend +20% | 13/13
    },
    'JPN225': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_FIB_618',       # PF 5 — score 0.52
            'D8',
            'TOK_NR4',
            'LON_DC10_MOM',
            'LON_DC10',
        ],
        # PF 5: PF 1.56 | WR 77% | DD -0.5% | Rend +7% | 13/13
    },
    'DAX40': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_FVG_BULL',      # Calmar 15 — score 2.04
            'ALL_STOCH_OB',
            'ALL_RSI_50',
            'IDX_ENGULF',
            'ALL_MSTAR',
            'ALL_ELDER_BULL',
            'ALL_RSI_EXTREME',
            'ALL_MACD_HIST',
            'IDX_TREND_DAY',
            'IDX_RSI_REV',
            'ALL_ENGULF',
            'ALL_FIB_618',
            'ALL_DC50',
            'LON_STOCH',
            'TOK_WILLR',
        ],
        # Calmar 15: PF 1.66 | WR 69% | DD -0.9% | Rend +36% | 12/13
    },
    'NAS100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',                # Calmar 7 — score 0.52
            'ALL_ADX_RSI50',
            'TOK_NR4',
            'ALL_SUPERTREND',
            'LON_STOCH',
            'ALL_RSI_50',
            'ALL_PSAR_EMA',
        ],
        # Calmar 7: PF 1.45 | WR 68% | DD -1.0% | Rend +11% | 12/13
    },
    'SP500': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_CONSEC_REV',    # Calmar 5 — score 0.56
            'ALL_SUPERTREND',
            'ALL_RSI_EXTREME',
            'ALL_PSAR_EMA',
            'IDX_RSI_REV',
        ],
        # Calmar 5: PF 1.53 | WR 69% | DD -0.8% | Rend +10% | 12/13
    },
    'UK100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',    # Calmar 4 — score 0.65
            'NY_HMA_CROSS',
            'NY_ELDER',
            'IDX_LATE_REV',
        ],
        # Calmar 4: PF 1.63 | WR 68% | DD -0.6% | Rend +10% | 12/13
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
