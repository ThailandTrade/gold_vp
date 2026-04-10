"""
Config ICM 15m — 12 instruments (2026-04-10, sim_exit unifie, margin 5%)
Compte personnel (pas de contrainte propfirm DD).
"""
BROKER = 'icm'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_MACD_RSI','IDX_TREND_DAY','IDX_PREV_HL','ALL_KC_BRK','ALL_PSAR_EMA',
            'ALL_MACD_FAST_SIG','LON_STOCH','IDX_VWAP_BOUNCE','IDX_KC_BRK','ALL_3SOLDIERS',
            'ALL_SUPERTREND','ALL_CMO_14','IDX_3SOLDIERS','ALL_CMO_9','ALL_FVG_BULL',
        ],
        # Sharpe 15: PF 1.54 | WR 75% | DD -0.7% | Rend +19% | 13/13
    },
    'US500': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_EMA_921','D8','ALL_EMA_821','ALL_KB_SQUEEZE','ALL_PIVOT_BRK',
            'ALL_FIB_618','TOK_BIG',
        ],
        # PF*WR 7: PF 1.73 | WR 75% | DD -0.9% | Rend +10% | 13/13
    },
    'USTEC': {
        'risk_pct': 0.0001,
        'portfolio': [
            'D8','ALL_EMA_921','ALL_ICHI_TK','ALL_ENGULF','ALL_MSTAR',
        ],
        # PF 5: PF 1.77 | WR 83% | DD -0.5% | Rend +5% | 13/13
    },
    'DE40': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_MSTAR','ALL_CCI_100','ALL_TRIX','ALL_KB_SQUEEZE','ALL_RSI_50','TOK_BIG',
        ],
        # Calmar 6: PF 1.51 | WR 65% | DD -0.7% | Rend +9% | 12/13
    },
    'JP225': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_PSAR_EMA','ALL_STOCH_PIVOT','ALL_SUPERTREND',
        ],
        # PF 3: PF 2.01 | WR 79% | DD -0.5% | Rend +5% | 13/13
    },
    'AUS200': {
        'risk_pct': 0.0001,
        'portfolio': [
            'D8','TOK_2BAR','ALL_FVG_BULL','ALL_FIB_618','ALL_CCI_20_ZERO',
            'ALL_MACD_ADX','ALL_ADX_FAST','ALL_MACD_STD_SIG',
        ],
        # Calmar 8: PF 1.53 | WR 78% | DD -0.6% | Rend +8% | 13/13
    },
    'EURUSD': {
        'risk_pct': 0.0001,
        'portfolio': [
            'D8','ALL_MACD_ADX',
        ],
        # Calmar 2: PF 1.78 | WR 84% | DD -0.2% | Rend +2% | 13/13
    },
    'GBPUSD': {
        'risk_pct': 0.0001,
        'portfolio': [
            'ALL_CONSEC_REV','ALL_AROON_CROSS','ALL_FVG_BULL',
        ],
        # Calmar 3: PF 1.59 | WR 74% | DD -0.4% | Rend +6% | 11/13
    },
    'AUDUSD': {
        'risk_pct': 0.0001,
        'portfolio': [
            'NY_ELDER','ALL_CONSEC_REV','ALL_ELDER_BULL','ALL_CMO_14',
        ],
        # Calmar 4: PF 1.41 | WR 74% | DD -0.8% | Rend +5% | 12/13
    },
    'USDCAD': {
        'risk_pct': 0.0001,
        'portfolio': [
            'NY_HMA_CROSS','ALL_MSTAR',
        ],
        # Calmar 2: PF 1.57 | WR 70% | DD -0.3% | Rend +3% | 12/13
    },
    'USDCHF': {
        'risk_pct': 0.0001,
        'portfolio': [
            'D8','IDX_GAP_CONT','ALL_MACD_HIST','ALL_RSI_EXTREME','ALL_RSI_DIV','IDX_BB_REV',
        ],
        # PF 6: PF 1.76 | WR 78% | DD -0.8% | Rend +10% | 13/13
    },
    'USDJPY': {
        'risk_pct': 0.0001,
        'portfolio': [
            'D8','ALL_ADX_FAST','ALL_PIVOT_BRK',
        ],
        # Calmar 3: PF 1.46 | WR 76% | DD -0.4% | Rend +3% | 11/13
    },
}

# Skip: US30, UK100, F40, STOXX50 (combos trop pauvres)

LIVE_INSTRUMENTS = list(ALL_INSTRUMENTS.keys())  # Tous actifs (live pas encore active)

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
