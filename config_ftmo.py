"""
Config FTMO 15m — XAUUSD focus (cleanup-v2 P10)
Portfolio TOP 4 determine par stepwise forward + bootstrap (2026-04-17).

Max DD FTMO: 10%. Backtest TOP 4:
  n=1039  PF=1.55  WR=84%  DD=-0.27%  Rend=+4.62%  Calmar=17.02
  CI 95% bootstrap: [1.27, 1.86]  p(PF<=1) = 0.0%  12/13 mois positifs

Note: les 5 autres instruments (GER40/US500/US100/US30/JP225) ont un edge
valide au niveau portefeuille mais inferieur a XAUUSD. Commentes ici,
peuvent etre reactives plus tard (historique garde pour reference).
"""
BROKER = 'FTMO'

ALL_INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'ALL_MACD_RSI',   # pilier 1 - PF 2.57 seul, CI [1.80, 3.58]
            'TOK_TRIX',       # decorrelation key - mean corr -0.10
            'ALL_CCI_100',    # contribution utile, peu de DD
            'ALL_ADX_FAST',   # ameliore Calmar
        ],
        # TOP 4: PF 1.55 | WR 84% | DD -0.27% | Rend +4.62% | Calmar 17 | 12/13 mois
    },
    # ── DESACTIVES - edges moins robustes, a reconsiderer apres consolidation XAUUSD ──
    # 'GER40.cash': {
    #     'risk_pct': 0.0005,
    #     'portfolio': ['ALL_CCI_100','ALL_TRIX','TOK_TRIX'],
    #     # CI [1.06, 2.29] - ATTENUE
    # },
    # 'US500.cash': {
    #     'risk_pct': 0.0005,
    #     'portfolio': ['ALL_ELDER_BULL','ALL_BB_TIGHT','ALL_DC10_EMA','ALL_EMA_513','ALL_MACD_ADX','IDX_3SOLDIERS'],
    #     # CI [1.08, 1.58] - ATTENUE
    # },
    # 'US100.cash': {
    #     'risk_pct': 0.0005,
    #     'portfolio': ['ALL_EMA_921','ALL_MACD_STD_SIG','ALL_KC_BRK','ALL_ICHI_TK','ALL_CMO_9',
    #                   'ALL_LR_BREAK','ALL_MACD_HIST','ALL_TRIX','IDX_GAP_CONT','IDX_TREND_DAY'],
    #     # CI [1.19, 1.61] - ATTENUE (sous le seuil 1.20 apres retrait IDX_KC_BRK doublon)
    # },
    # 'US30.cash': {
    #     'risk_pct': 0.0005,
    #     'portfolio': ['ALL_RSI_50','ALL_ADX_FAST','ALL_ADX_RSI50','NY_ELDER'],
    #     # CI [1.26, 1.67] - ROBUSTE
    # },
    # 'JP225.cash': {
    #     'risk_pct': 0.0005,
    #     'portfolio': ['ALL_PSAR_EMA','ALL_SUPERTREND','ALL_ICHI_TK'],
    #     # CI [1.31, 2.19] - ROBUSTE (mais PSAR_EMA == SUPERTREND a 97%)
    # },
}

LIVE_INSTRUMENTS = ['XAUUSD']

INSTRUMENTS = {k: v for k, v in ALL_INSTRUMENTS.items() if k in LIVE_INSTRUMENTS}

RISK_PCT = ALL_INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = ALL_INSTRUMENTS['XAUUSD']['portfolio']
