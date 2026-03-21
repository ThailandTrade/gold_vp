"""
Config 5ers — 6 strats
Backtest reference: PF 1.82, DD -12.4%, 11/13 mois+, 893 trades
Pas de donnees bid/ask, spread estime a 0.20 pts
Donnees: candles_mt5_xauusd_5m (5ers feed)
"""
BROKER = '5ers'
SPREAD_OVERRIDE = 0.20
PORTFOLIO = [
    'TOK_BIG','TOK_PREVEXT',
    'LON_BIGGAP','LON_PREV',
    'NY_DAYMOM','NY_LONMOM',
]

# Backtest reference (donnees 5ers, mars 2025 - mars 2026):
# Capital: $1,000 -> $19,511 (+1851%)
# Trades: 893 | WR: 47% | PF: 1.82 | Max DD: -12.4% | Mois+: 11/13
#
# A $100k, 0.2% risk: $100k -> $186k (+86.1%), DD -2.6%
#
# Par strat (5ers):
#   TOK_BIG      196  43%  PF 1.26
#   TOK_PREVEXT   40  50%  PF 2.22
#   LON_BIGGAP   187  49%  PF 1.73
#   LON_PREV     221  48%  PF 1.48
#   NY_DAYMOM    216  47%  PF 1.99
#   NY_LONMOM    176  38%  PF 1.56
