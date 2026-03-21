"""
Config FTMO — 8 strats (survivent sur donnees FTMO)
Backtest reference: PF 1.50, DD -12.7%, 13/13 mois+, 439 trades
Donnees: candles_mt5_xauusd_5m (FTMO feed)
"""
BROKER = 'FTMO'
PORTFOLIO = [
    'TOK_2BAR','TOK_FADE','TOK_PREVEXT',
    'LON_KZ','LON_TOKEND',
    'NY_DAYMOM','NY_LONEND',
    'D8',
]

# Backtest reference (donnees FTMO, mars 2025 - mars 2026):
# Combo: D8+LON_KZ+LON_TOKEND+NY_DAYMOM+NY_LONEND+TOK_2BAR+TOK_FADE+TOK_PREVEXT
# Capital: $1,000 -> $2,840 (+184%)  [a 1% risk, risque conservateur pour prop firm]
# Trades: 1166 | WR: 42% | PF: 1.18 | Max DD: -25.2% | Mois+: 10/13
#
# Combo conservateur: D8+LON_TOKEND+NY_DAYMOM+TOK_PREVEXT
# Capital: $1,000 -> $3,390 (+239%)
# Trades: 439 | WR: 45% | PF: 1.50 | Max DD: -12.7% | Mois+: 13/13
#
# Par strat (FTMO):
#   TOK_2BAR     243  41%  PF 1.29
#   TOK_FADE     232  38%  PF 1.21
#   TOK_PREVEXT   40  40%  PF 1.56
#   LON_KZ       225  42%  PF 1.28
#   LON_TOKEND   120  46%  PF 1.42
#   NY_DAYMOM    232  44%  PF 1.50
#   NY_LONEND    151  36%  PF 1.34
#   D8            52  50%  PF 1.37
