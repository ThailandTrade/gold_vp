"""
Config ICMarkets — Equilibre 10 strats (WR 72%, PF 1.32, DD -15%)
Objectif: WR eleve + DD bas + rendement correct
Donnees: candles_mt5_xauusd_5m (ICMarkets feed)
"""
BROKER = 'ICMarkets'
PORTFOLIO = [
    # Price Action (3)
    'TOK_2BAR','TOK_BIG','LON_KZ','LON_TOKEND',
    # Indicators (6)
    'PO3_SWEEP','ALL_3SOLDIERS','ALL_PSAR_EMA','ALL_FVG_BULL',
    'ALL_CONSEC_REV','ALL_MACD_RSI','ALL_FIB_618',
]

# Backtest reference Equilibre (donnees ICMarkets, mars 2025 - mars 2026, 1% risk):
# Trades: 2005 | WR: 72% | PF: 1.32 | Max DD: -15.4% | Rend: +511% | Mois+: 13/13
#
# Exits TPSL par strat:
#   PO3_SWEEP      SL=3.0 TP=0.75   PF=1.76  WR=80%
#   ALL_3SOLDIERS  SL=3.0 TP=1.50   PF=1.29  WR=64%
#   LON_KZ         SL=2.5 TP=0.50   PF=1.70  WR=80%
#   LON_TOKEND     SL=3.0 TP=1.50   PF=1.80  WR=65%
#   ALL_PSAR_EMA   SL=3.0 TP=1.00   PF=1.29  WR=72%
#   ALL_FVG_BULL   SL=2.5 TP=0.75   PF=1.45  WR=70%
#   ALL_CONSEC_REV SL=3.0 TP=0.50   PF=1.48  WR=77%
#   ALL_MACD_RSI   SL=3.0 TP=1.50   PF=1.22  WR=63%
#   ALL_FIB_618    SL=1.5 TP=0.50   PF=1.30  WR=65%
#   TOK_BIG        SL=3.0 TP=0.50   PF=1.30  WR=78%
#   TOK_2BAR       SL=3.0 TP=1.50   PF=1.57  WR=67%
