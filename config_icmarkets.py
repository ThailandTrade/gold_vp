"""
Config ICMarkets — 14 strats
Backtest reference: PF 1.57, DD -22.1%, 13/13 mois+, 2232 trades
Donnees: candles_mt5_xauusd_5m (ICMarkets feed)
"""
BROKER = 'ICMarkets'
PORTFOLIO = [
    'TOK_2BAR','TOK_BIG','TOK_FADE','TOK_PREVEXT',
    'LON_PIN','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
    'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM',
]

# Backtest reference (donnees ICMarkets, mars 2025 - mars 2026):
# Capital: $1,000 -> $2,742,638 (+274,164%)
# Trades: 2232 | WR: 45% | PF: 1.57 | Max DD: -22.1% | Mois+: 13/13
#
# Par strat:
#   TOK_2BAR     196  43%  PF 1.67
#   TOK_BIG      215  39%  PF 1.31
#   TOK_FADE     190  51%  PF 2.04
#   TOK_PREVEXT   12  92%  PF 11.19
#   LON_PIN      187  39%  PF 1.26
#   LON_GAP      243  46%  PF 1.75
#   LON_BIGGAP   222  45%  PF 1.70
#   LON_KZ       220  45%  PF 1.51
#   LON_TOKEND    47  57%  PF 2.77
#   LON_PREV     133  50%  PF 2.13
#   NY_GAP       105  40%  PF 2.48
#   NY_LONEND    100  43%  PF 1.96
#   NY_LONMOM    134  43%  PF 1.79
#   NY_DAYMOM    228  45%  PF 1.67
