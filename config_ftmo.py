"""
Config FTMO 15m — 6 instruments (2026-04-09, sim_exit unifie, margin 5%)
Max DD FTMO: 10%
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0003,
        'portfolio': [
            'ALL_MACD_RSI','IDX_TREND_DAY','ALL_BB_TIGHT','IDX_3SOLDIERS',
            'ALL_ELDER_BEAR','ALL_ROC_ZERO','ALL_KC_BRK','ALL_MACD_HIST','IDX_KC_BRK',
        ],
        # PF 9: PF 1.68 | WR 76% | DD -0.2% | Rend +3% | 13/13
    },
    'GER40.cash': {
        'risk_pct': 0.0003,
        'portfolio': [
            'ALL_MSTAR','ALL_CCI_100','ALL_TRIX','ALL_KB_SQUEEZE',
            'IDX_RSI_REV','ALL_ELDER_BULL','ALL_3SOLDIERS',
        ],
        # Calmar 7: PF 1.53 | WR 74% | DD -0.1% | Rend +2% | 13/13
    },
    'US500.cash': {
        'risk_pct': 0.0003,
        'portfolio': [
            'ALL_MSTAR','TOK_BIG','ALL_EMA_921','IDX_ENGULF',
            'ALL_MTF_BRK','ALL_CMO_14_ZERO','ALL_ELDER_BULL','ALL_MACD_ADX',
        ],
        # Sharpe 8: PF 1.63 | WR 69% | DD -0.2% | Rend +3% | 13/13
    },
    'US100.cash': {
        'risk_pct': 0.0003,
        'portfolio': [
            'D8','ALL_MSTAR','TOK_TRIX','ALL_EMA_821','ALL_ICHI_TK',
            'ALL_DC10_EMA','IDX_3SOLDIERS','ALL_RSI_50',
        ],
        # PF*WR 8: PF 1.58 | WR 72% | DD -0.2% | Rend +2% | 11/13
    },
    'US30.cash': {
        'risk_pct': 0.0003,
        'portfolio': [
            'TOK_2BAR','ALL_KB_SQUEEZE','NY_ELDER','TOK_TRIX',
        ],
        # Calmar 4: PF 1.61 | WR 70% | DD -0.1% | Rend +1% | 13/13
    },
    'JP225.cash': {
        'risk_pct': 0.0003,
        'portfolio': [
            'ALL_PSAR_EMA','ALL_MSTAR',
        ],
        # Calmar 2: PF 1.90 | WR 79% | DD -0.1% | Rend +1% | 11/13
    },
}

# Skip: UK100.cash (9/13, Rend +0%)

LIVE_INSTRUMENTS = ['GER40.cash', 'US500.cash', 'US100.cash', 'US30.cash', 'JP225.cash']  # XAUUSD desactive (lot min trop gros pour petit risque)

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
