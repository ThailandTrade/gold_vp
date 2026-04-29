"""
Config Pepperstone — compte propre 2026-04-29
Capital $200, risk 0.5%, pas de DD max, server UTC+3.
Optim: beam search + reverse cleanup, cost-r 0.05R, no LON/NY strats, no SHORT/LONG conflict filter.

20/22 instruments tradeables (EURUSD et CN50 exclus = 0 strat robuste).
"""
BROKER = 'pepperstone'

ALL_INSTRUMENTS = {
    # ==== FOREX ====
    'GBPUSD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ELDER_BULL'],
        # n=299 PF=1.13 WR=86% DD=-5.8% Rend=+6% M+=7/12
    },
    'AUDUSD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_MACD_HIST', 'ALL_FVG_BULL', 'ALL_CMO_9'],
        # n=736 PF=1.30 WR=65% DD=-9.7% Rend=+88% M+=9/13
    },
    'USDCAD': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_STOCH_PIVOT', 'IDX_GAP_CONT', 'ALL_ELDER_BEAR', 'TOK_STOCH'],
        # n=953 PF=1.19 WR=74% DD=-11.0% Rend=+59% M+=8/12
    },
    'USDCHF': {
        'risk_pct': 0.005,
        'portfolio': ['IDX_BB_REV', 'TOK_NR4', 'ALL_FIB_618', 'ALL_RSI_EXTREME', 'TOK_TRIX'],
        # n=864 PF=1.23 WR=66% DD=-9.1% Rend=+84% M+=9/12
    },
    'USDJPY': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_MSTAR', 'ALL_ENGULF'],
        # n=340 PF=1.22 WR=60% DD=-7.0% Rend=+37% M+=9/12
    },
    # ==== US INDICES (1 seul pour eviter sur-exposition correlee) ====
    'NAS100': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_AROON_CROSS', 'ALL_DC10_EMA', 'ALL_EMA_821', 'ALL_MACD_RSI',
                      'ALL_LR_BREAK', 'ALL_EMA_921', 'ALL_ICHI_TK'],
        # beam_7: n=1390 PF=1.32 WR=69% DD=-11.5% Rend=+345% M+=12/12
    },
    # Skip 2026-04-29: US500 / US30 / US2000 (correlation 0.7-0.95 avec NAS100, sur-exposition US)
    # ==== ASIA ====
    'JPN225': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_ENGULF', 'IDX_3SOLDIERS'],
        # n=508 PF=1.16 WR=67% DD=-8.4% Rend=+34% M+=7/12
    },
    'AUS200': {
        'risk_pct': 0.005,
        'portfolio': ['TOK_2BAR', 'ALL_DPO_14', 'ALL_MSTAR', 'ALL_PIVOT_BOUNCE', 'ALL_MOM_10'],
        # n=922 PF=1.29 WR=69% DD=-7.3% Rend=+133% M+=12/12 ⭐
    },
    'CHINAH': {
        'risk_pct': 0.005,
        'portfolio': ['IDX_VWAP_BOUNCE', 'ALL_KB_SQUEEZE', 'ALL_STOCH_OB'],
        # n=388 PF=1.28 WR=73% DD=-9.2% Rend=+32% M+=10/12
    },
    'HK50': {
        'risk_pct': 0.005,
        'portfolio': ['IDX_VWAP_BOUNCE', 'IDX_3SOLDIERS', 'ALL_KB_SQUEEZE'],
        # n=424 PF=1.34 WR=66% DD=-8.3% Rend=+73% M+=9/12
    },
    # ==== EUROPE ====
    'GER40': {
        'risk_pct': 0.005,
        'portfolio': ['TOK_FISHER', 'ALL_EMA_513', 'ALL_FISHER_9', 'ALL_MACD_HIST',
                      'ALL_HMA_CROSS', 'ALL_LR_BREAK', 'ALL_MACD_FAST_ZERO'],
        # n=1262 PF=1.25 WR=69% DD=-16.0% Rend=+133% M+=12/12 ⭐
    },
    'EUSTX50': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_PSAR_EMA', 'ALL_ICHI_TK', 'ALL_PIVOT_BOUNCE', 'ALL_FISHER_9',
                      'ALL_MACD_HIST', 'ALL_KC_BRK', 'ALL_SUPERTREND', 'ALL_DOJI_REV'],
        # n=1293 PF=1.28 WR=70% DD=-14.5% Rend=+164% M+=9/12
    },
    'UK100': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_DOJI_REV', 'TOK_NR4', 'ALL_CMO_14', 'ALL_MSTAR'],
        # n=725 PF=1.20 WR=82% DD=-5.8% Rend=+28% M+=9/12
    },
    'SCI25': {
        'risk_pct': 0.005,
        'portfolio': ['IDX_PREV_HL'],
        # n=158 PF=1.32 WR=68% DD=-5.9% Rend=+12% M+=7/12
    },
    'FRA40': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_STOCH_OB'],
        # n=238 PF=1.21 WR=58% DD=-13.0% Rend=+25% M+=9/12
    },
    'NETH25': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_FISHER_9'],
        # n=252 PF=1.21 WR=60% DD=-9.0% Rend=+13% M+=8/12
    },
    'SPA35': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_CCI_100', 'ALL_PSAR_EMA', 'ALL_ELDER_BULL'],
        # n=535 PF=1.21 WR=62% DD=-10.0% Rend=+61% M+=10/12
    },
    'SWI20': {
        'risk_pct': 0.005,
        'portfolio': ['ALL_TRIX', 'ALL_CMO_9'],
        # n=457 PF=1.26 WR=70% DD=-8.8% Rend=+38% M+=8/12
    },
    # Skip: EURUSD (cleanup vide), CN50 (0 strat robuste)
}

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['AUS200']['portfolio']
