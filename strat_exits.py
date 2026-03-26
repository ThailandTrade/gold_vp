"""
Config exit optimale par strat (optimisee 2026-03-23 via optimize_all.py).
Score: PF * WR, filtre split OK + PF > 1.05.
Type: TRAIL (sl, act, trail) ou TPSL (sl, tp)
"""

# Format: 'STRAT': ('TYPE', param1, param2, param3)
# TRAIL: ('TRAIL', sl, act, trail)
# TPSL:  ('TPSL', sl, tp, 0)

STRAT_EXITS = {
    # ── Price Action ──
    'TOK_2BAR':       ('TRAIL', 3.00, 0.50, 0.50),   # PF=1.61 WR=75%
    'TOK_BIG':        ('TRAIL', 3.00, 0.30, 0.30),   # PF=1.57 WR=76%
    'TOK_FADE':       ('TRAIL', 3.00, 0.50, 0.30),   # PF=1.10 WR=70%
    'TOK_PREVEXT':    ('TRAIL', 1.50, 0.75, 1.00),   # PF=1.53 WR=51%
    'LON_PIN':        ('TPSL',  2.50, 1.00, 0),      # PF=1.13 WR=75%
    'LON_GAP':        ('TRAIL', 3.00, 0.30, 0.30),   # PF=1.65 WR=74%
    'LON_BIGGAP':     ('TRAIL', 3.00, 0.75, 0.50),   # PF=1.70 WR=74%
    'LON_KZ':         ('TRAIL', 3.00, 0.50, 0.30),   # PF=1.80 WR=82%
    'LON_TOKEND':     ('TRAIL', 3.00, 0.30, 0.30),   # PF=1.81 WR=68%
    'LON_PREV':       ('TRAIL', 2.00, 0.75, 0.75),   # PF=1.19 WR=63%
    'NY_GAP':         ('TRAIL', 2.00, 0.50, 0.50),   # PF=1.16 WR=53%
    'NY_LONEND':      ('TRAIL', 3.00, 0.75, 0.30),   # PF=1.48 WR=62%
    'NY_LONMOM':      ('TRAIL', 3.00, 0.75, 0.30),   # PF=1.30 WR=62%
    'NY_DAYMOM':      ('TRAIL', 3.00, 0.75, 0.50),   # PF=1.34 WR=63%
    'D8':             ('TRAIL', 1.00, 1.00, 0.75),   # PF=1.69 WR=56%

    # ── Indicators (dans detect_all) ──
    'ALL_MACD_RSI':   ('TRAIL', 1.50, 0.50, 0.50),   # PF=1.67 WR=60%
    'ALL_FVG_BULL':   ('TRAIL', 3.00, 1.00, 0.75),   # PF=1.63 WR=70%
    'ALL_CONSEC_REV': ('TRAIL', 3.00, 0.30, 0.30),   # PF=1.65 WR=77%
    'ALL_FIB_618':    ('TRAIL', 3.00, 0.30, 0.30),   # PF=1.48 WR=78%
    'ALL_3SOLDIERS':  ('TPSL',  3.00, 2.00, 0),      # PF=1.34 WR=67%
    'ALL_PSAR_EMA':   ('TPSL',  3.00, 1.50, 0),      # PF=1.21 WR=74%
    'PO3_SWEEP':      ('TRAIL', 3.00, 0.75, 0.75),   # PF=2.46 WR=79%
    'ALL_KC_BRK':     ('TRAIL', 3.00, 1.00, 0.75),   # PF=1.20 WR=69%

    # ── Indicators (dans optimize_all.py seulement) ──
    'ALL_MACD_STD_SIG':  ('TPSL',  3.00, 0.50, 0),   # PF=1.31 WR=88%
    'ALL_MACD_MED_SIG':  ('TRAIL', 3.00, 0.50, 0.50), # PF=1.44 WR=69%
    'ALL_MACD_FAST_SIG': ('TRAIL', 3.00, 0.50, 0.50), # PF=1.33 WR=70%
    'ALL_ADX_FAST':      ('TRAIL', 3.00, 0.50, 0.50), # PF=1.47 WR=69%
    'ALL_RSI_50':        ('TRAIL', 3.00, 0.50, 0.50), # PF=1.28 WR=69%
    'ALL_RSI_DIV':       ('TRAIL', 3.00, 0.30, 0.30), # PF=1.50 WR=73%
    'ALL_DC10':          ('TRAIL', 3.00, 0.75, 0.75), # PF=1.33 WR=66%
    'ALL_DC10_EMA':      ('TRAIL', 3.00, 0.75, 0.75), # PF=1.29 WR=66%
    'ALL_DC50':          ('TRAIL', 3.00, 0.50, 0.30), # PF=1.19 WR=72%
    'ALL_KC_BRK':        ('TRAIL', 3.00, 1.00, 0.75), # PF=1.20 WR=69%
    'ALL_MACD_ADX':      ('TPSL',  3.00, 0.50, 0),   # PF=1.18 WR=88%
    'ALL_ICHI_TK':       ('TPSL',  2.50, 0.50, 0),   # PF=1.06 WR=85%
    'ALL_WILLR_7':       ('TRAIL', 3.00, 0.50, 0.30), # PF=1.15 WR=72%
    'ALL_WILLR_14':      ('TRAIL', 2.00, 0.50, 0.30), # PF=1.46 WR=65%
    'ALL_MOM_10':        ('TRAIL', 3.00, 0.30, 0.30), # PF=1.48 WR=72%
    'ALL_MOM_14':        ('TPSL',  3.00, 0.75, 0),   # PF=1.34 WR=84%
    'ALL_NR4':           ('TPSL',  2.00, 0.50, 0),   # PF=1.22 WR=82%
    'ALL_HMA_CROSS':     ('TRAIL', 3.00, 0.50, 0.50), # PF=1.40 WR=70%
    'ALL_PIVOT_BOUNCE':  ('TRAIL', 3.00, 0.50, 0.50), # PF=1.39 WR=68%
    'ALL_PIVOT_BRK':     ('TRAIL', 1.50, 0.75, 0.30), # PF=1.39 WR=56%
    'ALL_MTF_BRK':       ('TRAIL', 3.00, 0.50, 0.50), # PF=1.26 WR=71%
    'ALL_AO_SAUCER':     ('TPSL',  3.00, 0.50, 0),   # PF=1.23 WR=88%
    'ALL_CMO_9':         ('TRAIL', 3.00, 1.00, 0.75), # PF=1.31 WR=61%
    'ALL_CMO_14':        ('TRAIL', 1.00, 0.50, 0.50), # PF=1.20 WR=40%
    'ALL_CMO_14_ZERO':   ('TPSL',  3.00, 0.75, 0),   # PF=1.34 WR=84%
    'ALL_FISHER_9':      ('TRAIL', 3.00, 0.75, 0.75), # PF=1.20 WR=65%
    'ALL_DPO_14':        ('TPSL',  3.00, 0.25, 0),   # PF=1.43 WR=94%
    'ALL_BB_TIGHT':      ('TPSL',  3.00, 0.75, 0),   # PF=1.30 WR=82%
    'ALL_CCI_14_ZERO':   ('TPSL',  3.00, 0.50, 0),   # PF=1.13 WR=87%
    'ALL_CCI_20_ZERO':   ('TPSL',  3.00, 0.75, 0),   # PF=1.35 WR=83%
    'ALL_EMA_513':       ('TPSL',  3.00, 0.25, 0),   # PF=1.23 WR=94%
    'ALL_EMA_821':       ('TRAIL', 0.50, 1.00, 0.30), # PF=1.17 WR=23%
    'ALL_EMA_921':       ('TPSL',  0.50, 3.00, 0),   # PF=1.30 WR=16%
    'ALL_EMA_TREND_PB':  ('TRAIL', 3.00, 0.50, 0.50), # PF=1.25 WR=71%
    'ALL_HMA_DIR':       ('TRAIL', 3.00, 0.50, 0.50), # PF=1.19 WR=67%
    'ALL_MACD_FAST_ZERO':('TPSL',  3.00, 0.25, 0),   # PF=1.23 WR=94%
    'LON_DC10':          ('TRAIL', 2.00, 0.30, 0.30), # PF=1.10 WR=69%
    'LON_DC10_MOM':      ('TRAIL', 2.00, 0.30, 0.30), # PF=1.10 WR=69%
    'NY_HMA_CROSS':      ('TRAIL', 2.00, 1.00, 0.75), # PF=1.09 WR=51%

    # ── Tokyo session indicators ──
    'TOK_MACD_MED':      ('TPSL',  2.50, 1.00, 0),   # PF=1.28 WR=73%
    'TOK_NR4':           ('TPSL',  1.50, 0.50, 0),   # PF=1.30 WR=78%
    'TOK_WILLR':         ('TRAIL', 2.00, 0.50, 0.30), # PF=1.48 WR=67%
    'TOK_FISHER':        ('TRAIL', 3.00, 0.75, 0.75), # PF=1.17 WR=66%

    # ── New strats (default configs, will be optimized per broker) ──
    'ALL_ENGULF':        ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_HAMMER':        ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_DOJI_REV':      ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_MSTAR':         ('TRAIL', 3.00, 0.50, 0.50),
    'LON_ASIAN_BRK':     ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_INSIDE_BRK':    ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_BB_SQUEEZE':    ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_RSI_EXTREME':   ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_MACD_HIST':     ('TRAIL', 3.00, 0.50, 0.50),
    'ALL_VOL_SPIKE':     ('TRAIL', 3.00, 0.50, 0.50),
}

# Default pour strats pas dans le dict
DEFAULT_EXIT = ('TRAIL', 3.00, 0.50, 0.50)
