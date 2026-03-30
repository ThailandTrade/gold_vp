"""
Config FTMO — Prop firm — Multi-instrument (re-optimise 2026-03-29 avec 110 strats)
Max DD FTMO: 10%
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
"""
BROKER = 'FTMO'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'PO3_SWEEP',       # ex-Diverse 8 sans open (LON_TOKEND, LON_KZ, LON_PREV, LON_BIGGAP retirees)
            'D8',
            'ALL_SUPERTREND',
            'TOK_WILLR',
        ],
        # Sans open: 4 strats
    },
    'GER40.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'TOK_FISHER',      # ex-Sharpe 6 sans open (TOK_PREVEXT retiree)
            'ALL_FVG_BULL',
            'ALL_ELDER_BULL',
            'ALL_LR_BREAK',
            'ALL_INSIDE_BRK',
        ],
        # Sans open: 5 strats
    },
    'UK100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',  # ex-Diverse 6 sans open (LON_GAP retiree)
            'IDX_GAP_CONT',
            'ALL_FIB_618',
            'IDX_TREND_DAY',
            'ALL_ELDER_BULL',
        ],
        # Sans open: 5 strats
    },
    'US100.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',              # ex-PF 9 sans open (TOK_PREVEXT retiree)
            'ALL_MTF_BRK',
            'ALL_ELDER_BULL',
            'ALL_EMA_821',
            'ALL_FIB_618',
            'TOK_WILLR',
            'ALL_FVG_BULL',
            'TOK_STOCH',
        ],
        # Sans open: 8 strats
    },
    'US500.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_DOJI_REV',    # Calmar 11 — aucune open strat, inchange
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
        # Inchange: 11 strats (0 open)
    },
    'US30.cash': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_PREV_HL',     # ex-PF 10 sans open (NY_LONEND, TOK_FADE, TOK_PREVEXT retirees)
            'ALL_SUPERTREND',
            'ALL_MSTAR',
            'ALL_ELDER_BULL',
            'IDX_3SOLDIERS',
            'ALL_MACD_HIST',
        ],
        # Sans open: 6 strats (TOK_2BAR est close, pas open)
    },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
