"""
Config 5ers — Multi-instrument (re-optimise 2026-03-31 close-only, marge>=8%, pkl aligne)
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
            'IDX_VWAP_BOUNCE',   # Calmar 9 — score 0.75
            'ALL_BB_TIGHT',
            'PO3_SWEEP',
            'ALL_FVG_BULL',
            'TOK_FISHER',
            'D8',
            'ALL_STOCH_OB',
            'ALL_FIB_618',
            'ALL_PIVOT_BRK',
        ],
        # Calmar 9: PF 1.52 | WR 72% | DD -0.8% | Rend +13% | 13/13
    },
    'JPN225': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_FIB_618',       # PF 5 — score 0.52
            'D8',
            'TOK_NR4',
            'LON_DC10',
            'LON_DC10_MOM',
        ],
        # PF 5: PF 1.55 | WR 77% | DD -0.5% | Rend +7% | 13/13
    },
    'DAX40': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_MACD_HIST',     # Sharpe 15 — score 1.84
            'ALL_FIB_618',
            'ALL_ELDER_BULL',
            'IDX_PREV_HL',
            'ALL_RSI_EXTREME',
            'IDX_TREND_DAY',
            'ALL_FVG_BULL',
            'ALL_CONSEC_REV',
            'LON_STOCH',
            'ALL_STOCH_OB',
            'ALL_MSTAR',
            'IDX_RSI_REV',
            'ALL_CMO_9',
            'ALL_KB_SQUEEZE',
            'TOK_WILLR',
        ],
        # Sharpe 15: PF 1.60 | WR 63% | DD -1.2% | Rend +43% | 12/13
    },
    'NAS100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',                # Calmar 7 — score 0.77
            'ALL_SUPERTREND',
            'LON_STOCH',
            'ALL_RSI_50',
            'TOK_NR4',
            'ALL_PSAR_EMA',
            'ALL_ADX_RSI50',
        ],
        # Calmar 7: PF 1.57 | WR 66% | DD -1.0% | Rend +16% | 12/13
    },
    'SP500': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_CONSEC_REV',    # Calmar 4 — score 0.53
            'ALL_SUPERTREND',
            'ALL_RSI_EXTREME',
            'ALL_PSAR_EMA',
        ],
        # Calmar 4: PF 1.53 | WR 69% | DD -0.7% | Rend +8% | 13/13
    },
    'UK100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'NY_HMA_CROSS',      # Calmar 4 — score 0.56
            'ALL_CONSEC_REV',
            'ALL_ELDER_BULL',
            'IDX_LATE_REV',
        ],
        # Calmar 4: PF 1.60 | WR 77% | DD -0.5% | Rend +7% | 12/13
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
