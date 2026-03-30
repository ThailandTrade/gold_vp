"""
Config ICMarkets — Compte propre — Multi-instrument
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
"""
BROKER = 'ICMarkets'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'PO3_SWEEP',       # TRAIL 3.0/0.75/0.75  PF=2.46 WR=79%
            'ALL_KC_BRK',      # TRAIL 3.0/1.00/0.75  PF=1.20 WR=69%
            'ALL_3SOLDIERS',   # TPSL  3.0/2.00       PF=1.34 WR=67%
            'ALL_FVG_BULL',    # TRAIL 3.0/1.00/0.75  PF=1.63 WR=70%
            'ALL_MACD_RSI',    # TRAIL 1.5/0.50/0.50  PF=1.67 WR=60%
            'TOK_BIG',         # TRAIL 3.0/0.30/0.30  PF=1.57 WR=76%
        ],
        # ex-Calmar 12 sans open (LON_PREV, LON_KZ, TOK_PREVEXT, LON_TOKEND retirees)
        # LON_BIGGAP deja exclue. TOK_2BAR est close, pas open.
    },
}

# Backward compat
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
