"""
Optimisation v3 — ajout London KZ fade, Gap continuation, Two-bar reversal.
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

print("Collecte...")
S = {}

# === STRATS EXISTANTES ===

# A
print("  A..."); t = []; prev_d = None; prev_vr = None; cd = -1
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
            t.append({'date': day, 'dir': 'short', 'sl_atr': 1.25, 'pnl_oz': (price-ex)-get_sp(day), 'atr': atr, 'ei': idx, 'xi': idx+bars})
            cd = idx + max(bars, 6)
    prev_d = pos
S['A'] = t

# B
print("  B...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 18: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lvl = period.iloc[:12]['high'].max()
    for i in range(12, len(period)):
        if period.iloc[i]['close'] > lvl:
            pi = candles.index.get_loc(period.index[i]); entry = period.iloc[i]['close']
            bars, ex = sim_trail(candles, pi, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            t.append({'date': day, 'dir': 'long', 'sl_atr': 0.75, 'pnl_oz': (ex-entry)-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars}); break
S['B'] = t

# D2
print("  D2...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,5,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lvl = period.iloc[:3]['high'].max()
    for i in range(3, len(period)):
        r = period.iloc[i]
        if r['close'] > lvl:
            body = abs(r['close']-r['open']); rng = r['high']-r['low']
            if rng > 0 and body/rng >= 0.5:
                pi = candles.index.get_loc(period.index[i]); entry = r['close']
                bars, ex = sim_trail(candles, pi, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
                t.append({'date': day, 'dir': 'long', 'sl_atr': 0.75, 'pnl_oz': (ex-entry)-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars})
            break
S['D2'] = t

# FADE
print("  FADE...")
t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_move = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    if abs(tok_move) < 1.0: continue
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0]); entry = lon.iloc[0]['open']
    d = 'short' if tok_move > 0 else 'long'
    bars, ex = sim_trail(candles, pi, entry, d, 0.75, atr, 24, 0.5, 0.3)
    pnl = (ex-entry) if d == 'long' else (entry-ex)
    t.append({'date': day, 'dir': d, 'sl_atr': 0.75, 'pnl_oz': pnl-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars})
S['FADE'] = t

# G
print("  G...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(period) < 11: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(5, len(period)):
        if (period.iloc[i-5:i]['close'] > period.iloc[i-5:i]['open']).all():
            pi = candles.index.get_loc(period.index[i-1]); entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pi, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            t.append({'date': day, 'dir': 'long', 'sl_atr': 0.75, 'pnl_oz': (ex-entry)-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars}); break
S['G'] = t

# H
print("  H...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 8: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(period)):
        pc = period.iloc[i-1]; cc = period.iloc[i]
        pb = abs(pc['close']-pc['open']); cb = abs(cc['close']-cc['open'])
        bull = (pc['close']<pc['open'] and cc['close']>cc['open'] and cb>pb and cc['open']<=pc['close'] and cc['close']>=pc['open'])
        bear = (pc['close']>pc['open'] and cc['close']<cc['open'] and cb>pb and cc['open']>=pc['close'] and cc['close']<=pc['open'])
        if bull or bear:
            pi = candles.index.get_loc(period.index[i]); entry = cc['close']; d = 'long' if bull else 'short'
            bars, ex = sim_trail(candles, pi, entry, d, 0.75, atr, 24, 0.5, 0.3)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            t.append({'date': day, 'dir': d, 'sl_atr': 0.75, 'pnl_oz': pnl-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars}); break
S['H'] = t

# === NOUVELLES STRATS ===

# KZ: London Kill Zone fade (8h-10h move -> inverse a 10h)
print("  KZ...")
t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    kz = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz) < 20: continue
    kz_move = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
    if abs(kz_move) < 0.5: continue
    post = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
    if len(post) < 6: continue
    pi = candles.index.get_loc(post.index[0]); entry = post.iloc[0]['open']
    d = 'short' if kz_move > 0 else 'long'
    bars, ex = sim_trail(candles, pi, entry, d, 0.75, atr, 24, 0.5, 0.3)
    pnl = (ex-entry) if d == 'long' else (entry-ex)
    t.append({'date': day, 'dir': d, 'sl_atr': 0.75, 'pnl_oz': pnl-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars})
S['KZ'] = t

# GAP: Gap Tokyo-London continuation
print("  GAP...")
t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok_e = pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')
    tok_c = candles[candles['ts_dt'] < tok_e]
    if len(tok_c) < 5: continue
    tok_close = tok_c.iloc[-1]['close']
    lon_s = pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')
    lon = candles[candles['ts_dt'] >= lon_s]
    if len(lon) < 6: continue
    lon_open = lon.iloc[0]['open']
    gap = (lon_open - tok_close) / atr
    if abs(gap) < 0.5: continue
    pi = candles.index.get_loc(lon.index[0]); entry = lon_open
    d = 'long' if gap > 0 else 'short'  # continuation
    bars, ex = sim_trail(candles, pi, entry, d, 0.75, atr, 24, 0.5, 0.3)
    pnl = (ex-entry) if d == 'long' else (entry-ex)
    t.append({'date': day, 'dir': d, 'sl_atr': 0.75, 'pnl_oz': pnl-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars})
S['GAP'] = t

# 2BAR: Tokyo two-bar reversal
print("  2BAR...")
t = []
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 8: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(period)):
        b1 = period.iloc[i-1]; b2 = period.iloc[i]
        b1b = b1['close']-b1['open']; b2b = b2['close']-b2['open']
        if abs(b1b) < 0.5*atr: continue
        if abs(b2b) < 0.5*atr: continue
        if b1b * b2b >= 0: continue
        if abs(b2b) <= abs(b1b): continue
        pi = candles.index.get_loc(period.index[i]); entry = b2['close']
        d = 'long' if b2b > 0 else 'short'
        bars, ex = sim_trail(candles, pi, entry, d, 0.75, atr, 24, 0.5, 0.3)
        pnl = (ex-entry) if d == 'long' else (entry-ex)
        t.append({'date': day, 'dir': d, 'sl_atr': 0.75, 'pnl_oz': pnl-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars}); break
S['2BAR'] = t

# Stats
print("\n" + "=" * 80)
print("STATS INDIVIDUELLES")
print("=" * 80)
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 10: print("  {}: n={} --".format(sn, len(t))); continue
    df = pd.DataFrame(t)
    gp = df[df['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(df[df['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (df['pnl_oz']>0).mean()*100
    ns = (df['dir']=='short').sum(); nl = (df['dir']=='long').sum()
    mid = len(df)//2; f1 = df.iloc[:mid]['pnl_oz'].mean(); f2 = df.iloc[mid:]['pnl_oz'].mean()
    ok = "OK" if f1>0 and f2>0 else "!!"
    print("  {:6s}: n={:4d} ({:3d}L {:3d}S) WR={:.0f}% PF={:.2f} {:.1f}t/j [{:+.2f}|{:+.2f}] {}".format(
        sn, len(df), nl, ns, wr, gp/gl, len(df)/n_td, f1, f2, ok))

# Combinaisons
print("\n" + "=" * 80)
print("COMBINAISONS (risk 0.4%)")
print("=" * 80)

all_n = sorted(S.keys())
results = []

for size in range(2, min(len(all_n)+1, 8)):  # max 7 strats pour limiter le temps
    for combo in combinations(all_n, size):
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
            pnl = t['pnl_oz'] * (capital*0.004)/(t['sl_atr']*t['atr'])
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
            'combo': '+'.join(combo), 'ns': len(combo), 'n': len(df), 'tpd': len(df)/n_td,
            'ret': ret, 'mdd': mdd, 'cal': ret/abs(mdd) if mdd<0 else 0,
            'pf': gp/gl, 'wr': len(wins)/len(eq)*100,
            'split': p1>0 and p2>0, 'tiers': sum(1 for x in [t1,t2,t3] if x>0),
            'both': has_s and has_l, 'pm': (mp>0).sum(), 'tm': len(mp),
        })

rdf = pd.DataFrame(results)
ok = rdf[(rdf['split']) & (rdf['tiers']==3)]

def show(title, sub, col, n=10):
    print("\n  " + title)
    print("  {:40s} {:>5s} {:>4s} {:>7s} {:>6s} {:>5s} {:>5s} {:>4s} {:>5s}".format(
        "Combo","trad","t/j","Rend%","DD%","Cal","PF","WR%","M+"))
    for _, r in sub.sort_values(col, ascending=False).head(n).iterrows():
        d = "L+S" if r['both'] else "L"
        print("  {:40s} {:5d} {:4.1f} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:3.0f}% {:2.0f}/{:.0f} {}".format(
            r['combo'][:40], r['n'], r['tpd'], r['ret'], r['mdd'], r['cal'], r['pf'], r['wr'], r['pm'], r['tm'], d))

show("TOP 10 RENDEMENT (split OK, tiers 3/3)", ok, 'ret')
show("TOP 10 CALMAR (split OK, tiers 3/3, DD>-6%)", ok[ok['mdd']>-6], 'cal')
show("TOP 10 PF (split OK, tiers 3/3, n>=300)", ok[ok['n']>=300], 'pf')
show("TOP 10 DIVERSIFIES (L+S, split OK, tiers 3/3, DD>-6%)", ok[(ok['both'])&(ok['mdd']>-6)], 'cal')

conn.close()
print("\n" + "=" * 80)
