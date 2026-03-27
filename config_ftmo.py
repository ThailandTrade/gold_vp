"""
Config FTMO — Prop firm — Multi-instrument
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'PO3_SWEEP',       # TRAIL 3.0/0.75/0.75  PF=1.81 WR=67%
            'LON_PREV',        # TRAIL 2.0/0.75/0.75  PF=1.50 WR=71%
            'ALL_PSAR_EMA',    # TPSL  3.0/1.50       PF=1.32 WR=72%
            'TOK_2BAR',        # TRAIL 3.0/0.50/0.50  PF=1.44 WR=61%
            'ALL_DC10',        # TRAIL 3.0/0.75/0.75  PF=1.33 WR=66%
        ],
    },
}

# Backward compat
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
