"""
Config Pepperstone multi-TF — compte propre 2026-04-30.
Capital $200, risk 0.5%, server UTC+3.
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}

Pipeline find_winners (cost-r 0.05R applique au strat):
filtres n>=80, avg_R>=0.05, avg_R_trim>0, median_R>0, OS<30%, M+>=7/12, walk-forward halves >0.

20 instruments tradeables (78 strats au total).
Skip 0-strats: CN50, CHINAH, NETH25, SCI25, HSTECH, US400, TWN.
"""
BROKER = 'pepperstone'

ALL_INSTRUMENTS = {
    'AUDUSD': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_CONSEC_REV', 'ALL_ENGULF', 'ALL_FVG_BULL', 'ALL_PIVOT_BRK']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50', 'ALL_HAMMER', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_14_ZERO', 'ALL_CCI_20_ZERO', 'ALL_CMO_14', 'ALL_CMO_14_ZERO', 'ALL_DC10', 'ALL_DC10_EMA', 'ALL_DPO_14', 'ALL_EMA_513', 'ALL_LR_BREAK', 'ALL_MACD_DIV', 'ALL_MACD_FAST_ZERO', 'ALL_MOM_10', 'ALL_MOM_14', 'ALL_PIVOT_BRK', 'ALL_RSI_50', 'AVWAP_RECLAIM', 'IDX_BB_REV', 'TOK_BIG']},
    },
    'EURUSD': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_STD_SIG', 'ALL_WILLR_14', 'TOK_WILLR']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FISHER_9', 'ALL_ICHI_TK', 'ALL_MACD_ADX', 'ALL_MACD_STD_SIG', 'ALL_STOCH_RSI', 'ALL_WILLR_7', 'AVWAP_RECLAIM']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_14', 'ALL_EMA_821', 'ALL_KC_BRK', 'AVWAP_RECLAIM', 'TOK_NR4']},
    },
    'GBPUSD': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_ELDER_BULL']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_FISHER_9', 'AVWAP_RECLAIM']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_MTF_BRK', 'IDX_3SOLDIERS']},
    },
    'USDCAD': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_MACD_DIV', 'ALL_WILLR_14', 'IDX_GAP_CONT', 'TOK_STOCH', 'TOK_TRIX', 'TOK_WILLR']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'ALL_PIVOT_BOUNCE', 'IDX_PREV_HL']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_NR4', 'BOS_FVG', 'IDX_3SOLDIERS', 'TOK_NR4']},
    },
    'USDCHF': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_FIB_618']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ELDER_BULL', 'ALL_MACD_HIST', 'IDX_VWAP_BOUNCE']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_14_ZERO', 'ALL_DPO_14', 'ALL_MACD_DIV', 'ALL_PIVOT_BRK', 'BOS_FVG']},
    },
    'USDJPY': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_MSTAR', 'ALL_PIVOT_BOUNCE', 'TOK_BIG']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_20_ZERO', 'ALL_RSI_EXTREME', 'IDX_RSI_REV', 'IDX_VWAP_BOUNCE', 'TOK_NR4']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_921', 'ALL_MACD_RSI', 'ALL_MACD_STD_SIG', 'BOS_FVG']},
    },
    'AUS200': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_100', 'ALL_CCI_14_ZERO', 'ALL_DPO_14', 'ALL_ELDER_BULL', 'ALL_HMA_CROSS', 'ALL_MACD_FAST_SIG', 'ALL_MACD_HIST', 'ALL_RSI_50', 'ALL_RSI_EXTREME', 'ALL_WILLR_14', 'ALL_WILLR_7', 'IDX_CONSEC_REV', 'IDX_RSI_REV', 'TOK_2BAR', 'TOK_WILLR']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_BB_TIGHT', 'ALL_ELDER_BULL', 'ALL_FISHER_9', 'ALL_MACD_ADX', 'ALL_MACD_DIV', 'ALL_MTF_BRK', 'ALL_NR4', 'ALL_PIVOT_BOUNCE', 'ALL_RSI_DIV', 'ALL_WILLR_14', 'TOK_FISHER']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_INSIDE_BRK', 'ALL_MACD_DIV', 'ALL_RSI_DIV', 'ALL_STOCH_RSI']},
    },
    'EUSTX50': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_DOJI_REV', 'ALL_EMA_921', 'ALL_MACD_HIST']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DOJI_REV', 'ALL_SUPERTREND']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_FVG_BULL', 'ALL_LR_BREAK', 'BOS_FVG']},
    },
    'FRA40': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_NR4']},
    },
    'JPN225': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'ALL_STOCH_OB']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_DIV', 'ALL_MOM_10', 'ALL_STOCH_RSI']},
    },
    'NAS100': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_14_ZERO', 'ALL_EMA_821', 'ALL_LR_BREAK', 'ALL_MACD_STD_SIG', 'ALL_NR4']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_EMA_921', 'ALL_KC_BRK', 'ALL_STOCH_OB']},
    },
    'UK100': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_CMO_14', 'ALL_CMO_9', 'ALL_DOJI_REV', 'ALL_ELDER_BULL', 'ALL_MSTAR', 'ALL_NR4', 'ALL_STOCH_RSI', 'TOK_NR4']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14_ZERO', 'ALL_MOM_14', 'ALL_MTF_BRK', 'IDX_CONSEC_REV']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_BB_TIGHT', 'ALL_ENGULF', 'ALL_HAMMER', 'TOK_NR4']},
    },
    'US30': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_MSTAR', 'ALL_NR4', 'TOK_NR4']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_DIV', 'ALL_NR4', 'ALL_PIVOT_BOUNCE', 'ALL_PSAR_EMA', 'IDX_PREV_HL', 'TOK_NR4']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_AROON_CROSS', 'ALL_CMO_14_ZERO', 'ALL_DPO_14', 'ALL_HAMMER', 'ALL_LR_BREAK', 'ALL_MOM_10', 'ALL_MOM_14', 'IDX_3SOLDIERS']},
    },
    'US500': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_DC10', 'ALL_ENGULF', 'ALL_STOCH_OB', 'BOS_FVG', 'IDX_PREV_HL']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS', 'ALL_HAMMER', 'ALL_HMA_CROSS', 'ALL_PIVOT_BOUNCE']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ENGULF', 'ALL_STOCH_OB']},
    },
    'GER40': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_14_ZERO', 'ALL_EMA_513', 'ALL_EMA_821', 'ALL_MACD_FAST_ZERO', 'ALL_MOM_14', 'ALL_MTF_BRK']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_CMO_9', 'ALL_CONSEC_REV', 'ALL_INSIDE_BRK', 'ALL_KC_BRK', 'ALL_MACD_ADX', 'ALL_PSAR_EMA', 'ALL_RSI_DIV', 'ALL_WILLR_7', 'BOS_FVG', 'IDX_CONSEC_REV', 'TOK_FISHER']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_LR_BREAK', 'ALL_MACD_RSI']},
    },
    'SPA35': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_ICHI_TK']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ELDER_BULL', 'ALL_HMA_CROSS']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_FVG_BULL']},
    },
    'HK50': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'IDX_ORB30']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'ALL_DPO_14', 'ALL_FVG_BULL', 'ALL_NR4', 'BOS_FVG', 'IDX_3SOLDIERS']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_AROON_CROSS', 'ALL_CCI_100', 'ALL_CMO_14', 'ALL_MACD_DIV', 'ALL_MOM_10', 'ALL_WILLR_14']},
    },
    'US2000': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_ICHI_TK', 'IDX_VWAP_BOUNCE']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_100', 'ALL_EMA_921', 'ALL_ENGULF', 'ALL_MACD_DIV', 'ALL_RSI_50', 'ALL_RSI_DIV', 'ALL_WILLR_14', 'ALL_WILLR_7']},
    },
    'CA60': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50', 'ALL_FVG_BULL', 'ALL_HAMMER']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_NR4']},
    },
    'SWI20': {
        '15m': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_HIST', 'ALL_STOCH_OB']},
        '1h': {'risk_pct': 0.005, 'portfolio': ['IDX_3SOLDIERS']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_WILLR_14']},
    },
    'CN50': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_9', 'ALL_ELDER_BULL']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_PIVOT_BRK', 'ALL_TRIX', 'TOK_FISHER']},
    },
    'CHINAH': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_DC50', 'ALL_KC_BRK', 'ALL_MACD_RSI', 'BOS_FVG', 'IDX_CONSEC_REV', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CMO_14', 'ALL_DOJI_REV', 'ALL_ENGULF', 'ALL_RSI_50', 'TOK_BIG']},
    },
    'NETH25': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC50']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_KC_BRK']},
    },
    'SCI25': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_RSI', 'ALL_PSAR_EMA', 'TOK_TRIX']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_KC_BRK', 'ALL_RSI_50', 'ALL_WILLR_7', 'IDX_PREV_HL']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['AUS200']['15m']['portfolio']
