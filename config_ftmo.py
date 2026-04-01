"""
Config FTMO — Prop firm — Multi-instrument (2026-04-01 close-only, marge>=8%, pkl aligne)
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
            'PO3_SWEEP',        # Calmar 17 — score 1.12
            'ALL_BB_TIGHT',
            'IDX_NY_MOM',
            'ALL_MSTAR',
            'ALL_MACD_RSI',
            'D8',
            'ALL_STOCH_OB',
            'IDX_VWAP_BOUNCE',
            'ALL_PIVOT_BRK',
            'ALL_KB_SQUEEZE',
            'ALL_FVG_BULL',
            'TOK_STOCH',
            'IDX_ORB30',
            'IDX_PREV_HL',
            'TOK_TRIX',
            'ALL_DC10',
            'ALL_WILLR_14',
        ],
        # Calmar 17: PF 1.41 | WR 71% | DD -0.8% | Rend +20% | 13/13
    },
    'GER40.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_FISHER',       # PF 13 — score 1.98
            'ALL_FVG_BULL',
            'ALL_MACD_HIST',
            'ALL_DPO_14',
            'ALL_RSI_DIV',
            'ALL_ELDER_BULL',
            'TOK_WILLR',
            'ALL_RSI_50',
            'ALL_MTF_BRK',
            'ALL_FISHER_9',
            'ALL_FIB_618',
            'TOK_BIG',
            'ALL_WILLR_14',
        ],
        # PF 13: PF 1.82 | WR 71% | DD -1.0% | Rend +33% | 12/13
    },
    'US500.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_KB_SQUEEZE',   # Sharpe 8 — score 0.98
            'ALL_CONSEC_REV',
            'ALL_SUPERTREND',
            'ALL_MACD_FAST_SIG',
            'ALL_ELDER_BULL',
            'IDX_CONSEC_REV',
            'TOK_FISHER',
            'ALL_PSAR_EMA',
        ],
        # Sharpe 8: PF 1.52 | WR 69% | DD -0.7% | Rend +16% | 13/13
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
