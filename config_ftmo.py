"""
Config FTMO — Prop firm — Multi-instrument (re-optimise 2026-04-06, pipeline unifie backtest_engine)
Max DD FTMO: 10%
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
REGLE: Marge WR >= 8% obligatoire (WR_reel - WR_breakeven)
"""
BROKER = 'FTMO'

# Tous les instruments optimises (pour backtest)
ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0001,
        'portfolio': [
            'PO3_SWEEP','ALL_MSTAR','IDX_PREV_HL','ALL_STOCH_OB','ALL_BB_TIGHT',
            'IDX_VWAP_BOUNCE','ALL_FVG_BULL','ALL_KB_SQUEEZE','ALL_MACD_RSI',
        ],
        # Sharpe 9: PF 1.53 | WR 72% | DD -0.9% | Rend +15% | 13/13
    },
    'GER40.cash': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_MACD_HIST','ALL_FIB_618','ALL_RSI_DIV','IDX_ENGULF','TOK_FISHER',
            'ALL_ELDER_BULL','TOK_STOCH','ALL_ENGULF','ALL_MACD_DIV','ALL_PSAR_EMA',
        ],
        # Calmar 10: PF 1.84 | WR 68% | DD -0.7% | Rend +32% | 13/13
    },
    'US500.cash': {
        'risk_pct': 0.0001,
        'portfolio': [
            'TOK_FISHER','ALL_RSI_EXTREME','IDX_CONSEC_REV','ALL_ELDER_BULL',
        ],
        # Calmar 4: PF 1.61 | WR 70% | DD -0.6% | Rend +10% | 12/13
    },
    'US100.cash': {
        'risk_pct': 0.0001,
        'portfolio': [
            'D8','ALL_HMA_CROSS','ALL_STOCH_RSI','LON_STOCH','ALL_ADX_RSI50','ALL_RSI_50',
        ],
        # Calmar 6: PF 1.49 | WR 73% | DD -0.6% | Rend +10% | 13/13
    },
    'US30.cash': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_MACD_HIST','ALL_FIB_618','ALL_MSTAR',
        ],
        # PF 3: PF 1.51 | WR 72% | DD -0.5% | Rend +5% | 13/13
    },
    'JP225.cash': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_FIB_618','IDX_LATE_REV','TOK_NR4',
        ],
        # PF 3: PF 1.78 | WR 76% | DD -0.1% | Rend +1% | 12/13
    },
}

# Skip: UK100.cash (PF 1.47, seulement 10/13 mois)

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = ['XAUUSD', 'GER40.cash', 'US500.cash', 'US100.cash', 'US30.cash', 'JP225.cash']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat: default instrument
RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
