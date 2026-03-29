"""
Config 5ers — Multi-instrument (re-optimise 2026-03-29 avec 110 strats)
Max DD 5ers: 4% challenge
"""
BROKER = '5ers'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_VWAP_BOUNCE',  # Calmar 19 — score 2.00
            'LON_PREV',
            'ALL_STOCH_OB',
            'LON_KZ',
            'ALL_FIB_618',
            'ALL_MACD_STD_SIG',
            'ALL_PSAR_EMA',
            'TOK_FISHER',
            'ALL_BB_TIGHT',
            'ALL_MSTAR',
            'ALL_SUPERTREND',
            'LON_BIGGAP',
            'PO3_SWEEP',
            'TOK_PREVEXT',
            'LON_TOKEND',
            'IDX_CONSEC_REV',
            'D8',
            'TOK_WILLR',
            'IDX_NR4',
        ],
        # Calmar19: PF 1.62 | WR 79% | DD -0.6% | Rend +24% | 13/13
    },
    'JPN225': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_FIB_618',     # Calmar 21 — score 2.80
            'LON_GAP',
            'ALL_NR4',
            'ALL_STOCH_PIVOT',
            'ALL_MTF_BRK',
            'LON_DC10',
            'ALL_FISHER_9',
            'IDX_GAP_CONT',
            'ALL_MACD_RSI',
            'IDX_LATE_REV',
            'TOK_NR4',
            'ALL_WILLR_14',
            'ALL_PIVOT_BOUNCE',
            'LON_DC10_MOM',
            'ALL_CMO_14',
            'D8',
            'LON_TOKEND',
            'TOK_PREVEXT',
            'NY_LONEND',
            'ALL_STOCH_RSI',
            'ALL_MACD_MED_SIG',
        ],
        # Calmar21: PF 1.67 | WR 75% | DD -0.6% | Rend +37% | 13/13
    },
    'DAX40': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_FVG_BULL',    # PF 17 — score 2.23
            'ALL_STOCH_OB',
            'ALL_CCI_20_ZERO',
            'ALL_MACD_HIST',
            'ALL_ELDER_BULL',
            'ALL_ADX_RSI50',
            'ALL_MACD_STD_SIG',
            'TOK_FADE',
            'ALL_FISHER_9',
            'ALL_INSIDE_BRK',
            'TOK_WILLR',
            'ALL_BB_TIGHT',
            'TOK_BIG',
            'ALL_RSI_DIV',
            'ALL_DC10',
            'ALL_DC10_EMA',
            'TOK_PREVEXT',
        ],
        # PF17: PF 1.84 | WR 75% | DD -1.3% | Rend +40% | 12/13
    },
    # BTCUSD retire — fees/spread trop eleves
    'NAS100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'D8',              # Calmar 19 — score 1.66
            'ALL_HMA_CROSS',
            'ALL_SUPERTREND',
            'TOK_NR4',
            'TOK_FADE',
            'ALL_RSI_50',
            'ALL_PIVOT_BOUNCE',
            'ALL_MSTAR',
            'IDX_PREV_HL',
            'ALL_MACD_HIST',
            'ALL_FVG_BULL',
            'IDX_NY_MOM',
            'ALL_NR4',
            'TOK_PREVEXT',
            'ALL_ELDER_BULL',
            'LON_BIGGAP',
            'ALL_DC50',
            'IDX_TREND_DAY',
            'ALL_STOCH_PIVOT',
        ],
        # Calmar19: PF 1.51 | WR 69% | DD -0.8% | Rend +30% | 13/13
    },
    'SP500': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_DOJI_REV',    # Calmar 16 — score 1.57
            'TOK_FISHER',
            'IDX_CONSEC_REV',
            'ALL_ICHI_TK',
            'ALL_DC50',
            'ALL_RSI_EXTREME',
            'ALL_FVG_BULL',
            'LON_PREV',
            'ALL_3SOLDIERS',
            'ALL_PSAR_EMA',
            'ALL_SUPERTREND',
            'ALL_MACD_HIST',
            'IDX_RSI_REV',
            'ALL_ELDER_BULL',
            'ALL_STOCH_CROSS',
            'ALL_MACD_FAST_SIG',
        ],
        # Calmar16: PF 1.53 | WR 71% | DD -1.0% | Rend +29% | 13/13
    },
    'UK100': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_CONSEC_REV',  # Calmar 14 — score 1.17
            'NY_HMA_CROSS',
            'NY_ELDER',
            'ALL_ELDER_BULL',
            'IDX_TREND_DAY',
            'LON_BIGGAP',
            'IDX_LATE_REV',
            'ALL_MACD_DIV',
            'IDX_CONSEC_REV',
            'LON_GAP',
            'ALL_HAMMER',
            'TOK_NR4',
            'ALL_MSTAR',
            'LON_PREV',
        ],
        # Calmar14: PF 1.46 | WR 73% | DD -0.7% | Rend +20% | 12/13
    },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
