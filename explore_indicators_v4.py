"""
Exploration V4 - Patterns avances:
FVG (Fair Value Gap), pivot points, candle clock, Heikin Ashi,
session range patterns, ATR regime, multi-bar momentum,
Larry Williams patterns, Turtle Soup.
Tout sur bougies FERMEES, ZERO look-ahead.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import sim_exit_custom
from strat_exits import DEFAULT_EXIT

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

print("Precalcul...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['abs_body'] = abs(c['body'])
c['range'] = c['high'] - c['low']
c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']
c['mid'] = (c['high'] + c['low']) / 2

# Heikin Ashi
c['ha_close'] = (c['open']+c['high']+c['low']+c['close'])/4
c['ha_open'] = c['open'].copy()
for i in range(1, len(c)):
    c.iloc[i, c.columns.get_loc('ha_open')] = (c.iloc[i-1]['ha_open'] + c.iloc[i-1]['ha_close']) / 2
c['ha_high'] = c[['high','ha_open','ha_close']].max(axis=1)
c['ha_low'] = c[['low','ha_open','ha_close']].min(axis=1)
c['ha_body'] = c['ha_close'] - c['ha_open']

# ATR
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
c['atr14'] = tr.ewm(span=14, adjust=False).mean()
c['atr50'] = tr.ewm(span=50, adjust=False).mean()

# Pivot points (daily)
c['prev_high'] = np.nan; c['prev_low'] = np.nan; c['prev_close_d'] = np.nan
dates = c['date'].unique()
for i in range(1, len(dates)):
    prev_dc = c[c['date']==dates[i-1]]
    today_mask = c['date']==dates[i]
    c.loc[today_mask, 'prev_high'] = prev_dc['high'].max()
    c.loc[today_mask, 'prev_low'] = prev_dc['low'].min()
    c.loc[today_mask, 'prev_close_d'] = prev_dc.iloc[-1]['close']
c['pivot'] = (c['prev_high'] + c['prev_low'] + c['prev_close_d']) / 3
c['r1'] = 2*c['pivot'] - c['prev_low']
c['s1'] = 2*c['pivot'] - c['prev_high']
c['r2'] = c['pivot'] + (c['prev_high'] - c['prev_low'])
c['s2'] = c['pivot'] - (c['prev_high'] - c['prev_low'])

# EMA for context
c['ema21'] = c['close'].ewm(span=21, adjust=False).mean()
c['ema50'] = c['close'].ewm(span=50, adjust=False).mean()

# Rolling highs/lows
c['high20'] = c['high'].rolling(20).max()
c['low20'] = c['low'].rolling(20).min()
c['high50'] = c['high'].rolling(50).max()
c['low50'] = c['low'].rolling(50).min()

# Consecutive candle count
bull_streak = np.zeros(len(c)); bear_streak = np.zeros(len(c))
for i in range(1, len(c)):
    if c.iloc[i]['close'] > c.iloc[i]['open']:
        bull_streak[i] = bull_streak[i-1] + 1
    else:
        bull_streak[i] = 0
    if c.iloc[i]['close'] < c.iloc[i]['open']:
        bear_streak[i] = bear_streak[i-1] + 1
    else:
        bear_streak[i] = 0
c['bull_streak'] = bull_streak
c['bear_streak'] = bear_streak

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None

# Test configs: TRAIL + TPSL
configs = [
    ('TRAIL', 1.0, 0.5, 0.75),  # default
    ('TRAIL', 0.5, 0.5, 0.50),  # tight
    ('TRAIL', 2.0, 0.5, 0.75),  # wide
    ('TPSL',  0.5, 3.0, 0),     # tight SL, large TP
    ('TPSL',  1.0, 2.0, 0),     # balanced
    ('TPSL',  0.5, 1.5, 0),     # scalp
]

for ci in range(100, len(c)):
    row = c.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
            if len(yc) > 0:
                prev_day_data = {'open':float(yc.iloc[0]['open']),'close':float(yc.iloc[-1]['close']),
                                 'high':float(yc['high'].max()),'low':float(yc['low'].min()),
                                 'range':float(yc['high'].max()-yc['low'].min()),
                                 'body':float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue

    prev = c.iloc[ci-1]
    prev2 = c.iloc[ci-2] if ci >= 2 else prev
    prev3 = c.iloc[ci-3] if ci >= 3 else prev

    def add(sn, d, e):
        # Test with default config
        b, ex = sim_exit_custom(c, ci, e, d, atr, 'TRAIL', 1.0, 0.5, 0.75, check_entry_candle=False)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════
    # FVG (Fair Value Gap) — imbalance entre 3 bougies
    # ═══════════════════════════════════════════
    if ci >= 3:
        # Bullish FVG: bougie 1 high < bougie 3 low (gap haussier)
        sn = 'ALL_FVG_BULL'
        if sn not in trig:
            if prev3['high'] < row['low'] and row['close'] > row['open'] and abs(row['body']) >= 0.3*atr:
                add(sn,'long',row['close']); trig[sn]=True
        sn = 'ALL_FVG_BEAR'
        if sn not in trig:
            if prev3['low'] > row['high'] and row['close'] < row['open'] and abs(row['body']) >= 0.3*atr:
                add(sn,'short',row['close']); trig[sn]=True

    # FVG fill (price retests into the gap)
    if ci >= 5:
        sn = 'ALL_FVG_FILL'
        if sn not in trig:
            for k in range(2, 5):
                b_k = c.iloc[ci-k]; b_k2 = c.iloc[ci-k-2] if ci-k-2 >= 0 else b_k
                if b_k2['high'] < b_k['low']:  # bullish FVG existed
                    if row['low'] <= b_k['low'] and row['close'] > b_k['low']:  # filled and bounced
                        add(sn,'long',row['close']); trig[sn]=True; break
                if b_k2['low'] > b_k['high']:  # bearish FVG
                    if row['high'] >= b_k['high'] and row['close'] < b_k['high']:
                        add(sn,'short',row['close']); trig[sn]=True; break

    # ═══════════════════════════════════════════
    # PIVOT POINTS
    # ═══════════════════════════════════════════
    if pd.notna(row['pivot']):
        # Pivot bounce
        sn = 'ALL_PIVOT_BOUNCE'
        if sn not in trig:
            if prev['low'] <= row['pivot']*1.001 and row['close'] > row['pivot'] and row['close'] > row['open']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['high'] >= row['pivot']*0.999 and row['close'] < row['pivot'] and row['close'] < row['open']:
                add(sn,'short',row['close']); trig[sn]=True

        # S1/R1 bounce
        sn = 'ALL_SR1_BOUNCE'
        if sn not in trig:
            if prev['low'] <= row['s1']*1.002 and row['close'] > row['s1'] and row['close'] > row['open']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['high'] >= row['r1']*0.998 and row['close'] < row['r1'] and row['close'] < row['open']:
                add(sn,'short',row['close']); trig[sn]=True

        # Pivot breakout
        sn = 'ALL_PIVOT_BRK'
        if sn not in trig:
            if prev['close'] < row['pivot'] and row['close'] > row['pivot'] and abs(row['body']) >= 0.2*atr:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['close'] > row['pivot'] and row['close'] < row['pivot'] and abs(row['body']) >= 0.2*atr:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # HEIKIN ASHI
    # ═══════════════════════════════════════════
    # HA color change
    sn = 'ALL_HA_FLIP'
    if sn not in trig and pd.notna(row['ha_body']):
        if prev['ha_body'] < 0 and row['ha_body'] > 0 and abs(row['ha_body']) >= 0.2*atr:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['ha_body'] > 0 and row['ha_body'] < 0 and abs(row['ha_body']) >= 0.2*atr:
            add(sn,'short',row['close']); trig[sn]=True

    # HA strong candle (no lower wick for bull, no upper wick for bear)
    sn = 'ALL_HA_STRONG'
    if sn not in trig and pd.notna(row['ha_body']):
        ha_rng = row['ha_high'] - row['ha_low']
        if ha_rng > 0:
            if row['ha_body'] > 0 and (row['ha_open'] - row['ha_low']) < 0.1*ha_rng:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['ha_body'] < 0 and (row['ha_high'] - row['ha_open']) < 0.1*ha_rng:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # CANDLE CLOCK (specific time slots)
    # ═══════════════════════════════════════════
    # First candle of each session with body filter
    for h_start, sess in [(0.0,'TOK_CLK'),(8.0,'LON_CLK'),(14.5,'NY_CLK')]:
        sn = sess
        if h_start <= hour < h_start+0.1 and sn not in trig:
            if abs(row['body']) >= 0.3*atr:
                add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # TURTLE SOUP (Linda Raschke)
    # Break 20-bar low/high then reverse
    # ═══════════════════════════════════════════
    sn = 'ALL_TURTLE_SOUP'
    if sn not in trig and ci >= 22 and pd.notna(row.get('low20')):
        prev_low20 = c.iloc[ci-2:ci]['low'].min()  # low des 2 dernieres barres
        low20_before = c.iloc[ci-22:ci-2]['low'].min()  # low des 20 barres avant
        if prev_low20 < low20_before and row['close'] > low20_before and row['close'] > row['open']:
            add(sn,'long',row['close']); trig[sn]=True
        prev_high20 = c.iloc[ci-2:ci]['high'].max()
        high20_before = c.iloc[ci-22:ci-2]['high'].max()
        if prev_high20 > high20_before and row['close'] < high20_before and row['close'] < row['open']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # LIQUIDITY SWEEP (stop hunt then reverse)
    # ═══════════════════════════════════════════
    sn = 'ALL_LIQ_SWEEP'
    if sn not in trig and ci >= 12:
        # Sweep lows then close above
        recent_low = c.iloc[ci-10:ci]['low'].min()
        if row['low'] < recent_low and row['close'] > recent_low and row['close'] > row['open'] and abs(row['body']) >= 0.3*atr:
            add(sn,'long',row['close']); trig[sn]=True
        recent_high = c.iloc[ci-10:ci]['high'].max()
        if row['high'] > recent_high and row['close'] < recent_high and row['close'] < row['open'] and abs(row['body']) >= 0.3*atr:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # BOS (Break of Structure)
    # ═══════════════════════════════════════════
    sn = 'ALL_BOS'
    if sn not in trig and ci >= 30:
        # Find last swing high/low in 30 bars
        last30 = c.iloc[ci-30:ci]
        swing_high = last30['high'].max()
        swing_low = last30['low'].min()
        if row['close'] > swing_high and prev['close'] <= swing_high:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < swing_low and prev['close'] >= swing_low:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ATR REGIME FILTER + big candle
    # ═══════════════════════════════════════════
    sn = 'ALL_ATR_REGIME'
    if sn not in trig and pd.notna(row['atr14']) and pd.notna(row['atr50']):
        # Expanding vol + big candle
        if row['atr14'] > 1.3 * row['atr50'] and abs(row['body']) >= 0.5*atr:
            add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True

    # Contracting vol then breakout
    sn = 'ALL_ATR_CONTRACT'
    if sn not in trig and pd.notna(row['atr14']) and pd.notna(row['atr50']):
        if prev['atr14'] < 0.7 * prev['atr50'] and abs(row['body']) >= 0.5*atr:
            add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # STREAK FADE (consecutive candles then reversal)
    # ═══════════════════════════════════════════
    for n_streak, nm in [(4,'4'),(5,'5'),(6,'6')]:
        sn = f'ALL_STREAK_FADE_{nm}'
        if sn not in trig:
            if row['bear_streak'] >= n_streak and row['close'] > row['open']:  # bearish streak broken by bull
                add(sn,'long',row['close']); trig[sn]=True
            elif row['bull_streak'] >= n_streak and row['close'] < row['open']:  # bullish streak broken by bear
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ASIAN RANGE BREAKOUT at London
    # ═══════════════════════════════════════════
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    if 8.0<=hour<14.5 and 'ASIAN_BRK' not in trig:
        asian = c[(c['ts_dt']>=ds)&(c['ts_dt']<te)]
        if len(asian) >= 50:
            if 'ASIAN_h' not in trig:
                trig['ASIAN_h'] = float(asian['high'].max())
                trig['ASIAN_l'] = float(asian['low'].min())
                trig['ASIAN_rng'] = trig['ASIAN_h'] - trig['ASIAN_l']
            # Only breakout if Asian range was narrow (< 0.7 ATR)
            if trig.get('ASIAN_rng',999) < 0.7*atr:
                if row['close'] > trig['ASIAN_h']:
                    add('ASIAN_BRK','long',row['close']); trig['ASIAN_BRK']=True
                elif row['close'] < trig['ASIAN_l']:
                    add('ASIAN_BRK','short',row['close']); trig['ASIAN_BRK']=True

    # Asian range breakout (any range)
    if 8.0<=hour<14.5 and 'ASIAN_BRK_ANY' not in trig:
        if 'ASIAN_h' in trig:
            if row['close'] > trig['ASIAN_h']:
                add('ASIAN_BRK_ANY','long',row['close']); trig['ASIAN_BRK_ANY']=True
            elif row['close'] < trig['ASIAN_l']:
                add('ASIAN_BRK_ANY','short',row['close']); trig['ASIAN_BRK_ANY']=True

    # ═══════════════════════════════════════════
    # HAMMER / ENGULFING at key levels
    # ═══════════════════════════════════════════
    # Hammer at 20-bar low
    sn = 'ALL_HAMMER_LOW'
    if sn not in trig and ci >= 20:
        if row['low'] <= c.iloc[ci-20:ci]['low'].min():
            if row['lower_wick'] > 2*row['abs_body'] and row['upper_wick'] < row['abs_body'] and row['abs_body'] >= 0.1*atr:
                add(sn,'long',row['close']); trig[sn]=True
    sn = 'ALL_STAR_HIGH'
    if sn not in trig and ci >= 20:
        if row['high'] >= c.iloc[ci-20:ci]['high'].max():
            if row['upper_wick'] > 2*row['abs_body'] and row['lower_wick'] < row['abs_body'] and row['abs_body'] >= 0.1*atr:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # POWER OF 3 (AMD pattern)
    # Accumulation (tight range), Manipulation (fake break), Distribution (real move)
    # ═══════════════════════════════════════════
    if ci >= 10:
        sn = 'ALL_AMD'
        if sn not in trig:
            # Look for tight range in last 6 bars, then break and reverse in last 3
            last6 = c.iloc[ci-6:ci]
            rng6 = last6['high'].max() - last6['low'].min()
            if rng6 < 0.5*atr:  # accumulation
                # Did the current bar break and reverse?
                if row['low'] < last6['low'].min() and row['close'] > last6['high'].max():
                    add(sn,'long',row['close']); trig[sn]=True
                elif row['high'] > last6['high'].max() and row['close'] < last6['low'].min():
                    add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION-SPECIFIC
    # ═══════════════════════════════════════════
    # Pivot bounce at London open
    if 8.0<=hour<10.0 and pd.notna(row['pivot']):
        sn = 'LON_PIVOT'
        if sn not in trig:
            if prev['low'] <= row['pivot']*1.001 and row['close'] > row['pivot'] and row['close'] > row['open']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['high'] >= row['pivot']*0.999 and row['close'] < row['pivot'] and row['close'] < row['open']:
                add(sn,'short',row['close']); trig[sn]=True

    # HA flip at NY
    if 14.5<=hour<17.0:
        sn = 'NY_HA_FLIP'
        if sn not in trig and pd.notna(row['ha_body']):
            if prev['ha_body'] < 0 and row['ha_body'] > 0 and abs(row['ha_body']) >= 0.3*atr:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['ha_body'] > 0 and row['ha_body'] < 0 and abs(row['ha_body']) >= 0.3*atr:
                add(sn,'short',row['close']); trig[sn]=True

    # Liquidity sweep at Tokyo
    if 0.0<=hour<6.0:
        sn = 'TOK_LIQ'
        if sn not in trig and ci >= 12:
            tok_candles = c[(c['ts_dt']>=ds)&(c['ts_dt']<te)&(c['ts_dt']<ct)]
            if len(tok_candles) >= 6:
                rl = tok_candles['low'].min()
                rh = tok_candles['high'].max()
                if row['low'] < rl and row['close'] > rl and row['close'] > row['open']:
                    add(sn,'long',row['close']); trig[sn]=True
                elif row['high'] > rh and row['close'] < rh and row['close'] < row['open']:
                    add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION V4 - Patterns avances (FVG, Pivots, HA, SMC, Turtle Soup, etc.)")
print("="*130)
print(f"{'Strat':>18s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*130)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 20: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1,t2,t3] if x>0)
    split = f1>0 and f2>0
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>18s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
