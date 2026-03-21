"""
Config FTMO — 4 strats (solide, DD contenu, 13/13 mois+)
Backtest reference: PF 1.50, DD -12.7%, 13/13 mois+, 439 trades
Donnees: candles_mt5_xauusd_5m (FTMO feed)
"""
BROKER = 'FTMO'
PORTFOLIO = [
    'TOK_PREVEXT',
    'LON_TOKEND',
    'NY_DAYMOM',
    'D8',
]

# Backtest reference (donnees FTMO, mars 2025 - mars 2026):
# Capital: $1,000 -> $3,390 (+239%)
# Trades: 439 | WR: 45% | PF: 1.50 | Max DD: -12.7% | Mois+: 13/13
#
# Par strat (FTMO):
#   TOK_PREVEXT   40  40%  PF 1.56  (prev day close extreme -> Tokyo)
#   LON_TOKEND   120  46%  PF 1.42  (3 last Tokyo candles >1ATR -> London)
#   NY_DAYMOM    232  44%  PF 1.50  (daily move >1.5ATR -> NY continuation)
#   D8            52  50%  PF 1.37  (inside day breakout London)
