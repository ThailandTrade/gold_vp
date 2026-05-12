"""
Config Pepperstone multi-TF -- 15m v4 + 1h v3 + 4h.
Cryptos retirees 2026-05-12 (spreads Standard rhedibitoires, decision 2026-05-09).
Capital $200, risk 0.04%, server UTC+3.
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}

Pipeline find_winners:
- 15m: n>=100, PF>=1.2, lookback 1y glissant (v4 2026-05-11)
- 1h:  n>=60  (v3 2026-04-30)
- 4h:  n>=40
- Filtres communs: avg_R>=0.05, avg_R_trim>0, median_R>0, OS<30%, M+>=7/12, h1>0, h2>0
"""
BROKER = 'pepperstone'

ALL_INSTRUMENTS = {
    'AUDUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'ALL_DOJI_REV', 'ALL_HMA_CROSS', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_14_ZERO', 'ALL_CCI_20_ZERO', 'ALL_CMO_14', 'ALL_CMO_14_ZERO', 'ALL_DC10', 'ALL_DC10_EMA', 'ALL_DPO_14', 'ALL_EMA_513', 'ALL_FVG_BULL', 'ALL_LR_BREAK', 'ALL_MACD_DIV', 'ALL_MACD_FAST_ZERO', 'ALL_MOM_10', 'ALL_MOM_14', 'ALL_PIVOT_BRK', 'ALL_RSI_50', 'ALL_TRIX', 'AVWAP_RECLAIM', 'IDX_3SOLDIERS', 'IDX_BB_REV', 'TOK_BIG']},
    },
    'EURUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FISHER_9', 'ALL_ICHI_TK', 'ALL_MACD_ADX', 'ALL_MACD_RSI', 'ALL_MACD_STD_SIG', 'ALL_STOCH_RSI', 'AVWAP_RECLAIM', 'TOK_FISHER']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_14', 'ALL_EMA_821', 'ALL_KC_BRK', 'ALL_RSI_50', 'AVWAP_RECLAIM', 'TOK_NR4']},
    },
    'GBPUSD': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_ELDER_BULL']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CONSEC_REV', 'ALL_EMA_921', 'ALL_FISHER_9', 'AVWAP_RECLAIM']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_KC_BRK', 'ALL_MTF_BRK']},
    },
    'USDCHF': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_FIB_618']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'IDX_VWAP_BOUNCE']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_14_ZERO', 'ALL_DPO_14', 'ALL_MACD_DIV', 'ALL_PIVOT_BRK', 'BOS_FVG']},
    },
    'USDJPY': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_PIVOT_BOUNCE']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_RSI_EXTREME', 'IDX_RSI_REV', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_921', 'ALL_MACD_RSI', 'ALL_MACD_STD_SIG', 'BOS_FVG']},
    },
    'USDCAD': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_FIB_618', 'ALL_MACD_DIV', 'TOK_STOCH', 'TOK_WILLR']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'ALL_PIVOT_BOUNCE', 'IDX_PREV_HL']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_NR4', 'BOS_FVG', 'IDX_3SOLDIERS', 'TOK_NR4']},
    },
    'AUS200': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_CCI_20_ZERO', 'ALL_CONSEC_REV', 'ALL_DPO_14', 'ALL_MACD_HIST', 'ALL_PSAR_EMA', 'ALL_RSI_EXTREME', 'ALL_WILLR_14', 'ALL_WILLR_7', 'IDX_CONSEC_REV', 'IDX_RSI_REV', 'TOK_2BAR', 'TOK_WILLR']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_BB_TIGHT', 'ALL_ELDER_BULL', 'ALL_FISHER_9', 'ALL_MACD_ADX', 'ALL_MTF_BRK', 'ALL_NR4', 'ALL_PIVOT_BOUNCE', 'ALL_WILLR_14', 'TOK_FISHER', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_INSIDE_BRK', 'ALL_MACD_DIV', 'ALL_RSI_DIV', 'ALL_STOCH_RSI']},
    },
    'EUSTX50': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_DOJI_REV', 'ALL_EMA_921', 'TOK_FISHER']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_PSAR_EMA', 'ALL_SUPERTREND', 'IDX_CONSEC_REV']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_FVG_BULL', 'BOS_FVG']},
    },
    'FRA40': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['IDX_ORB30']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_STD_SIG', 'ALL_NR4', 'ALL_WILLR_14', 'AVWAP_RECLAIM', 'IDX_3SOLDIERS']},
    },
    'JPN225': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_DC50']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'ALL_STOCH_OB', 'BOS_FVG']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_DIV', 'ALL_MOM_10', 'ALL_STOCH_RSI']},
    },
    'NAS100': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_LR_BREAK', 'ALL_MACD_STD_SIG', 'ALL_NR4']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_EMA_921', 'ALL_KC_BRK', 'ALL_STOCH_OB']},
    },
    'UK100': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_CMO_14', 'ALL_CMO_9', 'ALL_HAMMER', 'ALL_KB_SQUEEZE', 'ALL_MSTAR', 'ALL_NR4', 'TOK_NR4']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14_ZERO', 'ALL_ELDER_BEAR', 'ALL_MOM_14', 'IDX_BB_REV', 'IDX_CONSEC_REV']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ENGULF', 'ALL_HAMMER', 'IDX_PREV_HL', 'TOK_NR4']},
    },
    'US30': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_NR4', 'TOK_NR4']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MOM_10', 'ALL_NR4', 'ALL_PIVOT_BOUNCE', 'ALL_TRIX', 'IDX_PREV_HL', 'TOK_NR4']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_AROON_CROSS', 'ALL_CMO_14_ZERO', 'ALL_DPO_14', 'ALL_HAMMER', 'ALL_LR_BREAK', 'ALL_MOM_10', 'ALL_MOM_14', 'IDX_3SOLDIERS']},
    },
    'US500': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_ENGULF', 'BOS_FVG']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ENGULF', 'ALL_STOCH_OB']},
    },
    'GER40': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_EMA_513', 'ALL_EMA_821', 'ALL_MACD_FAST_ZERO']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_CMO_14', 'ALL_CMO_9', 'ALL_CONSEC_REV', 'ALL_INSIDE_BRK', 'ALL_KC_BRK', 'ALL_MACD_ADX', 'ALL_PSAR_EMA', 'ALL_RSI_DIV', 'ALL_WILLR_7']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_LR_BREAK', 'ALL_MACD_RSI']},
    },
    'SPA35': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ELDER_BULL']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_FVG_BULL']},
    },
    'HK50': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['IDX_TREND_DAY']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'ALL_DPO_14', 'ALL_FVG_BULL', 'BOS_FVG', 'IDX_3SOLDIERS']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_AROON_CROSS', 'ALL_CCI_100', 'ALL_CMO_14', 'ALL_MACD_DIV', 'ALL_MOM_10', 'ALL_WILLR_14']},
    },
    'US2000': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_ICHI_TK', 'ALL_MACD_FAST_SIG', 'ALL_STOCH_RSI', 'IDX_VWAP_BOUNCE']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_100', 'ALL_EMA_921', 'ALL_ENGULF', 'ALL_MACD_DIV', 'ALL_RSI_50', 'ALL_RSI_DIV', 'ALL_WILLR_14', 'ALL_WILLR_7']},
    },
    'CA60': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_3SOLDIERS']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50', 'ALL_ELDER_BULL', 'ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL']},
    },
    'SWI20': {
        '15m': {'risk_pct': 0.0004, 'portfolio': ['ALL_STOCH_OB']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['IDX_3SOLDIERS']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_WILLR_14']},
    },
    'CN50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_9', 'ALL_ELDER_BULL']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_PIVOT_BRK', 'TOK_FISHER']},
    },
    'CHINAH': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50', 'ALL_EMA_513', 'ALL_KC_BRK', 'ALL_MACD_FAST_ZERO', 'ALL_MACD_RSI', 'BOS_FVG', 'IDX_CONSEC_REV', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_14', 'ALL_DOJI_REV', 'ALL_ENGULF', 'ALL_RSI_50', 'ALL_WILLR_14', 'TOK_BIG']},
    },
    'SCI25': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_RSI', 'TOK_TRIX']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_KC_BRK', 'ALL_RSI_50', 'IDX_PREV_HL']},
    },
    'NETH25': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_KC_BRK']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['AUS200']['1h']['portfolio'] if 'AUS200' in ALL_INSTRUMENTS and '1h' in ALL_INSTRUMENTS['AUS200'] else []
