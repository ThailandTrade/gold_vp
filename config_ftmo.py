"""
Config FTMO — Prop firm — Multi-instrument (re-optimise 2026-03-30 close-only, marge>=8%)
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
            'PO3_SWEEP',        # Sharpe 17 — score 0.98
            'ALL_MSTAR',
            'ALL_DC10',
            'IDX_PREV_HL',
            'IDX_VWAP_BOUNCE',
            'ALL_FVG_BULL',
            'D8',
            'ALL_MACD_RSI',
            'IDX_ORB30',
            'ALL_KB_SQUEEZE',
            'ALL_STOCH_OB',
            'IDX_TREND_DAY',
            'ALL_BB_TIGHT',
            'ALL_ELDER_BULL',
            'ALL_HMA_CROSS',
            'TOK_STOCH',
            'ALL_DC10_EMA',
        ],
        # Sharpe 17: PF 1.46 | WR 72% | DD -1.5% | Rend +23% | 13/13
    },
    'GER40.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_FISHER',       # PF 17 — score 2.01
            'ALL_FVG_BULL',
            'ALL_ELDER_BULL',
            'ALL_RSI_50',
            'ALL_MACD_HIST',
            'ALL_MTF_BRK',
            'ALL_FISHER_9',
            'ALL_ADX_FAST',
            'ALL_RSI_DIV',
            'ALL_BB_SQUEEZE',
            'ALL_DC50',
            'ALL_DPO_14',
            'TOK_BIG',
            'ALL_DC10',
            'ALL_DC10_EMA',
            'TOK_TRIX',
            'ALL_WILLR_14',
        ],
        # PF 17: PF 1.75 | WR 72% | DD -1.3% | Rend +40% | 12/13
    },
    'UK100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',   # Calmar 3 — score 0.31
            'NY_HMA_CROSS',
            'IDX_CONSEC_REV',
        ],
        # Calmar 3: PF 1.48 | WR 75% | DD -0.6% | Rend +5% | 12/13
    },
    'US100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',               # Calmar 3 — score 0.20
            'TOK_NR4',
            'ALL_ADX_RSI50',
        ],
        # Calmar 3: PF 1.48 | WR 73% | DD -0.6% | Rend +4% | 11/13
    },
    'US500.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_RSI_EXTREME',  # Sharpe 6 — score 0.80
            'IDX_CONSEC_REV',
            'ALL_SUPERTREND',
            'ALL_FIB_618',
            'TOK_FISHER',
            'ALL_KB_SQUEEZE',
        ],
        # Sharpe 6: PF 1.53 | WR 69% | DD -0.5% | Rend +12% | 13/13
    },
    'US30.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_PREV_HL',      # Calmar 3 — score 0.23
            'ALL_FIB_618',
            'IDX_3SOLDIERS',
        ],
        # Calmar 3: PF 1.45 | WR 71% | DD -0.6% | Rend +5% | 10/13
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
