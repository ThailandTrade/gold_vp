"""
Config FTMO — Prop firm — Multi-instrument (re-optimise 2026-03-29 avec 110 strats)
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'PO3_SWEEP',       # Diverse 8
            'D8',
            'LON_TOKEND',
            'ALL_SUPERTREND',
            'TOK_WILLR',
            'LON_KZ',
            'LON_PREV',
            'LON_BIGGAP',
        ],
        # Diverse8: PF 1.91 | WR 80% | DD -0.5% @ 0.05% | Rend +12% | 13/13
    },
    'GER40.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_FISHER',      # Sharpe 6
            'ALL_FVG_BULL',
            'ALL_ELDER_BULL',
            'ALL_LR_BREAK',
            'TOK_PREVEXT',
            'ALL_INSIDE_BRK',
        ],
        # Sharpe6: PF 1.98 | WR 76% | DD -0.5% @ 0.05% | Rend +14% | 13/13
    },
    'UK100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',  # Diverse 6
            'IDX_GAP_CONT',
            'LON_GAP',
            'ALL_FIB_618',
            'IDX_TREND_DAY',
            'ALL_ELDER_BULL',
        ],
        # Diverse6: PF 1.43 | WR 71% | DD -0.5% @ 0.05% | Rend +9% | 13/13
    },
    'US100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',              # PF 9
            'TOK_PREVEXT',
            'ALL_MTF_BRK',
            'ALL_ELDER_BULL',
            'ALL_EMA_821',
            'ALL_FIB_618',
            'TOK_WILLR',
            'ALL_FVG_BULL',
            'TOK_STOCH',
        ],
        # PF9: PF 1.59 | WR 78% | DD -0.6% @ 0.05% | Rend +11% | 13/13
    },
    'US500.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_DOJI_REV',    # Calmar 11
            'ALL_FIB_618',
            'TOK_FISHER',
            'ALL_DC50',
            'IDX_CONSEC_REV',
            'ALL_FVG_BULL',
            'IDX_RSI_REV',
            'ALL_SUPERTREND',
            'ALL_LR_BREAK',
            'ALL_ICHI_TK',
            'ALL_KB_SQUEEZE',
        ],
        # Calmar11: PF 1.54 | WR 76% | DD -0.5% @ 0.05% | Rend +16% | 13/13
    },
    'US30.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_PREV_HL',     # PF 10
            'NY_LONEND',
            'TOK_2BAR',
            'ALL_SUPERTREND',
            'ALL_MSTAR',
            'ALL_ELDER_BULL',
            'IDX_3SOLDIERS',
            'TOK_FADE',
            'ALL_MACD_HIST',
            'TOK_PREVEXT',
        ],
        # PF10: PF 1.74 | WR 67% | DD -1.2% @ 0.05% | Rend +23% | 13/13
    },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
