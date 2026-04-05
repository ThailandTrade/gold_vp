"""
Config Crypto — 10 cryptos validees (2026-04-05)
Source: optimize_crypto avec forex hours filter + margin WR>=8%, 25 mois
REGLE: PAS de strats open (timing non reproductible en live)
REGLE: Marge WR >= 8% obligatoire (WR_reel - WR_breakeven)
"""
BROKER = 'crypto'  # pkl dans data/crypto/

# Tous les instruments optimises (pour backtest)
ALL_INSTRUMENTS = {
    'BNBUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'ALL_CMO_9','LON_ASIAN_BRK','TOK_2BAR','LON_STOCH','ALL_HMA_CROSS',
            'ALL_MACD_FAST_SIG','TOK_NR4','IDX_BB_REV','NY_HMA_CROSS',
        ],
        # PF 9: PF 1.54 | WR 72% | DD -3.9% | Rend +253% | 25/25
    },
    'BTCUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_AO_SAUCER','PO3_SWEEP',
        ],
        # Calmar 3: PF 1.73 | WR 82% | DD -1.4% | Rend +27% | 23/25
    },
    'ETHUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_ENGULF','IDX_ENGULF',
        ],
        # Calmar 3: PF 1.55 | WR 75% | DD -3.6% | Rend +41% | 21/25
    },
    'BCHUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'ALL_CCI_100','LON_ASIAN_BRK','ALL_MOM_14','ALL_CMO_14_ZERO',
        ],
        # Calmar 4: PF 1.37 | WR 58% | DD -5.7% | Rend +97% | 18/25
    },
    'AVAUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_DOJI_REV','IDX_GAP_FILL','ALL_MACD_HIST',
        ],
        # Calmar 4: PF 1.28 | WR 69% | DD -4.4% | Rend +36% | 19/25
    },
    'NEOUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','ALL_HAMMER','ALL_RSI_DIV','LON_ASIAN_BRK','ALL_MACD_DIV',
        ],
        # Calmar 5: PF 1.41 | WR 68% | DD -3.3% | Rend +74% | 23/25
    },
    'DOGEUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'ALL_AO_SAUCER','ALL_ELDER_BEAR',
        ],
        # Calmar 2: PF 1.45 | WR 77% | DD -2.2% | Rend +27% | 20/25
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
    'AAVEUSD': {
        'risk_pct': 0.002,
        'portfolio': [
            'D8','IDX_NY_MOM',
        ],
        # Calmar 2: PF 1.61 | WR 74% | DD -1.2% | Rend +18% | 21/25
    },
}

# Skip (perfs insuffisantes ou data issues):
# NEAR, ALGO, XRP, PEPE, ZEC, LNK (perfs trop faibles)
# LTC, XMR, ETC, FET, HYPE, SOL, SUI, TAO, UNI (pkl pas exploitable apres filtre margin 8%)

# Instruments actifs en live (subset de ALL_INSTRUMENTS)
LIVE_INSTRUMENTS = []

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

# Backward compat
RISK_PCT = 0.002
PORTFOLIO = ALL_INSTRUMENTS['BNBUSD']['portfolio']
