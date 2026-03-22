"""
Config FTMO — 4 strats (solide, DD contenu, 13/13 mois+)
Backtest reference (post-fix look-ahead): PF 1.50, DD -12.7%, 13/13 mois+, 437 trades
Donnees: candles_mt5_xauusd_5m (FTMO feed)
"""
BROKER = 'FTMO'
PORTFOLIO = [
    'TOK_PREVEXT',
    'LON_TOKEND',
    'NY_DAYMOM',
    'D8',
]
