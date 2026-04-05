"""
Config Crypto — 12 cryptos (optimise 2026-04-04 close-only, marge>=8%)
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
REGLE: Marge WR >= 8% obligatoire (WR_reel - WR_breakeven)
"""
BROKER = 'crypto'  # pkl dans data/crypto/

# Tous les instruments optimises (pour backtest)
ALL_INSTRUMENTS = {
    'BNBUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_CMO_14','ALL_CMO_9','TOK_2BAR','ALL_MACD_ADX',
            'ALL_MACD_STD_SIG','ALL_HMA_CROSS','PO3_SWEEP',
            'ALL_MACD_FAST_ZERO','IDX_BB_REV','ALL_EMA_513',
        ],
        # PF*WR 11: PF 1.55 | WR 78% | DD -0.9% | Rend +19% | 13/13
    },
    'LTCUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'ALL_CONSEC_REV','ALL_DOJI_REV','ALL_RSI_EXTREME','ALL_CMO_9',
            'ALL_CMO_14','ALL_STOCH_PIVOT','IDX_RSI_REV','IDX_CONSEC_REV',
        ],
        # Calmar 8: PF 1.60 | WR 75% | DD -1.4% | Rend +21% | 12/13
    },
    'BCHUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'IDX_PREV_HL','ALL_CMO_14','IDX_GAP_CONT','LON_ASIAN_BRK',
            'ALL_CCI_100','IDX_LATE_REV',
        ],
        # Calmar 6: PF 1.61 | WR 71% | DD -1.0% | Rend +17% | 13/13
    },
    'AVAUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_MACD_DIV','PO3_SWEEP','ALL_KB_SQUEEZE',
            'ALL_RSI_DIV','IDX_PREV_HL',
        ],
        # Calmar 6: PF 1.59 | WR 71% | DD -0.5% | Rend +12% | 13/13
    },
    'NEOUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','IDX_TREND_DAY','ALL_RSI_EXTREME','PO3_SWEEP',
            'ALL_ELDER_BEAR','IDX_RSI_REV',
        ],
        # Calmar 6: PF 1.71 | WR 74% | DD -0.6% | Rend +12% | 12/13
    },
    'BTCUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'PO3_SWEEP','D8','ALL_CCI_100','IDX_CONSEC_REV','ALL_MSTAR',
        ],
        # Calmar 5: PF 1.51 | WR 58% | DD -0.8% | Rend +13% | 12/13
    },
    'XMRUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'TOK_2BAR','ALL_MACD_HIST','IDX_CONSEC_REV',
            'ALL_INSIDE_BRK','ALL_DOJI_REV',
        ],
        # PF 5: PF 1.61 | WR 73% | DD -0.7% | Rend +12% | 12/13
    },
    'DOTUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_MACD_HIST','ALL_STOCH_RSI',
        ],
        # Calmar 3: PF 1.39 | WR 80% | DD -2.2% | Rend +22% | 18/25
    },
    'ADAUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_RSI_DIV',
        ],
        # Calmar 2: PF 1.38 | WR 80% | DD -1.3% | Rend +11% | 19/25
    },
    'DOGEUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'IDX_CONSEC_REV','ALL_CCI_100','D8','ALL_DC50',
        ],
        # Diverse 4: PF 1.49 | WR 69% | DD -1.1% | Rend +8% | 12/13
    },
    'XRPUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'ALL_HAMMER','ALL_CMO_14',
        ],
        # Calmar 2: PF 1.65 | WR 80% | DD -0.3% | Rend +5% | 13/13
    },
    'ETHUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','IDX_TREND_DAY','ALL_STOCH_RSI',
        ],
        # Calmar 3: PF 1.50 | WR 74% | DD -0.4% | Rend +5% | 11/13
    },
    'ETCUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','IDX_BB_REV','ALL_HAMMER','ALL_STOCH_PIVOT',
        ],
        # Calmar 4: PF 1.55 | WR 77% | DD -0.5% | Rend +6% | 12/13
    },
}

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = []

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat
RISK_PCT = 0.002
PORTFOLIO = ALL_INSTRUMENTS['BNBUSD']['portfolio']
