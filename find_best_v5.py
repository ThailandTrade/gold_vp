"""
Optimisation v5 — 16 strategies candidates, combos de 6 a 16.
A, C, D, E, F, G, H, I, J (champion actuel)
+ O (BigCandle_tok), P (ORB_NY30), Q (Engulfing_lon)
+ R (3soldiers_cont_tok), S (3soldiers_rev_lon), T (London_fail_Asian), U (Faux_breakout_lon)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import time
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)

cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)
n_td = len(set(candles['date'].unique()))
SL, ACT, TRAIL = 0.75, 0.5, 0.3

S = {}

# ── A: IB Tokyo 1h UP ──
print("  A (IB_tok_1h)...", flush=True); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 18: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lvl = p.iloc[:12]['high'].max()
    for i in range(12, len(p)):
        if p.iloc[i]['close'] > lvl:
            pi = candles.index.get_loc(p.index[i]); e = p.iloc[i]['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['A'] = t

# ── C: FADE Tokyo->London ──
print("  C (FADE_tok_lon)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['C'] = t

# ── D: GAP Tokyo-London ──
print("  D (GAP_tok_lon)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tc = candles[candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc) < 5: continue
    tok_close = tc.iloc[-1]['close']
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    lon_open = lon.iloc[0]['open']
    gap = (lon_open - tok_close) / atr
    if abs(gap) < 0.5: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon_open
    d = 'long' if gap > 0 else 'short'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['D'] = t

# ── E: KZ London fade ──
print("  E (KZ_lon_fade)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    kz = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz) < 20: continue
    m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
    if abs(m) < 0.5: continue
    post = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
    if len(post) < 6: continue
    pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['E'] = t

# ── F: 2BAR Tokyo rev ──
print("  F (2BAR_tok_rev)..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 8: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(p)):
        b1b = p.iloc[i-1]['close']-p.iloc[i-1]['open']; b2b = p.iloc[i]['close']-p.iloc[i]['open']
        if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
        if b1b*b2b >= 0 or abs(b2b) <= abs(b1b): continue
        pi = candles.index.get_loc(p.index[i]); e = p.iloc[i]['close']
        d = 'long' if b2b > 0 else 'short'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['F'] = t

# ── G: NY1st candle ──
print("  G (NY1st_candle)..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first = p.iloc[0]; body = first['close'] - first['open']
    if abs(body) < 0.3*atr: continue
    d = 'long' if body > 0 else 'short'
    if len(p) < 2: continue
    pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['G'] = t

# ── H: TOKEND 3b ──
print("  H (TOKEND_3b)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 9: continue
    last3 = tok.iloc[-3:]
    m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
    d = 'long' if m > 0 else 'short'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['H'] = t

# ── I: FADENY 1h ──
print("  I (FADENY_1h)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ny1 = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1) < 10: continue
    m = (ny1.iloc[-1]['close'] - ny1.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue
    post = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
    if len(post) < 6: continue
    pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['I'] = t

# ── J: LON1st candle ──
print("  J (LON1st_candle)..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first = p.iloc[0]; body = first['close'] - first['open']
    if abs(body) < 0.3*atr: continue
    d = 'long' if body > 0 else 'short'
    if len(p) < 2: continue
    pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['J'] = t

# ── O: Big candle >1ATR Tokyo continuation ──
print("  O (BigCandle_tok)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                   (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess) < 6: continue
    for i in range(len(sess)):
        r = sess.iloc[i]
        body = r['close'] - r['open']
        if abs(body) >= 1.0*atr:
            d = 'long' if body > 0 else 'short'
            pi = candles.index.get_loc(sess.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['O'] = t

# ── P: ORB NY 30min ──
print("  P (ORB_NY30)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ny = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) &
                 (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(ny) < 12: continue
    orb_high = ny.iloc[:6]['high'].max()
    orb_low = ny.iloc[:6]['low'].min()
    for i in range(6, len(ny)):
        r = ny.iloc[i]
        if r['close'] > orb_high:
            pi = candles.index.get_loc(ny.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        elif r['close'] < orb_low:
            pi = candles.index.get_loc(ny.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['P'] = t

# ── Q: Engulfing London ──
print("  Q (Engulfing_lon)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                   (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess) < 6: continue
    for i in range(1, len(sess)):
        prev_b = sess.iloc[i-1]; cur_b = sess.iloc[i]
        triggered = False
        # Bullish engulfing
        if (prev_b['close'] < prev_b['open'] and cur_b['close'] > cur_b['open'] and
            cur_b['open'] <= prev_b['close'] and cur_b['close'] >= prev_b['open'] and
            abs(cur_b['close']-cur_b['open']) >= 0.3*atr):
            pi = candles.index.get_loc(sess.index[i]); e = cur_b['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); triggered = True
        # Bearish engulfing
        if not triggered and (prev_b['close'] > prev_b['open'] and cur_b['close'] < cur_b['open'] and
            cur_b['open'] >= prev_b['close'] and cur_b['close'] <= prev_b['open'] and
            abs(cur_b['close']-cur_b['open']) >= 0.3*atr):
            pi = candles.index.get_loc(sess.index[i]); e = cur_b['close']
            b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); triggered = True
        if triggered: break
S['Q'] = t

# ── R: 3 soldiers/crows continuation Tokyo ──
print("  R (3soldiers_tok)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                   (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess) < 6: continue
    for i in range(2, len(sess)):
        c1 = sess.iloc[i-2]; c2 = sess.iloc[i-1]; c3 = sess.iloc[i]
        b1 = c1['close']-c1['open']; b2 = c2['close']-c2['open']; b3 = c3['close']-c3['open']
        if b1*b2 > 0 and b2*b3 > 0 and min(abs(b1),abs(b2),abs(b3)) > 0.1*atr:
            total = abs(b1+b2+b3)
            if total < 0.5*atr: continue
            d = 'long' if b3 > 0 else 'short'
            pi = candles.index.get_loc(sess.index[i]); e = c3['close']
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['R'] = t

# ── S: 3 soldiers/crows reversal London ──
print("  S (3soldiers_rev_lon)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                   (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess) < 6: continue
    for i in range(2, len(sess)):
        c1 = sess.iloc[i-2]; c2 = sess.iloc[i-1]; c3 = sess.iloc[i]
        b1 = c1['close']-c1['open']; b2 = c2['close']-c2['open']; b3 = c3['close']-c3['open']
        if b1*b2 > 0 and b2*b3 > 0 and min(abs(b1),abs(b2),abs(b3)) > 0.1*atr:
            total = abs(b1+b2+b3)
            if total < 0.5*atr: continue
            # REVERSAL
            d = 'short' if b3 > 0 else 'long'
            pi = candles.index.get_loc(sess.index[i]); e = c3['close']
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['S'] = t

# ── T: London failed Asian break ──
print("  T (Lon_fail_Asian)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                  (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_high = tok['high'].max(); tok_low = tok['low'].min()
    lon = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                  (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 10: continue
    for i in range(len(lon)):
        r = lon.iloc[i]
        if r['high'] > tok_high and r['close'] < tok_high:
            pi = candles.index.get_loc(lon.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        if r['low'] < tok_low and r['close'] > tok_low:
            pi = candles.index.get_loc(lon.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['T'] = t

# ── U: Faux breakout intra London ──
print("  U (Faux_break_lon)..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                   (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess) < 6: continue
    run_high = sess.iloc[0]['high']; run_low = sess.iloc[0]['low']
    for i in range(1, len(sess)):
        r = sess.iloc[i]
        if r['high'] > run_high and r['close'] < sess.iloc[i-1]['close']:
            if (r['high'] - run_high) > 0.1*atr:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        if r['low'] < run_low and r['close'] > sess.iloc[i-1]['close']:
            if (run_low - r['low']) > 0.1*atr:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        run_high = max(run_high, r['high']); run_low = min(run_low, r['low'])
S['U'] = t

conn.close()

# Legende
LEGEND = {
    'A': 'IB_tok_1h_UP', 'C': 'FADE_tok_lon', 'D': 'GAP_tok_lon',
    'E': 'KZ_lon_fade', 'F': '2BAR_tok_rev', 'G': 'NY1st_candle',
    'H': 'TOKEND_3b', 'I': 'FADENY_1h', 'J': 'LON1st_candle',
    'O': 'BigCandle_tok', 'P': 'ORB_NY30', 'Q': 'Engulfing_lon',
    'R': '3soldiers_tok', 'S': '3soldiers_rev_lon', 'T': 'Lon_fail_Asian',
    'U': 'Faux_break_lon'
}

# Stats individuelles
print("\n" + "="*80)
print("STATS INDIVIDUELLES (16 strats)")
print("="*80)
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 10: print(f"  {sn:2s} ({LEGEND.get(sn,'?'):20s}): n={len(t)} --"); continue
    df = pd.DataFrame(t)
    gp = df[df['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(df[df['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (df['pnl_oz']>0).mean()*100
    ns = (df['dir']=='short').sum(); nl = (df['dir']=='long').sum()
    mid = len(df)//2; f1 = df.iloc[:mid]['pnl_oz'].mean(); f2 = df.iloc[mid:]['pnl_oz'].mean()
    ok = "OK" if f1>0 and f2>0 else "!!"
    print(f"  {sn:2s} ({LEGEND.get(sn,'?'):20s}): n={len(df):4d} ({nl:3d}L {ns:3d}S) WR={wr:.0f}% PF={gp/gl:.2f} [{f1:+.3f}|{f2:+.3f}] {ok}")

# ── Pre-conversion en arrays numpy pour vitesse ──
# Pour chaque strat: array de (ei, xi, dir_int, pnl_oz, sl_atr, atr, date_ordinal, month_str)
# dir_int: 1=long, -1=short
strat_arrays = {}
for sn in S:
    if len(S[sn]) == 0: continue
    rows = []
    for t in S[sn]:
        di = 1 if t['dir'] == 'long' else -1
        do = t['date'].toordinal() if hasattr(t['date'], 'toordinal') else 0
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t['xi'], di, t['pnl_oz'], t['sl_atr'], t['atr'], do, mo, sn))
    strat_arrays[sn] = rows

def eval_combo_fast(combo):
    """Evalue un portfolio sans creer de DataFrame."""
    # Fusionner et trier par (ei, strat_name) pour determinisme
    combined = []
    for sn in combo:
        if sn in strat_arrays:
            combined.extend(strat_arrays[sn])
    if len(combined) < 50: return None
    combined.sort(key=lambda x: (x[0], x[8]))  # tri par ei puis strat

    # Conflict resolution
    active = []  # (xi, dir_int)
    accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, do, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active):
            continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, do, mo, _sn))
        active.append((xi, di))

    n = len(accepted)
    if n < 50: return None

    # Equity simulation
    capital = 10000.0
    peak = capital
    max_dd = 0.0
    gp = 0.0; gl = 0.0; wins = 0
    pnls = []
    months = {}
    has_l = False; has_s = False

    for ei, xi, di, pnl_oz, sl_atr, atr, do, mo, _sn in accepted:
        pnl = pnl_oz * (capital * 0.004) / (sl_atr * atr)
        capital += pnl
        pnls.append(pnl)
        if capital > peak: peak = capital
        dd = (capital - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        months[mo] = months.get(mo, 0.0) + pnl
        if di == 1: has_l = True
        else: has_s = True

    mdd = max_dd * 100
    ret = (capital - 10000) / 100
    pf = gp / (gl + 0.01)
    wr = wins / n * 100
    mid = n // 2
    p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    pm = sum(1 for v in months.values() if v > 0)
    tm = len(months)

    return {
        'combo': '+'.join(combo), 'ns': len(combo), 'n': n, 'tpd': n / n_td,
        'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
        'pf': pf, 'wr': wr,
        'split': p1 > 0 and p2 > 0,
        'tiers': sum(1 for x in [t1, t2, t3] if x > 0),
        'both': has_s and has_l,
        'pm': pm, 'tm': tm,
    }

# ── Combinaisons (6 a 16 strats) ──
all_n = sorted(strat_arrays.keys())
n_strats = len(all_n)
total_combos = sum(1 for sz in range(6, n_strats+1) for _ in combinations(all_n, sz))
print(f"\n{'='*80}", flush=True)
print(f"COMBINAISONS ({total_combos} combos, {n_strats} strats, taille 6-{n_strats})", flush=True)
print(f"{'='*80}", flush=True)

results = []
done = 0
t0 = time.time()

for size in range(6, n_strats+1):
    for combo in combinations(all_n, size):
        done += 1
        if done % 1000 == 0:
            elapsed = time.time() - t0
            speed = done / elapsed if elapsed > 0 else 0
            eta = (total_combos - done) / speed if speed > 0 else 0
            pct = done * 100 // total_combos
            bar = '#' * (pct // 2) + '-' * (50 - pct // 2)
            print(f"\r  [{bar}] {pct:3d}% ({done}/{total_combos}) ETA {eta:.0f}s   ", end='', flush=True)
        r = eval_combo_fast(combo)
        if r is not None:
            results.append(r)

print(f"\n\n  {len(results)} combos valides", flush=True)

rdf = pd.DataFrame(results)
ok = rdf[(rdf['split']) & (rdf['tiers']==3)]

def show(title, sub, col, n=20):
    print(f"\n  {title}")
    print(f"  {'Combo':55s} {'trad':>5s} {'t/j':>4s} {'Rend%':>8s} {'DD%':>7s} {'Cal':>6s} {'PF':>5s} {'WR%':>4s} {'M+':>5s}")
    for _, r in sub.sort_values(col, ascending=False).head(n).iterrows():
        d = "L+S" if r['both'] else "L"
        print(f"  {r['combo'][:55]:55s} {r['n']:5d} {r['tpd']:4.1f} {r['ret']:+7.1f}% {r['mdd']:+6.1f}% {r['cal']:6.1f} {r['pf']:.2f} {r['wr']:3.0f}% {r['pm']:2.0f}/{r['tm']:.0f} {d}")

print("\n  LEGENDE:")
for k in sorted(LEGEND.keys()):
    print(f"    {k} = {LEGEND[k]}")

show("TOP 20 CALMAR (split OK, tiers 3/3, DD>-6%)", ok[ok['mdd']>-6], 'cal', 20)
show("TOP 20 CALMAR (split OK, tiers 3/3, DD>-10%)", ok[ok['mdd']>-10], 'cal', 20)
show("TOP 20 RENDEMENT (split OK, tiers 3/3)", ok, 'ret', 20)
show("TOP 20 PF (split OK, tiers 3/3, n>=500)", ok[ok['n']>=500], 'pf', 20)
show("TOP 20 DIVERSIFIES (L+S, split OK, tiers 3/3, DD>-6%)", ok[(ok['both'])&(ok['mdd']>-6)], 'cal', 20)

print(f"\n{'='*80}")
