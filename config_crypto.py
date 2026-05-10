"""
Config crypto -- find_winners 1h v1 (2026-05-10) + 4h v1 (2026-05-10).
Source: Binance Futures USDT-M perps (top 16 market cap CoinGecko).
Lookback: 2y pour 1h, 4y pour 4h (sf cryptos recentes: full disponible).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}

Pipeline find_winners:
- 1h: n>=80, lookback 2y
- 1d: n>=80, lookback full (~5+ ans)
- Filtres: avg_R>=0.05, avg_R_trim>0, median_R>0, OS<30%, M+>=7/12, h1>0, h2>0
- TPSL only (TRAIL/BE_TP retires 2026-05-10)
- Sunday inclus (crypto 24/7)
"""
BROKER = 'crypto'

ALL_INSTRUMENTS = {
    'BTCUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FIB_618', 'ALL_PSAR_EMA', 'ALL_SUPERTREND']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_BB_TIGHT', 'ALL_DC10', 'ALL_DC10_EMA', 'ALL_KC_BRK', 'ALL_MACD_RSI', 'ALL_MTF_BRK', 'IDX_PREV_HL']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_STOCH_OB', 'TOK_STOCH']},
    },
    'ETHUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_LR_BREAK', 'ALL_MACD_DIV', 'ALL_MACD_STD_SIG', 'ALL_TRIX']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_ENGULF', 'IDX_3SOLDIERS']},
    },
    'BNBUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_PIVOT_BRK']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_DC10', 'ALL_DC10_EMA', 'ALL_FVG_BULL', 'ALL_HMA_CROSS', 'ALL_LR_BREAK', 'ALL_STOCH_OB', 'BOS_FVG', 'TOK_STOCH']},
    },
    'SOLUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_513', 'ALL_MACD_FAST_ZERO', 'ALL_MACD_STD_SIG', 'TOK_STOCH']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_CCI_20_ZERO', 'ALL_HMA_CROSS', 'BOS_FVG', 'IDX_3SOLDIERS']},
    },
    'DOGEUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ENGULF', 'ALL_PIVOT_BRK']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_NR4', 'TOK_NR4', 'TOK_STOCH']},
    },
    'HYPEUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['TOK_BIG']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_DPO_14']},
    },
    'BCHUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['TOK_2BAR']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_ELDER_BEAR', 'ALL_INSIDE_BRK', 'IDX_CONSEC_REV']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_ADX', 'ALL_STOCH_OB']},
    },
    'LINKUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS', 'ALL_DC10', 'ALL_DC10_EMA', 'AVWAP_RECLAIM', 'TOK_WILLR']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_14_ZERO', 'ALL_CCI_20_ZERO', 'ALL_DOJI_REV', 'ALL_ELDER_BULL', 'ALL_EMA_821', 'ALL_EMA_921', 'ALL_FVG_BULL', 'ALL_MACD_ADX', 'ALL_MACD_RSI']},
    },
    'XMRUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ICHI_TK', 'ALL_TRIX', 'BOS_FVG']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_14_ZERO', 'ALL_CMO_9', 'ALL_TRIX', 'AVWAP_RECLAIM', 'TOK_TRIX']},
    },
    'XLMUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_PSAR_EMA', 'ALL_SUPERTREND', 'TOK_2BAR']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_CMO_14_ZERO', 'ALL_DC10', 'ALL_DC10_EMA', 'ALL_DC50', 'ALL_ICHI_TK', 'ALL_MACD_RSI', 'ALL_MOM_14']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_RSI50', 'ALL_CCI_100', 'ALL_EMA_513', 'ALL_MACD_ADX', 'ALL_MACD_FAST_ZERO', 'ALL_MACD_STD_SIG', 'ALL_RSI_50']},
    },
    'LTCUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'ALL_DOJI_REV', 'ALL_EMA_821', 'ALL_MACD_STD_SIG', 'ALL_STOCH_OB', 'ALL_TRIX', 'AVWAP_RECLAIM', 'IDX_VWAP_BOUNCE']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_100', 'ALL_EMA_513', 'ALL_LR_BREAK', 'ALL_MACD_FAST_ZERO', 'ALL_RSI_DIV', 'ALL_WILLR_7']},
    },
    'XRPUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_DC10', 'ALL_DC10_EMA', 'ALL_EMA_921']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_9', 'ALL_ELDER_BEAR', 'ALL_HAMMER', 'ALL_HMA_CROSS', 'ALL_LR_BREAK', 'ALL_STOCH_OB', 'AVWAP_RECLAIM', 'TOK_STOCH']},
    },
    'ADAUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_20_ZERO', 'ALL_DPO_14', 'ALL_EMA_821', 'ALL_EMA_921', 'IDX_VWAP_BOUNCE']},
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_MACD_ADX', 'ALL_MACD_RSI', 'ALL_NR4', 'TOK_NR4']},
    },
    'TONUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_FVG_BULL', 'ALL_MACD_ADX', 'IDX_VWAP_BOUNCE']},
    },
    'TRXUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14']},
    },
    'ZECUSD': {
        '1d': {'risk_pct': 0.005, 'portfolio': ['ALL_CCI_20_ZERO', 'ALL_CMO_9', 'ALL_STOCH_PIVOT', 'IDX_BB_REV']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['BTCUSD']['1h']['portfolio'] if 'BTCUSD' in ALL_INSTRUMENTS and '1h' in ALL_INSTRUMENTS['BTCUSD'] else []
