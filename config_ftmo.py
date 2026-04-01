"""
Config FTMO — Prop firm — Multi-instrument (re-optimise 2026-04-01 close-only, marge>=8%, pkl aligne)
Max DD FTMO: 10%
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
REGLE: Marge WR >= 8% obligatoire (WR_reel - WR_breakeven)
"""
BROKER = 'FTMO'

# Tous les instruments optimises (pour backtest)
ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'PO3_SWEEP',        # Calmar 11 — score 0.92
            'ALL_BB_TIGHT',
            'IDX_VWAP_BOUNCE',
            'ALL_WILLR_14',
            'ALL_MSTAR',
            'D8',
            'ALL_STOCH_OB',
            'ALL_MACD_RSI',
            'ALL_DC10',
            'TOK_STOCH',
            'IDX_ORB30',
        ],
        # Calmar 11: PF 1.46 | WR 70% | DD -0.6% | Rend +15% | 12/12
    },
    'GER40.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_FISHER',       # PF 11 — score 2.17
            'ALL_FVG_BULL',
            'ALL_MACD_HIST',
            'ALL_DPO_14',
            'ALL_FISHER_9',
            'ALL_RSI_DIV',
            'ALL_ELDER_BULL',
            'TOK_WILLR',
            'ALL_RSI_50',
            'ALL_MTF_BRK',
            'ALL_FIB_618',
        ],
        # PF 11: PF 1.90 | WR 73% | DD -1.0% | Rend +31% | 12/12
    },
    'UK100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',   # Calmar 3 — score 0.41
            'NY_HMA_CROSS',
            'IDX_TREND_DAY',
        ],
        # Calmar 3: PF 1.49 | WR 74% | DD -0.3% | Rend +5% | 12/12
    },
    'US500.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_RSI_EXTREME',  # Calmar 9 — score 0.98
            'ALL_FISHER_9',
            'ALL_CONSEC_REV',
            'IDX_CONSEC_REV',
            'ALL_KB_SQUEEZE',
            'ALL_PSAR_EMA',
            'ALL_SUPERTREND',
            'TOK_FISHER',
            'ALL_LR_BREAK',
        ],
        # Calmar 9: PF 1.49 | WR 65% | DD -0.9% | Rend +19% | 12/12
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
