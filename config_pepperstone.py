"""
Config Pepperstone — compte propre 2026-04-30
Capital $200, risk 0.5%, server UTC+3.
Pipeline find_winners: cost-r 0.05R applique au strat, exits choisis sous cost,
filtres: n>=80, avg_R>=0.05, avg_R_trim>0, median_R>0, OS<30%, M+>=7/12,
walk-forward halves >0.

20 instruments tradeables (78 strats au total).
Skip 0-strats: CN50, CHINAH, NETH25, SCI25, HSTECH, US400, TWN, EURUSD (anciennement vide, maintenant 3 strats).
"""
BROKER = 'pepperstone'

ALL_INSTRUMENTS = {
    'AUDUSD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_CONSEC_REV', 'ALL_ENGULF', 'ALL_FVG_BULL', 'ALL_PIVOT_BRK'],
    },
    'EURUSD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_MACD_STD_SIG', 'ALL_WILLR_14', 'TOK_WILLR'],
    },
    'GBPUSD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ELDER_BULL'],
    },
    'USDCAD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_CCI_100', 'ALL_MACD_DIV', 'ALL_WILLR_14', 'IDX_GAP_CONT', 'TOK_STOCH', 'TOK_TRIX', 'TOK_WILLR'],
    },
    'USDCHF': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_FIB_618'],
    },
    'USDJPY': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ADX_FAST', 'ALL_MSTAR', 'ALL_PIVOT_BOUNCE', 'TOK_BIG'],
    },
    'AUS200': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_100', 'ALL_CCI_14_ZERO', 'ALL_DPO_14', 'ALL_ELDER_BULL', 'ALL_HMA_CROSS', 'ALL_MACD_FAST_SIG', 'ALL_MACD_HIST', 'ALL_RSI_50', 'ALL_RSI_EXTREME', 'ALL_WILLR_14', 'ALL_WILLR_7', 'IDX_CONSEC_REV', 'IDX_RSI_REV', 'TOK_2BAR', 'TOK_WILLR'],
    },
    'EUSTX50': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_DOJI_REV', 'ALL_EMA_921', 'ALL_MACD_HIST'],
    },
    'FRA40': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_MACD_HIST'],
    },
    'JPN225': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_DC50'],
    },
    'NAS100': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_CCI_14_ZERO', 'ALL_EMA_821', 'ALL_LR_BREAK', 'ALL_MACD_STD_SIG', 'ALL_NR4'],
    },
    'UK100': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_CCI_100', 'ALL_CMO_14', 'ALL_CMO_9', 'ALL_DOJI_REV', 'ALL_ELDER_BULL', 'ALL_MSTAR', 'ALL_NR4', 'ALL_STOCH_RSI', 'TOK_NR4'],
    },
    'US30': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ADX_FAST', 'ALL_MSTAR', 'ALL_NR4', 'TOK_NR4'],
    },
    'US500': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_DC10', 'ALL_ENGULF', 'ALL_STOCH_OB', 'BOS_FVG', 'IDX_PREV_HL'],
    },
    'GER40': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_14_ZERO', 'ALL_EMA_513', 'ALL_EMA_821', 'ALL_MACD_FAST_ZERO', 'ALL_MOM_14', 'ALL_MTF_BRK'],
    },
    'SPA35': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ICHI_TK'],
    },
    'HK50': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_3SOLDIERS', 'IDX_ORB30'],
    },
    'US2000': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_EMA_821'],
    },
    'CA60': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_3SOLDIERS'],
    },
    'SWI20': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_MACD_HIST', 'ALL_STOCH_OB'],
    },
}

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['AUS200']['portfolio']
