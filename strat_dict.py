"""
Dictionnaire complet de toutes les strategies.
Nomenclature: {SESSION}_{TYPE}_{DETAIL}

Sessions: TOK (0-6h), LON (8-14h30), NY (14h30-21h), ALL (24h), CROSS (multi-session)
Types: GAP, MOM, REV, BRK, PIN, IND (indicator), FADE, CONT
Indicators: EMA, RSI, MACD, BB (Bollinger), STOCH, VWAP, ADX, ICHI, KC (Keltner), DC (Donchian)

Format: SESSION_TYPE[_INDICATOR][_DETAIL]
Ex: LON_IND_EMA_CROSS, ALL_IND_RSI_OB, NY_BRK_DC20
"""

# ═══════════════════════════════════════════════════════
# STRATEGIES EXISTANTES (testees, certaines survivent)
# ═══════════════════════════════════════════════════════

EXISTING = {
    # TOKYO (0h-6h)
    'TOK_2BAR':    {'type':'close', 'session':'Tokyo', 'pf_icm':1.68, 'pf_ftmo':1.29, 'desc':'Two-bar reversal (body>0.5ATR, 2nd>1st)'},
    'TOK_BIG':     {'type':'close', 'session':'Tokyo', 'pf_icm':1.33, 'pf_ftmo':1.05, 'desc':'Big candle >1ATR continuation'},
    'TOK_FADE':    {'type':'open',  'session':'Tokyo', 'pf_icm':1.76, 'pf_ftmo':1.08, 'desc':'Fade previous day >1ATR'},
    'TOK_PREVEXT': {'type':'open',  'session':'Tokyo', 'pf_icm':5.68, 'pf_ftmo':0.88, 'desc':'Prev day close near extreme (top/bottom 10%)'},
    'TOK_IB':      {'type':'close', 'session':'Tokyo', 'pf_icm':None, 'pf_ftmo':1.12, 'desc':'IB 1h breakout'},
    'TOK_3BAR':    {'type':'close', 'session':'Tokyo', 'pf_icm':None, 'pf_ftmo':1.01, 'desc':'3 consecutive same-dir candles >0.5ATR'},
    'TOK_6BAR':    {'type':'close', 'session':'Tokyo', 'pf_icm':None, 'pf_ftmo':1.19, 'desc':'6-bar bias (5/6 or 1/6 bullish)'},
    'TOK_OUTSIDE': {'type':'close', 'session':'Tokyo', 'pf_icm':None, 'pf_ftmo':1.66, 'desc':'Outside bar engulfing 3 previous'},

    # LONDON (8h-14h30)
    'LON_PIN':     {'type':'close', 'session':'London', 'pf_icm':1.30, 'pf_ftmo':0.88, 'desc':'Pin bar (close top/bottom 10%)'},
    'LON_GAP':     {'type':'open',  'session':'London', 'pf_icm':1.56, 'pf_ftmo':1.28, 'desc':'Gap Tokyo->London >0.5ATR'},
    'LON_BIGGAP':  {'type':'open',  'session':'London', 'pf_icm':1.52, 'pf_ftmo':1.25, 'desc':'Gap Tokyo->London >1.0ATR'},
    'LON_KZ':      {'type':'open',  'session':'London', 'pf_icm':1.46, 'pf_ftmo':1.22, 'desc':'KZ 8h-10h fade >0.5ATR'},
    'LON_TOKEND':  {'type':'open',  'session':'London', 'pf_icm':2.03, 'pf_ftmo':1.14, 'desc':'3 last Tokyo candles >1ATR continuation'},
    'LON_PREV':    {'type':'open',  'session':'London', 'pf_icm':1.90, 'pf_ftmo':1.11, 'desc':'Previous day >1ATR continuation'},
    'LON_FADE':    {'type':'open',  'session':'London', 'pf_icm':None, 'pf_ftmo':0.67, 'desc':'Fade Tokyo move >1ATR'},
    'LON_2BAR':    {'type':'close', 'session':'London', 'pf_icm':None, 'pf_ftmo':0.76, 'desc':'2BAR reversal London'},
    'LON_ENGULF':  {'type':'close', 'session':'London', 'pf_icm':None, 'pf_ftmo':0.74, 'desc':'Engulfing London'},
    'D8':          {'type':'close', 'session':'London', 'pf_icm':None, 'pf_ftmo':1.36, 'desc':'Inside day breakout London'},

    # NY (14h30-21h)
    'NY_GAP':      {'type':'open',  'session':'NY', 'pf_icm':1.30, 'pf_ftmo':1.06, 'desc':'Gap London->NY >0.5ATR'},
    'NY_LONEND':   {'type':'open',  'session':'NY', 'pf_icm':1.55, 'pf_ftmo':1.14, 'desc':'3 last London candles >1ATR continuation'},
    'NY_LONMOM':   {'type':'open',  'session':'NY', 'pf_icm':1.38, 'pf_ftmo':1.02, 'desc':'3 last London candles >0.5ATR continuation'},
    'NY_DAYMOM':   {'type':'open',  'session':'NY', 'pf_icm':1.10, 'pf_ftmo':0.93, 'desc':'Daily move >1.5ATR continuation'},
}

