"""
Config ICM 15m — BEAM SEARCH 2026-04-25
Methode: beam search top-3 + reverse cleanup iteratif (cost-r 0.05R combo).
13 instruments, 50 strats. Skip F40 et STOXX50 (0 strats robustes).
Compte personnel.
"""
BROKER = 'icm'

ALL_INSTRUMENTS = {
    'EURUSD': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_RSI_50', 'ALL_DOJI_REV', 'ALL_WILLR_14',
            'ALL_STOCH_RSI', 'ALL_MACD_ADX',
        ],
    },
    'GBPUSD': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_WILLR_7', 'ALL_AROON_CROSS', 'ALL_CONSEC_REV',
            'ALL_CMO_14', 'ALL_MACD_HIST',
        ],
    },
    'USDCHF': {
        'risk_pct': 0.01,
        'portfolio': ['IDX_BB_REV', 'ALL_ELDER_BULL'],
    },
    'USDJPY': {
        'risk_pct': 0.01,
        'portfolio': ['LON_ASIAN_BRK'],
    },
    'USDCAD': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_STOCH_PIVOT', 'IDX_GAP_CONT', 'ALL_HAMMER'],
    },
    'AUDUSD': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_PIVOT_BRK', 'ALL_MACD_ADX', 'NY_ELDER'],
    },
    'AUS200': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_HMA_CROSS', 'TOK_WILLR', 'ALL_RSI_EXTREME', 'IDX_BB_REV',
            'ALL_CCI_100', 'ALL_ENGULF', 'ALL_FIB_618',
        ],
    },
    'DE40': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_CCI_100', 'TOK_FISHER', 'TOK_TRIX'],
    },
    'JP225': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_STOCH_RSI', 'ALL_PSAR_EMA', 'ALL_SUPERTREND', 'ALL_3SOLDIERS',
        ],
    },
    'UK100': {
        'risk_pct': 0.01,
        'portfolio': ['TOK_TRIX', 'ALL_EMA_921'],
    },
    'US30': {
        'risk_pct': 0.01,
        'portfolio': [
            'IDX_3SOLDIERS', 'ALL_NR4', 'IDX_PREV_HL', 'ALL_MSTAR', 'TOK_TRIX',
        ],
    },
    'US500': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_MACD_STD_SIG', 'ALL_PIVOT_BOUNCE', 'ALL_MACD_ADX',
        ],
    },
    'USTEC': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_LR_BREAK', 'ALL_DC10_EMA', 'ALL_MACD_STD_SIG',
            'ALL_NR4', 'ALL_ICHI_TK', 'ALL_FVG_BULL',
        ],
    },
    # === Vague 2 — nouveaux instruments 2026-04-26 (validation user: A + ES35 + NETH25) ===
    'SOLUSD': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_STOCH_PIVOT', 'NY_ELDER', 'ALL_ELDER_BEAR', 'ALL_WILLR_7'],
    },
    'ES35': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_CCI_14_ZERO', 'ALL_FIB_618', 'ALL_DOJI_REV'],
    },
    'NETH25': {
        'risk_pct': 0.01,
        'portfolio': ['NY_HMA_CROSS', 'ALL_WILLR_7', 'ALL_STOCH_OB'],
    },
    'SE30': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_INSIDE_BRK', 'ALL_DC50'],
    },
    'SWI20': {
        'risk_pct': 0.01,
        'portfolio': ['ALL_RSI_EXTREME', 'ALL_MACD_HIST', 'IDX_RSI_REV', 'LON_STOCH'],
    },
    'SA40': {
        'risk_pct': 0.01,
        'portfolio': [
            'ALL_ADX_FAST', 'IDX_BB_REV', 'LON_DC10', 'ALL_PIVOT_BRK',
            'ALL_3SOLDIERS', 'ALL_DOJI_REV', 'ALL_FVG_BULL', 'ALL_FISHER_9',
            'ALL_STOCH_OB', 'LON_DC10_MOM', 'IDX_3SOLDIERS', 'ALL_CCI_100',
        ],
    },
    'NOR25': {
        'risk_pct': 0.01,
        'portfolio': ['IDX_3SOLDIERS', 'ALL_3SOLDIERS'],
    },
    # Skip user: ETHUSD, BNBUSD, HK50, IT40, CA60 (PF/DD/M+ insuffisants ou crypto trop volatile)
    # Skip auto: BTCUSD (PF 0.56), US2000 (0 strats robustes)
}

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['EURUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['EURUSD']['portfolio']
