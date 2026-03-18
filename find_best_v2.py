"""
Optimisation v2 — toutes les strats incluant les nouvelles.
Strats:
  A: VA short (standard)
  B: IB Tokyo 0h-1h UP
  C: IB Tokyo 0h-30m DOWN
  D: IB Tokyo 5h-5h15 UP (sans filtre body)
  D2: IB Tokyo 5h-5h15 UP + body>50% (ameliore)
  F_fade: Fading Tokyo >1ATR -> inverse a London
  G: London 5 consec bullish
  H: Tokyo engulfing
  J: Tokyo pin bar
  K: Tokyo 4 consec bearish
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import (
    get_conn, SESSIONS_CONFIG, compute_vp, load_ticks_for_period,
    compute_atr, get_trading_days
)
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10

def classify(p, vah, val):
    if p > vah: return 'above'
    elif p < val: return 'below'
    return 'inside'

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

def sim_std(cdf, pos, entry, d, target, stop, mx):
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] >= target: return j, target
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] <= target: return j, target
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

daily_va = {}
for day in trading_days:
    s = datetime(day.year, day.month, day.day, 0, 0)
    p, v = load_ticks_for_period(conn, s, s + timedelta(days=1))
    if len(p) < 100: continue
    poc, vah, val, _ = compute_vp(p, v)
    if vah is not None:
        daily_va[day] = {'poc': poc, 'vah': vah, 'val': val, 'width': vah - val}

va_w = {}
for day, va in daily_va.items():
    atr = daily_atr.get(day, global_atr)
    if atr > 0: va_w[day] = va['width'] / atr

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

def rolling_med(day, w=60):
    di = trading_days.index(day) if day in trading_days else -1
    if di < 1: return None
    vals = [va_w[d] for d in trading_days[max(0,di-w):di] if d in va_w]
    return np.median(vals) if len(vals) >= 10 else None

def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

n_td = len(set(candles['date'].unique()))

print("Collecte des trades...")
S = {}

# A: VA short
print("  A...")
t = []; prev_d = None; prev_vr = None; cd = -1
for idx in range(3, len(candles)):
    r = candles.iloc[idx]; day = r['date']; price = r['close']
    if day.weekday() == 2: continue
    pd_ = prev_day(day)
    if not pd_: prev_d = None; prev_vr = None; continue
    dv = daily_va.get(pd_)
    if not dv: prev_d = None; prev_vr = None; continue
    atr = daily_atr.get(pd_, global_atr)
    if atr == 0: continue
    if pd_ != prev_vr: prev_d = None; prev_vr = pd_
    rm = rolling_med(day)
    if rm is None: prev_d = classify(price, dv['vah'], dv['val']); continue
    pos = classify(price, dv['vah'], dv['val'])
    if pos == 'below' and prev_d == 'inside' and (dv['width']/atr) <= rm and idx > cd:
        bear = (candles.iloc[idx-3:idx]['close'] < candles.iloc[idx-3:idx]['open']).sum()
        if bear >= 2:
            bars, ex = sim_std(candles, idx, price, 'short', price-2.0*atr, price+1.25*atr, 48)
            t.append({'date': day, 'dir': 'short', 'sl_atr': 1.25,
                'pnl_oz': (price-ex) - get_sp(day), 'atr': atr, 'ei': idx, 'xi': idx+bars})
            cd = idx + max(bars, 6)
    prev_d = pos
S['A'] = t

# IB strats
for sn, sh, eh, sm, em, ib_b, d, sl, act, trail in [
    ('B', 0, 6, 0, 0, 12, 'long', 0.75, 0.5, 0.3),
    ('C', 0, 6, 0, 0, 6, 'short', 0.75, 0.5, 0.3),
    ('D', 5, 6, 0, 0, 3, 'long', 1.0, 1.0, 0.5),
]:
    print("  {}...".format(sn))
    t = []
    for day in trading_days:
        obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
        period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
        if len(period) < ib_b + 6: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ib = period.iloc[:ib_b]
        lvl = ib['high'].max() if d == 'long' else ib['low'].min()
        for i in range(ib_b, len(period)):
            r = period.iloc[i]
            trig = (d == 'long' and r['close'] > lvl) or (d == 'short' and r['close'] < lvl)
            if trig:
                pos_i = candles.index.get_loc(period.index[i])
                entry = r['close']
                bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                t.append({'date': day, 'dir': d, 'sl_atr': sl,
                    'pnl_oz': pnl - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
                break
    S[sn] = t

# D2: IB Tokyo 5h UP + body>50%
print("  D2...")
t = []
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 5, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
    if len(period) < 6: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ib_high = period.iloc[:3]['high'].max()
    for i in range(3, len(period)):
        r = period.iloc[i]
        if r['close'] > ib_high:
            body = abs(r['close'] - r['open'])
            rng = r['high'] - r['low']
            if rng > 0 and body / rng >= 0.5:
                pos_i = candles.index.get_loc(period.index[i])
                entry = r['close']
                bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
                t.append({'date': day, 'dir': 'long', 'sl_atr': 0.75,
                    'pnl_oz': (ex-entry) - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
S['D2'] = t

# FADE: Fading Tokyo >1ATR
print("  FADE...")
t = []
for day in trading_days:
    tok_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    tok_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    tok = candles[(candles['ts_dt'] >= tok_s) & (candles['ts_dt'] < tok_e)]
    if len(tok) < 10: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok_move = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    if abs(tok_move) < 1.0: continue
    lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    lon = candles[candles['ts_dt'] >= lon_s]
    if len(lon) < 6: continue
    pos_i = candles.index.get_loc(lon.index[0])
    entry = lon.iloc[0]['open']
    d = 'short' if tok_move > 0 else 'long'
    bars, ex = sim_trail(candles, pos_i, entry, d, 0.75, atr, 24, 0.5, 0.3)
    pnl = (ex-entry) if d == 'long' else (entry-ex)
    t.append({'date': day, 'dir': d, 'sl_atr': 0.75,
        'pnl_oz': pnl - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
S['FADE'] = t

# G: London 5 bull
print("  G...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                     (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(period) < 11: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(5, len(period)):
        if (period.iloc[i-5:i]['close'] > period.iloc[i-5:i]['open']).all():
            pos_i = candles.index.get_loc(period.index[i-1])
            entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            t.append({'date': day, 'dir': 'long', 'sl_atr': 0.75,
                'pnl_oz': (ex-entry) - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
S['G'] = t

# H: Tokyo engulfing
print("  H...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                     (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 8: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(period)):
        pc = period.iloc[i-1]; cc = period.iloc[i]
        pb = abs(pc['close']-pc['open']); cb = abs(cc['close']-cc['open'])
        bull = (pc['close']<pc['open'] and cc['close']>cc['open'] and cb>pb and
                cc['open']<=pc['close'] and cc['close']>=pc['open'])
        bear = (pc['close']>pc['open'] and cc['close']<cc['open'] and cb>pb and
                cc['open']>=pc['close'] and cc['close']<=pc['open'])
        if bull or bear:
            pos_i = candles.index.get_loc(period.index[i])
            entry = cc['close']; d = 'long' if bull else 'short'
            bars, ex = sim_trail(candles, pos_i, entry, d, 0.75, atr, 24, 0.5, 0.3)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            t.append({'date': day, 'dir': d, 'sl_atr': 0.75,
                'pnl_oz': pnl - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
S['H'] = t

# J: Tokyo pin bar
print("  J...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                     (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 8: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(period)):
        r = period.iloc[i]
        body = abs(r['close']-r['open'])
        if body < 0.01: continue
        uw = r['high'] - max(r['close'],r['open'])
        lw = min(r['close'],r['open']) - r['low']
        if lw > 2*body and uw < body:
            pos_i = candles.index.get_loc(period.index[i])
            entry = r['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            t.append({'date': day, 'dir': 'long', 'sl_atr': 0.75,
                'pnl_oz': (ex-entry) - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
        elif uw > 2*body and lw < body:
            pos_i = candles.index.get_loc(period.index[i])
            entry = r['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'short', 0.75, atr, 24, 0.5, 0.3)
            t.append({'date': day, 'dir': 'short', 'sl_atr': 0.75,
                'pnl_oz': (entry-ex) - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
S['J'] = t

# K: Tokyo 4 consec bearish
print("  K...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                     (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 10: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(4, len(period)):
        if (period.iloc[i-4:i]['close'] < period.iloc[i-4:i]['open']).all():
            pos_i = candles.index.get_loc(period.index[i-1])
            entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'short', 1.0, atr, 24, 1.0, 0.5)
            t.append({'date': day, 'dir': 'short', 'sl_atr': 1.0,
                'pnl_oz': (entry-ex) - get_sp(day), 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
S['K'] = t

# Stats
print("\n" + "=" * 80)
print("STATS INDIVIDUELLES")
print("=" * 80)
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 10: print("  {}: n={} --".format(sn, len(t))); continue
    df = pd.DataFrame(t)
    gp = df[df['pnl_oz']>0]['pnl_oz'].sum()
    gl = abs(df[df['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (df['pnl_oz']>0).mean()*100
    ns = (df['dir']=='short').sum(); nl = (df['dir']=='long').sum()
    mid = len(df)//2
    f1 = df.iloc[:mid]['pnl_oz'].mean(); f2 = df.iloc[mid:]['pnl_oz'].mean()
    ok = "OK" if f1>0 and f2>0 else "!!"
    print("  {:6s}: n={:4d} ({:3d}L {:3d}S) WR={:.0f}% PF={:.2f} {:.1f}t/j [{:+.2f}|{:+.2f}] {}".format(
        sn, len(df), nl, ns, wr, gp/gl, len(df)/n_td, f1, f2, ok))

# Toutes les combinaisons
print("\n" + "=" * 80)
print("TOUTES COMBINAISONS (risk 0.4%)")
print("=" * 80)

all_names = sorted(S.keys())
results = []

for size in range(2, len(all_names)+1):
    for combo in combinations(all_names, size):
        # Skip D et D2 ensemble (redondant)
        if 'D' in combo and 'D2' in combo: continue

        combined = []
        for sn in combo:
            for t in S[sn]:
                combined.append({**t, 'strat': sn})
        if len(combined) < 50: continue

        cdf = pd.DataFrame(combined).sort_values('ei').reset_index(drop=True)
        al = []; acc = []
        for _, t in cdf.iterrows():
            al = [(ei, d) for ei, d in al if ei >= t['ei']]
            if not any(d != t['dir'] for _, d in al):
                acc.append(t.to_dict())
                al.append((t['xi'], t['dir']))

        df = pd.DataFrame(acc)
        if len(df) < 50: continue

        capital = 10000.0; recs = []
        for _, t in df.iterrows():
            pnl = t['pnl_oz'] * (capital * 0.004) / (t['sl_atr'] * t['atr'])
            capital += pnl
            recs.append({'capital': capital, 'pnl': pnl, 'date': t['date'],
                         'month': str(t['date'].year)+"-"+str(t['date'].month).zfill(2)})

        eq = pd.DataFrame(recs)
        pk = eq['capital'].cummax()
        mdd = ((eq['capital']-pk)/pk).min()*100
        ret = (capital-10000)/100
        wins = eq[eq['pnl']>0]
        gp = wins['pnl'].sum() if len(wins)>0 else 0
        gl = abs(eq[eq['pnl']<0]['pnl'].sum())+0.01
        mp = eq.groupby('month')['pnl'].sum()
        mid = len(eq)//2
        p1 = eq.iloc[:mid]['pnl'].sum(); p2 = eq.iloc[mid:]['pnl'].sum()
        has_s = any(t['dir']=='short' for t in acc)
        has_l = any(t['dir']=='long' for t in acc)
        t1 = eq.iloc[:len(eq)//3]['pnl'].sum()
        t2 = eq.iloc[len(eq)//3:2*len(eq)//3]['pnl'].sum()
        t3 = eq.iloc[2*len(eq)//3:]['pnl'].sum()

        results.append({
            'combo': '+'.join(combo), 'n_strats': len(combo),
            'n': len(df), 'tpd': len(df)/n_td,
            'ret': ret, 'mdd': mdd, 'cal': ret/abs(mdd) if mdd<0 else 0,
            'pf': gp/gl, 'wr': len(wins)/len(eq)*100,
            'split': p1>0 and p2>0, 'tiers': sum(1 for x in [t1,t2,t3] if x>0),
            'both': has_s and has_l,
            'pm': (mp>0).sum(), 'tm': len(mp),
        })

rdf = pd.DataFrame(results)
ok = rdf[(rdf['split']) & (rdf['tiers']==3)]

def show(title, sub, col, n=10):
    print("\n  " + title)
    print("  {:35s} {:>5s} {:>4s} {:>7s} {:>6s} {:>5s} {:>5s} {:>4s} {:>5s}".format(
        "Combo","trad","t/j","Rend%","DD%","Cal","PF","WR%","M+"))
    for _, r in sub.sort_values(col, ascending=False).head(n).iterrows():
        d = "L+S" if r['both'] else "L"
        print("  {:35s} {:5d} {:4.1f} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:3.0f}% {:2.0f}/{:.0f} {}".format(
            r['combo'][:35], r['n'], r['tpd'], r['ret'], r['mdd'], r['cal'], r['pf'], r['wr'], r['pm'], r['tm'], d))

show("TOP 10 RENDEMENT (split OK, tiers 3/3)", ok, 'ret')
show("TOP 10 CALMAR (split OK, tiers 3/3, DD>-5%)", ok[ok['mdd']>-5], 'cal')
show("TOP 10 CALMAR (split OK, tiers 3/3, DD>-8%)", ok[ok['mdd']>-8], 'cal')
show("TOP 10 PF (split OK, tiers 3/3, n>=300)", ok[ok['n']>=300], 'pf')
show("TOP 10 DIVERSIFIES L+S (split OK, tiers 3/3, DD>-5%)", ok[(ok['both'])&(ok['mdd']>-5)], 'cal')

conn.close()
print("\n" + "=" * 80)