# ═══════════════════════════════════════════════════════
# NOUVELLES STRATEGIES A TESTER (indicators)
# ═══════════════════════════════════════════════════════

NEW_INDICATOR_STRATS = {
    # EMA
    'ALL_IND_EMA_921':    {'desc':'EMA 9/21 crossover (9 crosses above 21 = long)', 'params':{'fast':9,'slow':21}},
    'ALL_IND_EMA_513':    {'desc':'EMA 5/13 crossover', 'params':{'fast':5,'slow':13}},
    'ALL_IND_EMA_821':    {'desc':'EMA 8/21 crossover', 'params':{'fast':8,'slow':21}},
    'ALL_IND_EMA_SLOPE':  {'desc':'EMA 21 slope > threshold (trending)', 'params':{'period':21,'threshold':0.1}},

    # RSI
    'ALL_IND_RSI_OB':     {'desc':'RSI 14 oversold (<30) -> long, overbought (>70) -> short', 'params':{'period':14,'ob':70,'os':30}},
    'ALL_IND_RSI_OB7':    {'desc':'RSI 7 oversold/overbought', 'params':{'period':7,'ob':70,'os':30}},
    'ALL_IND_RSI_50':     {'desc':'RSI 14 centerline cross (cross above 50 = long)', 'params':{'period':14}},
    'ALL_IND_RSI_EXT':    {'desc':'RSI 14 extreme (<20 or >80)', 'params':{'period':14,'ob':80,'os':20}},

    # MACD
    'ALL_IND_MACD_SIG':   {'desc':'MACD signal line cross', 'params':{'fast':12,'slow':26,'signal':9}},
    'ALL_IND_MACD_ZERO':  {'desc':'MACD zero line cross', 'params':{'fast':12,'slow':26,'signal':9}},
    'ALL_IND_MACD_HIST':  {'desc':'MACD histogram reversal (3 declining then 1 rising)', 'params':{'fast':12,'slow':26,'signal':9}},

    # Bollinger Bands
    'ALL_IND_BB_SQUEEZE': {'desc':'BB squeeze (bandwidth < threshold) then breakout', 'params':{'period':20,'std':2}},
    'ALL_IND_BB_MR':      {'desc':'BB mean reversion (price touches band, enter toward middle)', 'params':{'period':20,'std':2}},
    'ALL_IND_BB_WALK':    {'desc':'BB band walk (close above upper band = strong trend)', 'params':{'period':20,'std':2}},

    # Stochastic
    'ALL_IND_STOCH_OB':   {'desc':'Stoch K crosses D in oversold/overbought zone', 'params':{'k':14,'d':3,'smooth':3,'ob':80,'os':20}},

    # ADX
    'ALL_IND_ADX_TREND':  {'desc':'ADX > 25 + DI+ > DI- (long) or DI- > DI+ (short)', 'params':{'period':14,'threshold':25}},

    # Donchian Channel
    'ALL_IND_DC20_BRK':   {'desc':'Donchian 20 breakout (close above 20-bar high)', 'params':{'period':20}},
    'ALL_IND_DC50_BRK':   {'desc':'Donchian 50 breakout', 'params':{'period':50}},

    # Keltner Channel
    'ALL_IND_KC_BRK':     {'desc':'Keltner Channel breakout (EMA20 +/- 1.5*ATR14)', 'params':{'ema':20,'atr':14,'mult':1.5}},

    # VWAP (approximated from typical price * volume proxy)
    'ALL_IND_VWAP_CROSS': {'desc':'Price cross above/below session VWAP', 'params':{}},

    # Combinations
    'ALL_IND_RSI_EMA':    {'desc':'RSI <30 + price above EMA21 = strong long', 'params':{}},
    'ALL_IND_MACD_ADX':   {'desc':'MACD signal cross + ADX>25 = trend confirmed', 'params':{}},
    'ALL_IND_BB_RSI':     {'desc':'BB lower band touch + RSI<30 = long', 'params':{}},
    'ALL_IND_EMA_MACD':   {'desc':'EMA 9/21 cross + MACD same direction', 'params':{}},
    'ALL_IND_STOCH_BB':   {'desc':'Stoch oversold + BB lower band = long', 'params':{}},

    # Session-specific with indicators
    'TOK_IND_RSI_OB':     {'desc':'RSI oversold/overbought during Tokyo only', 'params':{'period':14,'ob':70,'os':30}},
    'LON_IND_EMA_CROSS':  {'desc':'EMA 9/21 cross during London open (8h-9h)', 'params':{'fast':9,'slow':21}},
    'NY_IND_MACD_SIG':    {'desc':'MACD signal cross at NY open', 'params':{'fast':12,'slow':26,'signal':9}},
    'LON_IND_BB_SQUEEZE': {'desc':'BB squeeze breakout during London', 'params':{'period':20,'std':2}},
    'NY_IND_RSI_EXT':     {'desc':'RSI extreme during NY session', 'params':{'period':14,'ob':80,'os':20}},
}
