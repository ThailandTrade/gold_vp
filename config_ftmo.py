"""
Config FTMO — Prop firm — Multi-instrument (optimise 2026-03-28)
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'PO3_SWEEP',       # Diverse 9 — valide 2026-03-28
            'D8',
            'LON_TOKEND',
            'ALL_PSAR_EMA',
            'TOK_WILLR',
            'LON_KZ',
            'TOK_PREVEXT',
            'LON_PREV',
            'LON_BIGGAP',
        ],
        # Diverse9: PF 1.92 | WR 79% | DD -0.6% @ 0.05% | Rend +13% | 13/13
    },
    'GER40.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_FISHER',      # PF*WR 7 — valide 2026-03-28
            'TOK_PREVEXT',
            'ALL_RSI_50',
            'TOK_FADE',
            'ALL_MACD_HIST',
            'ALL_BB_TIGHT',
            'ALL_HMA_CROSS',
        ],
        # PF*WR7: PF 2.16 | WR 79% | DD -0.5% @ 0.05% | Rend +15% | 13/13
    },
    'UK100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',  # Calmar 6 — valide 2026-03-28
            'IDX_GAP_CONT',
            'IDX_CONSEC_REV',
            'IDX_TREND_DAY',
            'ALL_FIB_618',
            'LON_GAP',
        ],
        # Calmar6: PF 1.44 | WR 71% | DD -0.6% @ 0.05% | Rend +10% | 13/13
    },
    'US100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',              # Calmar 5 — valide 2026-03-28
            'ALL_MACD_HIST',
            'ALL_FIB_618',
            'TOK_MACD_MED',
            'ALL_FVG_BULL',
        ],
        # Calmar5: PF 1.52 | WR 73% | DD -0.4% @ 0.05% | Rend +7% | 13/13
    },
    'US500.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_DOJI_REV',    # PF 5 — valide 2026-03-28
            'IDX_CONSEC_REV',
            'ALL_FIB_618',
            'LON_PREV',
            'ALL_CONSEC_REV',
        ],
        # PF5: PF 1.55 | WR 79% | DD -0.5% @ 0.05% | Rend +8% | 13/13
    },
    'US30.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_PREV_HL',     # PF 12 — valide 2026-03-28
            'NY_LONEND',
            'TOK_2BAR',
            'ALL_PSAR_EMA',
            'ALL_MSTAR',
            'IDX_3SOLDIERS',
            'ALL_FIB_618',
            'ALL_MACD_HIST',
            'TOK_FADE',
            'TOK_PREVEXT',
            'ALL_RSI_DIV',
            'ALL_NR4',
        ],
        # PF12: PF 1.68 | WR 64% | DD -1.0% @ 0.05% | Rend +30% | 13/13
    },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
