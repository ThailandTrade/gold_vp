"""
Config exit optimale par strat (optimisee sur ICMarkets).
Type: TRAIL (sl, act, trail) ou TPSL (sl, tp)
"""

# Format: 'STRAT': ('TYPE', param1, param2, param3)
# TRAIL: ('TRAIL', sl, act, trail)
# TPSL:  ('TPSL', sl, tp, 0)

STRAT_EXITS = {
    # Price Action
    'TOK_2BAR':       ('TPSL',  0.50, 3.00, 0),
    'TOK_BIG':        ('TRAIL', 1.00, 0.30, 0.75),
    'TOK_FADE':       ('TRAIL', 0.50, 0.30, 0.50),
    'TOK_PREVEXT':    ('TRAIL', 1.50, 0.75, 1.00),
    'LON_PIN':        ('TPSL',  2.00, 1.00, 0),
    'LON_GAP':        ('TRAIL', 1.00, 0.30, 0.75),
    'LON_BIGGAP':     ('TRAIL', 1.00, 0.30, 0.75),
    'LON_KZ':         ('TRAIL', 2.00, 0.30, 0.30),
    'LON_TOKEND':     ('TPSL',  0.50, 2.00, 0),
    'LON_PREV':       ('TRAIL', 0.50, 0.75, 0.50),
    'NY_GAP':         ('TPSL',  0.75, 3.00, 0),
    'NY_LONEND':      ('TPSL',  0.50, 3.00, 0),
    'NY_LONMOM':      ('TPSL',  0.50, 3.00, 0),
    'NY_DAYMOM':      ('TPSL',  0.50, 2.00, 0),
    'D8':             ('TRAIL', 1.00, 1.00, 0.75),

    # Indicators V1
    'ALL_MACD_SIG':   ('TRAIL', 0.50, 0.75, 0.30),  # = ALL_MACD_STD_SIG
    'ALL_RSI_50':     ('TRAIL', 0.50, 0.30, 0.30),
    'ALL_DC50':       ('TRAIL', 1.50, 0.30, 0.75),
    'ALL_DC10':       ('TRAIL', 0.50, 0.75, 0.50),
    'ALL_KC_BRK':     ('TPSL',  0.50, 3.00, 0),
    'ALL_EMA_513':    ('TPSL',  0.50, 1.00, 0),
    'ALL_MACD_ADX':   ('TRAIL', 0.50, 0.30, 0.50),

    # Indicators V2
    'ALL_MACD_MED_SIG': ('TRAIL', 0.50, 1.00, 0.30),
    'ALL_ADX_FAST':     ('TRAIL', 0.50, 0.50, 0.50),
    'ALL_RSI_DIV':      ('TRAIL', 1.50, 0.30, 0.75),
    'ALL_ICHI_TK':      ('TPSL',  0.50, 3.00, 0),
    'ALL_MACD_FAST_SIG': ('TRAIL', 0.75, 0.50, 0.75),
    'ALL_MACD_FAST_ZERO': ('TPSL', 0.50, 1.00, 0),
    'ALL_BB_TIGHT':     ('TPSL',  0.50, 1.50, 0),
    'LON_DC10':         ('TPSL',  1.00, 1.00, 0),

    # Indicators V3
    'ALL_MACD_RSI':     ('TRAIL', 0.50, 0.50, 0.50),
    'TOK_MACD_MED':     ('TRAIL', 1.00, 0.50, 0.75),
    'ALL_WILLR_7':      ('TPSL',  0.50, 3.00, 0),
    'ALL_WILLR_14':     ('TRAIL', 2.00, 0.50, 0.75),
    'TOK_WILLR':        ('TRAIL', 2.00, 0.50, 0.75),
    'ALL_MOM_14':       ('TRAIL', 2.00, 0.50, 1.00),
    'ALL_DC10_EMA':     ('TPSL',  0.50, 3.00, 0),
    'ALL_HMA_CROSS':    ('TPSL',  0.75, 3.00, 0),
    'ALL_MOM_10':       ('TRAIL', 1.50, 0.75, 0.50),
    'NY_HMA_CROSS':     ('TRAIL', 1.00, 0.75, 0.50),
    'ALL_EMA_TREND_PB': ('TRAIL', 1.00, 0.75, 0.75),
    'ALL_CCI_14_ZERO':  ('TRAIL', 0.50, 1.00, 0.30),
    'ALL_CCI_20_ZERO':  ('TRAIL', 0.50, 0.30, 0.50),
    'ALL_HMA_DIR':      ('TPSL',  0.50, 1.50, 0),
    'LON_DC10_MOM':     ('TPSL',  1.00, 1.00, 0),

    # Bonus (gagnees apres optimisation)
    'ALL_EMA_921':      ('TPSL',  0.50, 3.00, 0),
    'ALL_EMA_821':      ('TPSL',  0.50, 3.00, 0),
}

# Default pour strats pas dans le dict
DEFAULT_EXIT = ('TRAIL', 1.00, 0.50, 0.75)
