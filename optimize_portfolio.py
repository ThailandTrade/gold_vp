"""
Optimisation portfolio — teste TOUTES les combinaisons de strats
pour trouver le meilleur rendement/DD/PF.
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

def sim_trail(cdf, pos, entry, d, sl_atr, atr, mx, act, trail):
    best = entry
    stop = entry + sl_atr*atr if d == 'short' else entry - sl_atr*atr
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

va_w_by_date = {}
for day, va in daily_va.items():
    atr = daily_atr.get(day, global_atr)
    if atr > 0: va_w_by_date[day] = va['width'] / atr

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

def rolling_med(day, w=60):
    di = trading_days.index(day) if day in trading_days else -1
    if di < 1: return None
    recent = trading_days[max(0, di-w):di]
    vals = [va_w_by_date[d] for d in recent if d in va_w_by_date]
    if len(vals) < 10: return None
    return np.median(vals)

def get_spread(day):
    mk = str(day.year) + "-" + str(day.month).zfill(2)
    return 2 * monthly_spread.get(mk, avg_sp)

print("Collecte de tous les trades par strat...")

# Collecter TOUS les trades de TOUTES les strats dans un dict
all_strat_trades = {}

# A: VA short
print("  A...")
trades_a = []
prev_d = None; prev_va_ref = None; cd = -1
for idx in range(3, len(candles)):
    r = candles.iloc[idx]; day = r['date']; price = r['close']
    if day.weekday() == 2: continue
    pd_ = prev_day(day)
    if not pd_: prev_d = None; prev_va_ref = None; continue
    dv = daily_va.get(pd_)
    if not dv: prev_d = None; prev_va_ref = None; continue
    atr = daily_atr.get(pd_, global_atr)
    if atr == 0: continue
    if pd_ != prev_va_ref: prev_d = None; prev_va_ref = pd_
    rm = rolling_med(day)
    if rm is None: prev_d = classify(price, dv['vah'], dv['val']); continue
    pos = classify(price, dv['vah'], dv['val'])
    if pos == 'below' and prev_d == 'inside' and (dv['width']/atr) <= rm and idx > cd:
        bear = (candles.iloc[idx-3:idx]['close'] < candles.iloc[idx-3:idx]['open']).sum()
        if bear >= 2:
            bars, ex = sim_std(candles, idx, price, 'short', price-2.0*atr, price+1.25*atr, 48)
            sp = get_spread(day)
            trades_a.append({'date': day, 'dir': 'short', 'sl_atr': 1.25,
                'pnl_oz': (price-ex) - sp, 'atr': atr, 'ei': idx, 'xi': idx+bars})
            cd = idx + max(bars, 6)
    prev_d = pos
all_strat_trades['A'] = trades_a

# IB strats
for sn, sh, eh, sm, em, ib_b, d, sl, act, trail in [
    ('B', 0, 6, 0, 0, 12, 'long', 0.75, 0.5, 0.3),
    ('C', 0, 6, 0, 0, 6, 'short', 0.75, 0.5, 0.3),
    ('D', 5, 6, 0, 0, 3, 'long', 1.0, 1.0, 0.5),
    ('E', 14, 21, 30, 30, 12, 'long', 1.0, 0.75, 0.5),
]:
    print("  {}...".format(sn))
    trades = []
    for day in trading_days:
        obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
        mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
        period = candles[mask]
        if len(period) < ib_b + 6: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ib = period.iloc[:ib_b]
        lvl = ib['high'].max() if d == 'long' else ib['low'].min()
        rest = period.iloc[ib_b:]
        for i in range(len(rest)):
            r = rest.iloc[i]
            trig = (d == 'long' and r['close'] > lvl) or (d == 'short' and r['close'] < lvl)
            if trig:
                pos_i = candles.index.get_loc(rest.index[i])
                entry = r['close']
                bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                pnl_oz = (ex-entry) if d == 'long' else (entry-ex)
                sp = get_spread(day)
                trades.append({'date': day, 'dir': d, 'sl_atr': sl,
                    'pnl_oz': pnl_oz - sp, 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
                break
    all_strat_trades[sn] = trades

# Graal strats
print("  F...")
trades_f = []
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 9: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(3, len(period)):
        prev3 = period.iloc[i-3:i]
        if (prev3['close'] > prev3['open']).all():
            pos_i = candles.index.get_loc(period.index[i-1])
            entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            trades_f.append({'date': day, 'dir': 'long', 'sl_atr': 0.75,
                'pnl_oz': (ex-entry) - sp, 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
all_strat_trades['F'] = trades_f

print("  G...")
trades_g = []
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 11: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(5, len(period)):
        prev5 = period.iloc[i-5:i]
        if (prev5['close'] > prev5['open']).all():
            pos_i = candles.index.get_loc(period.index[i-1])
            entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            trades_g.append({'date': day, 'dir': 'long', 'sl_atr': 0.75,
                'pnl_oz': (ex-entry) - sp, 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
all_strat_trades['G'] = trades_g

print("  H...")
trades_h = []
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 8: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(period)):
        prev_c = period.iloc[i-1]; curr = period.iloc[i]
        pb = abs(prev_c['close'] - prev_c['open'])
        cb = abs(curr['close'] - curr['open'])
        bull = (prev_c['close'] < prev_c['open'] and curr['close'] > curr['open'] and
                cb > pb and curr['open'] <= prev_c['close'] and curr['close'] >= prev_c['open'])
        bear = (prev_c['close'] > prev_c['open'] and curr['close'] < curr['open'] and
                cb > pb and curr['open'] >= prev_c['close'] and curr['close'] <= prev_c['open'])
        if bull or bear:
            pos_i = candles.index.get_loc(period.index[i])
            entry = curr['close']
            d = 'long' if bull else 'short'
            bars, ex = sim_trail(candles, pos_i, entry, d, 0.75, atr, 24, 0.5, 0.3)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            sp = get_spread(day)
            trades_h.append({'date': day, 'dir': d, 'sl_atr': 0.75,
                'pnl_oz': pnl - sp, 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
all_strat_trades['H'] = trades_h

print("  I...")
trades_i = []
for day in trading_days:
    lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    lon_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    lon = candles[(candles['ts_dt'] >= lon_s) & (candles['ts_dt'] < lon_e)]
    if len(lon) < 10: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lon_high = lon['high'].max()
    ny_s = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    ny_e = pd.Timestamp(day.year, day.month, day.day, 21, 30, tz='UTC')
    ny = candles[(candles['ts_dt'] >= ny_s) & (candles['ts_dt'] < ny_e)]
    if len(ny) < 6: continue
    for i in range(len(ny)):
        r = ny.iloc[i]
        if r['close'] > lon_high:
            pos_i = candles.index.get_loc(ny.index[i])
            entry = r['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            trades_i.append({'date': day, 'dir': 'long', 'sl_atr': 0.75,
                'pnl_oz': (ex-entry) - sp, 'atr': atr, 'ei': pos_i, 'xi': pos_i+bars})
            break
all_strat_trades['I'] = trades_i

# Stats individuelles
print("\n" + "=" * 80)
print("STATS INDIVIDUELLES")
print("=" * 80)
for sn in sorted(all_strat_trades.keys()):
    trades = all_strat_trades[sn]
    if len(trades) < 10: continue
    df = pd.DataFrame(trades)
    gp = df[df['pnl_oz'] > 0]['pnl_oz'].sum()
    gl = abs(df[df['pnl_oz'] < 0]['pnl_oz'].sum()) + 0.001
    wr = (df['pnl_oz'] > 0).mean() * 100
    mid = len(df) // 2
    f1 = df.iloc[:mid]['pnl_oz'].mean()
    f2 = df.iloc[mid:]['pnl_oz'].mean()
    ok = "OK" if f1 > 0 and f2 > 0 else "!!"
    print("  {}: n={:4d} WR={:.0f}% PF={:.2f} [{:+.3f}|{:+.3f}] {}".format(
        sn, len(df), wr, gp/gl, f1, f2, ok))

# ══════════════════════════════════════════════════════
# TEST TOUTES LES COMBINAISONS de 3 a 9 strats
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("TOUTES LES COMBINAISONS (risk 0.25%)")
print("=" * 80)

all_strats = sorted(all_strat_trades.keys())
results = []

for size in range(2, len(all_strats) + 1):
    for combo in combinations(all_strats, size):
        # Combiner les trades
        combined = []
        for sn in combo:
            for t in all_strat_trades[sn]:
                combined.append({**t, 'strat': sn})

        cdf = pd.DataFrame(combined).sort_values('ei').reset_index(drop=True)

        # Conflits
        act_list = []; acc = []
        for _, t in cdf.iterrows():
            act_list = [(ei, d) for ei, d in act_list if ei >= t['ei']]
            if not any(d != t['dir'] for _, d in act_list):
                acc.append(t.to_dict())
                act_list.append((t['xi'], t['dir']))

        df = pd.DataFrame(acc)
        if len(df) < 50: continue

        # Simulation
        capital = 10000.0
        recs = []
        for _, t in df.iterrows():
            pos_oz = (capital * 0.0025) / (t['sl_atr'] * t['atr'])
            pnl = t['pnl_oz'] * pos_oz
            capital += pnl
            recs.append({'capital': capital, 'pnl': pnl})

        eq = pd.DataFrame(recs)
        pk = eq['capital'].cummax()
        mdd = ((eq['capital'] - pk) / pk).min() * 100
        ret = (capital - 10000) / 100
        wins = eq[eq['pnl'] > 0]
        gp = wins['pnl'].sum() if len(wins) > 0 else 0
        gl = abs(eq[eq['pnl'] < 0]['pnl'].sum()) + 0.01
        pf = gp / gl
        wr = len(wins) / len(eq) * 100

        mid = len(eq) // 2
        p1 = eq.iloc[:mid]['pnl'].sum()
        p2 = eq.iloc[mid:]['pnl'].sum()
        split_ok = p1 > 0 and p2 > 0

        has_short = any(t['dir'] == 'short' for t in acc)
        has_long = any(t['dir'] == 'long' for t in acc)

        results.append({
            'combo': '+'.join(combo),
            'n_strats': len(combo),
            'n_trades': len(df),
            'ret': ret,
            'mdd': mdd,
            'calmar': ret / abs(mdd) if mdd < 0 else 0,
            'pf': pf,
            'wr': wr,
            'split_ok': split_ok,
            'has_both_dirs': has_short and has_long,
        })

rdf = pd.DataFrame(results)

# Top par rendement (split OK)
print("\n  TOP 15 par RENDEMENT (split OK):")
top_ret = rdf[rdf['split_ok']].sort_values('ret', ascending=False).head(15)
print("  {:40s} {:>5s} {:>5s} {:>7s} {:>6s} {:>5s} {:>5s} {:>5s}".format(
    "Combo", "n", "trad", "Rend%", "DD%", "Cal", "PF", "WR%"))
for _, r in top_ret.iterrows():
    both = "L+S" if r['has_both_dirs'] else "L" if 'long' in str(r['combo']) else "S"
    print("  {:40s} {:5d} {:5d} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:4.0f}% {}".format(
        r['combo'], r['n_strats'], r['n_trades'], r['ret'], r['mdd'],
        r['calmar'], r['pf'], r['wr'], both))

# Top par Calmar (split OK, DD < 6%)
print("\n  TOP 15 par CALMAR (split OK, DD > -6%):")
top_cal = rdf[(rdf['split_ok']) & (rdf['mdd'] > -6)].sort_values('calmar', ascending=False).head(15)
for _, r in top_cal.iterrows():
    both = "L+S" if r['has_both_dirs'] else "L"
    print("  {:40s} {:5d} {:5d} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:4.0f}% {}".format(
        r['combo'], r['n_strats'], r['n_trades'], r['ret'], r['mdd'],
        r['calmar'], r['pf'], r['wr'], both))

# Top par PF (split OK)
print("\n  TOP 15 par PF (split OK):")
top_pf = rdf[rdf['split_ok']].sort_values('pf', ascending=False).head(15)
for _, r in top_pf.iterrows():
    both = "L+S" if r['has_both_dirs'] else "L"
    print("  {:40s} {:5d} {:5d} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:4.0f}% {}".format(
        r['combo'], r['n_strats'], r['n_trades'], r['ret'], r['mdd'],
        r['calmar'], r['pf'], r['wr'], both))

# Meilleur avec diversification L+S
print("\n  TOP 10 DIVERSIFIES (long+short, split OK, DD > -6%):")
top_div = rdf[(rdf['split_ok']) & (rdf['has_both_dirs']) & (rdf['mdd'] > -6)].sort_values('calmar', ascending=False).head(10)
for _, r in top_div.iterrows():
    print("  {:40s} {:5d} {:5d} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:4.0f}%".format(
        r['combo'], r['n_strats'], r['n_trades'], r['ret'], r['mdd'],
        r['calmar'], r['pf'], r['wr']))

conn.close()
print("\n" + "=" * 80)
