"""
Config crypto -- find_winners 1h v1 (2026-05-10).
Source: Binance Futures USDT-M perps (top 16 market cap CoinGecko).
Lookback 2 ans (sf HYPE/TON: full disponible).
Schema: ALL_INSTRUMENTS[sym][tf] = {'risk_pct': ..., 'portfolio': [...]}

Pipeline find_winners:
- 1h: n>=80, lookback 2y
- Filtres: avg_R>=0.05, avg_R_trim>0, median_R>0, OS<30%, M+>=7/12, h1>0, h2>0
- TPSL only (TRAIL/BE_TP retires 2026-05-10)
"""
BROKER = 'crypto'

ALL_INSTRUMENTS = {
    'BTCUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_FIB_618', 'ALL_PSAR_EMA', 'ALL_SUPERTREND', 'BOS_FVG']},
    },
    'ETHUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_BB_TIGHT']},
    },
    'BNBUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_TRIX', 'IDX_PREV_HL']},
    },
    'SOLUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_KB_SQUEEZE']},
    },
    'DOGEUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS']},
    },
    'HYPEUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_DOJI_REV', 'ALL_RSI_DIV', 'IDX_BB_REV', 'TOK_BIG']},
    },
    'BCHUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14_ZERO', 'ALL_LR_BREAK', 'ALL_MOM_14', 'ALL_TRIX', 'TOK_2BAR', 'TOK_BIG']},
    },
    'LINKUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_3SOLDIERS', 'TOK_BIG']},
    },
    'XMRUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_CMO_14', 'ALL_MACD_DIV', 'IDX_BB_REV', 'TOK_STOCH']},
    },
    'XLMUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_ADX_FAST', 'ALL_KB_SQUEEZE', 'ALL_KC_BRK', 'ALL_PSAR_EMA', 'ALL_SUPERTREND', 'TOK_2BAR']},
    },
    'LTCUSD': {
        '1h': {'risk_pct': 0.005, 'portfolio': ['ALL_MACD_DIV', 'ALL_SUPERTREND']},
    },
}

LIVE_TIMEFRAMES = ['1h']

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())
INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = 0.005
PORTFOLIO = ALL_INSTRUMENTS['BTCUSD']['1h']['portfolio'] if 'BTCUSD' in ALL_INSTRUMENTS else []
