"""
Config crypto -- find_winners 1h v1 (2026-05-10) + 4h v1 (2026-05-10).
Source: Binance Futures USDT-M perps (top 16 market cap CoinGecko).
Lookback: 2y pour 1h, 4y pour 4h (sf cryptos recentes: full disponible).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}

Pipeline find_winners:
- 1h: n>=80, lookback 2y
- 4h: n>=80, lookback 4y
- Filtres: avg_R>=0.05, avg_R_trim>0, median_R>0, OS<30%, M+>=7/12, h1>0, h2>0
- TPSL only (TRAIL/BE_TP retires 2026-05-10)
- Sunday inclus (crypto 24/7)
"""
BROKER = 'crypto'

ALL_INSTRUMENTS = {
    'BTCUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FIB_618', 'ALL_PSAR_EMA', 'ALL_SUPERTREND', 'BOS_FVG']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS', 'ALL_KB_SQUEEZE', 'ALL_MTF_BRK', 'D8']},
    },
    'ETHUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_BB_TIGHT']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_ADX_RSI50', 'ALL_RSI_50', 'TOK_TRIX']},
    },
    'BNBUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_TRIX', 'IDX_PREV_HL']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_DC50', 'D8']},
    },
    'SOLUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_KB_SQUEEZE']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_DPO_14', 'ALL_KC_BRK', 'IDX_VWAP_BOUNCE']},
    },
    'DOGEUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS']},
    },
    'HYPEUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DOJI_REV', 'ALL_RSI_DIV', 'IDX_BB_REV', 'TOK_BIG']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_DPO_14']},
    },
    'BCHUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14_ZERO', 'ALL_LR_BREAK', 'ALL_MOM_14', 'ALL_TRIX', 'TOK_2BAR', 'TOK_BIG']},
    },
    'LINKUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'TOK_BIG']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS', 'ALL_CCI_20_ZERO', 'ALL_CMO_14', 'ALL_EMA_513', 'ALL_MACD_FAST_ZERO', 'ALL_MOM_10', 'D8']},
    },
    'XMRUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_MACD_DIV', 'IDX_BB_REV', 'TOK_STOCH']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ICHI_TK', 'TOK_NR4']},
    },
    'XLMUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_KB_SQUEEZE', 'ALL_KC_BRK', 'ALL_PSAR_EMA', 'ALL_SUPERTREND', 'TOK_2BAR']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_AROON_CROSS', 'ALL_ICHI_TK', 'ALL_STOCH_PIVOT', 'BOS_FVG', 'TOK_TRIX']},
    },
    'LTCUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_DIV', 'ALL_SUPERTREND']},
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'ALL_MACD_DIV', 'ALL_RSI_EXTREME', 'IDX_BB_REV', 'IDX_RSI_REV']},
    },
    'XRPUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_821', 'ALL_ENGULF']},
    },
    'ZECUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_EMA_921', 'D8']},
    },
    'ADAUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_KC_BRK', 'ALL_RSI_EXTREME', 'IDX_RSI_REV']},
    },
    'TONUSD': {
        '4h': {'risk_pct': 0.005, 'portfolio': ['ALL_ELDER_BEAR', 'IDX_VWAP_BOUNCE']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['BTCUSD']['1h']['portfolio'] if 'BTCUSD' in ALL_INSTRUMENTS and '1h' in ALL_INSTRUMENTS['BTCUSD'] else []
