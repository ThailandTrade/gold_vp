"""
Portfolio elargi — strats existantes + nouveaux signaux graal.
Nouveau fichier, ne touche pas au backtest existant.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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
SPREAD_RT = 2 * avg_sp

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

print("=" * 80)
print("PORTFOLIO ELARGI — existantes + graal")
print("Spread RT {:.3f} + slippage {:.2f} inclus".format(SPREAD_RT, SLIPPAGE))
print("=" * 80)

candidates = []

# ══════════════════════════════════════════════════════
# STRATS EXISTANTES (identiques a portfolio_final_clean.py)
# ══════════════════════════════════════════════════════

print("Strat A (VA short)...")
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
            candidates.append({'date': day, 'strat': 'A_VA_short', 'dir': 'short',
                'sl_atr': 1.25, 'pnl_oz': (price-ex) - sp, 'atr': atr,
                'ei': idx, 'xi': idx+bars})
            cd = idx + max(bars, 6)
    prev_d = pos

for sn, sh, eh, sm, em, ib_b, d, sl, act, trail in [
    ('B_tok_0h1h_UP', 0, 6, 0, 0, 12, 'long', 0.75, 0.5, 0.3),
    ('C_tok_0h30m_DN', 0, 6, 0, 0, 6, 'short', 0.75, 0.5, 0.3),
    ('D_tok_5h15m_UP', 5, 6, 0, 0, 3, 'long', 1.0, 1.0, 0.5),
    ('E_ny_1h_UP', 14, 21, 30, 30, 12, 'long', 1.0, 0.75, 0.5),
]:
    print("Strat {}...".format(sn))
    for day in trading_days:
        obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
        mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
        period = candles[mask]
        if len(period) < ib_b + 6: continue
        prev_d_ib = prev_day(day)
        atr = daily_atr.get(prev_d_ib, global_atr) if prev_d_ib else global_atr
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
                pnl_oz = (ex - entry) if d == 'long' else (entry - ex)
                sp = get_spread(day)
                candidates.append({'date': day, 'strat': sn, 'dir': d,
                    'sl_atr': sl, 'pnl_oz': pnl_oz - sp, 'atr': atr,
                    'ei': pos_i, 'xi': pos_i+bars})
                break

# ══════════════════════════════════════════════════════
# NOUVELLES STRATS GRAAL
# ══════════════════════════════════════════════════════

# F: Tokyo 3 consec BULL (PF 1.88)
print("Strat F (Tokyo 3 consec bull)...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 9: continue
    prev_d_atr = prev_day(day)
    atr = daily_atr.get(prev_d_atr, global_atr) if prev_d_atr else global_atr
    if atr == 0: continue
    traded = False
    for i in range(3, len(period)):
        if traded: break
        prev3 = period.iloc[i-3:i]
        if (prev3['close'] > prev3['open']).all():
            pos_i = candles.index.get_loc(period.index[i-1])
            entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'F_tok_3bull', 'dir': 'long',
                'sl_atr': 0.75, 'pnl_oz': (ex - entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            traded = True

# G: London 5 consec BULL (PF 1.68)
print("Strat G (London 5 consec bull)...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 11: continue
    prev_d_atr = prev_day(day)
    atr = daily_atr.get(prev_d_atr, global_atr) if prev_d_atr else global_atr
    if atr == 0: continue
    traded = False
    for i in range(5, len(period)):
        if traded: break
        prev5 = period.iloc[i-5:i]
        if (prev5['close'] > prev5['open']).all():
            pos_i = candles.index.get_loc(period.index[i-1])
            entry = period.iloc[i-1]['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'G_lon_5bull', 'dir': 'long',
                'sl_atr': 0.75, 'pnl_oz': (ex - entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            traded = True

# H: Tokyo engulfing (PF 1.54, n=259)
print("Strat H (Tokyo engulfing)...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 8: continue
    prev_d_atr = prev_day(day)
    atr = daily_atr.get(prev_d_atr, global_atr) if prev_d_atr else global_atr
    if atr == 0: continue
    traded = False
    for i in range(1, len(period)):
        if traded: break
        prev_c = period.iloc[i-1]; curr = period.iloc[i]
        prev_body = abs(prev_c['close'] - prev_c['open'])
        curr_body = abs(curr['close'] - curr['open'])
        bull = (prev_c['close'] < prev_c['open'] and curr['close'] > curr['open'] and
                curr_body > prev_body and curr['open'] <= prev_c['close'] and curr['close'] >= prev_c['open'])
        bear = (prev_c['close'] > prev_c['open'] and curr['close'] < curr['open'] and
                curr_body > prev_body and curr['open'] >= prev_c['close'] and curr['close'] <= prev_c['open'])
        if bull or bear:
            pos_i = candles.index.get_loc(period.index[i])
            entry = curr['close']
            d = 'long' if bull else 'short'
            bars, ex = sim_trail(candles, pos_i, entry, d, 0.75, atr, 24, 0.5, 0.3)
            pnl = (ex - entry) if d == 'long' else (entry - ex)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'H_tok_engulf', 'dir': d,
                'sl_atr': 0.75, 'pnl_oz': pnl - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            traded = True

# I: London H/L -> NY UP (PF 1.53)
print("Strat I (London HL -> NY UP)...")
for day in trading_days:
    lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    lon_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    lon_mask = (candles['ts_dt'] >= lon_s) & (candles['ts_dt'] < lon_e)
    lon = candles[lon_mask]
    if len(lon) < 10: continue
    prev_d_atr = prev_day(day)
    atr = daily_atr.get(prev_d_atr, global_atr) if prev_d_atr else global_atr
    if atr == 0: continue
    lon_high = lon['high'].max()
    ny_s = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    ny_e = pd.Timestamp(day.year, day.month, day.day, 21, 30, tz='UTC')
    ny_mask = (candles['ts_dt'] >= ny_s) & (candles['ts_dt'] < ny_e)
    ny = candles[ny_mask]
    if len(ny) < 6: continue
    for i in range(len(ny)):
        r = ny.iloc[i]
        if r['close'] > lon_high:
            pos_i = candles.index.get_loc(ny.index[i])
            entry = r['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'I_lonHL_ny_UP', 'dir': 'long',
                'sl_atr': 0.75, 'pnl_oz': (ex - entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            break

print("\nTotal candidats: {}".format(len(candidates)))

# Conflits
cdf = pd.DataFrame(candidates).sort_values('ei').reset_index(drop=True)
act_list = []; acc = []
for _, t in cdf.iterrows():
    act_list = [(ei, d) for ei, d in act_list if ei >= t['ei']]
    if not any(d != t['dir'] for _, d in act_list):
        acc.append(t.to_dict())
        act_list.append((t['xi'], t['dir']))

df = pd.DataFrame(acc).sort_values('ei').reset_index(drop=True)
print("Acceptes: {} (conflits: {})".format(len(df), len(cdf) - len(df)))

for s in sorted(df['strat'].unique()):
    print("  {}: {}".format(s, (df['strat'] == s).sum()))

# Simulation multi-risque
print("\n" + "=" * 80)
print("RESULTATS")
print("=" * 80)

for risk in [0.002, 0.003, 0.004]:
    capital = 10000.0; recs = []
    for _, t in df.iterrows():
        pos_oz = (capital * risk) / (t['sl_atr'] * t['atr'])
        pnl = t['pnl_oz'] * pos_oz
        capital += pnl
        recs.append({'capital': capital, 'pnl': pnl, 'date': t['date'],
                     'strat': t['strat'],
                     'month': str(t['date'].year) + "-" + str(t['date'].month).zfill(2)})
    eq = pd.DataFrame(recs)
    pk = eq['capital'].cummax()
    mdd = ((eq['capital'] - pk) / pk).min() * 100
    ret = (capital - 10000) / 100
    wins = eq[eq['pnl'] > 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(eq[eq['pnl'] < 0]['pnl'].sum()) + 0.01
    mp = eq.groupby('month')['pnl'].sum()
    mid = len(eq) // 2
    p1 = eq.iloc[:mid]['pnl'].sum(); p2 = eq.iloc[mid:]['pnl'].sum()
    ok = "OK" if p1 > 0 and p2 > 0 else "!!"
    print("  Risk {:4.1f}%: Rend={:+6.1f}% DD={:+5.1f}% Cal={:5.1f} PF={:.2f} WR={:.0f}% n={} Mois+={}/{} [{:+.0f}|{:+.0f}] {}".format(
        risk*100, ret, mdd, ret/abs(mdd) if mdd < 0 else 0, gp/gl,
        len(wins)/len(eq)*100, len(eq), (mp>0).sum(), len(mp), p1, p2, ok))

# Detail 0.3%
print("\n" + "=" * 80)
print("DETAIL 0.3%")
print("=" * 80)

capital = 10000.0; recs = []
for _, t in df.iterrows():
    pos_oz = (capital * 0.003) / (t['sl_atr'] * t['atr'])
    pnl = t['pnl_oz'] * pos_oz
    capital += pnl
    recs.append({'capital': capital, 'pnl': pnl, 'date': t['date'],
                 'strat': t['strat'],
                 'month': str(t['date'].year) + "-" + str(t['date'].month).zfill(2)})

eq = pd.DataFrame(recs)
pk = eq['capital'].cummax()
mdd = ((eq['capital'] - pk) / pk).min() * 100
wins = eq[eq['pnl'] > 0]
gp = wins['pnl'].sum(); gl = abs(eq[eq['pnl'] < 0]['pnl'].sum()) + 0.01
ret = (capital - 10000) / 100
mid = len(eq)//2
p1 = eq.iloc[:mid]['pnl'].sum(); p2 = eq.iloc[mid:]['pnl'].sum()
ok = "OK" if p1 > 0 and p2 > 0 else "!!"
t1 = eq.iloc[:len(eq)//3]['pnl'].sum()
t2 = eq.iloc[len(eq)//3:2*len(eq)//3]['pnl'].sum()
t3 = eq.iloc[2*len(eq)//3:]['pnl'].sum()

print("\n  Capital: $10,000 -> ${:,.2f}".format(capital))
print("  Rendement: {:+.1f}%".format(ret))
print("  Trades: {} (~{:.1f}/semaine)".format(len(eq), len(eq)/52))
print("  WR: {:.1f}%  PF: {:.2f}".format(len(wins)/len(eq)*100, gp/gl))
print("  Max DD: {:.2f}%  Calmar: {:.1f}".format(mdd, ret/abs(mdd) if mdd < 0 else 0))
print("  Split: [${:+,.0f} | ${:+,.0f}] {}".format(p1, p2, ok))
print("  Tiers: [${:+,.0f} | ${:+,.0f} | ${:+,.0f}] ({}/3)".format(t1, t2, t3,
    sum(1 for x in [t1,t2,t3] if x > 0)))

print("\n  Contribution:")
for strat in sorted(eq['strat'].unique()):
    s = eq[eq['strat'] == strat]
    pnl_s = s['pnl'].sum()
    pct = pnl_s / eq['pnl'].sum() * 100 if eq['pnl'].sum() != 0 else 0
    wr = (s['pnl'] > 0).mean() * 100
    gp_s = s[s['pnl'] > 0]['pnl'].sum(); gl_s = abs(s[s['pnl'] < 0]['pnl'].sum()) + 0.01
    print("    {:22s}: n={:4d} ${:+,.2f} ({:4.0f}%) WR={:.0f}% PF={:.2f}".format(
        strat, len(s), pnl_s, pct, wr, gp_s/gl_s))

print("\n  {:>8s} {:>4s} {:>5s} {:>10s} {:>12s}".format("Mois", "n", "WR", "PnL", "Capital"))
print("  " + "-" * 47)
for month in eq['month'].unique():
    m = eq[eq['month'] == month]
    pnl_m = m['pnl'].sum()
    wr_m = (m['pnl'] > 0).mean() * 100
    cap = m['capital'].iloc[-1]
    bar = "+" * min(int(pnl_m / 20), 25) if pnl_m > 0 else "-" * min(int(-pnl_m / 20), 25)
    print("  {:>8s} {:4d} {:4.0f}% {:>+10.2f} {:>12,.2f} {}".format(
        month, len(m), wr_m, pnl_m, cap, bar))

mp = eq.groupby('month')['pnl'].sum()
print("\n  Mois positifs: {}/{} ({:.0f}%)".format((mp>0).sum(), len(mp), (mp>0).mean()*100))
print("  Meilleur mois: ${:+,.2f}".format(mp.max()))
print("  Pire mois: ${:+,.2f}".format(mp.min()))

mx_c = 0; c = 0
for _, r in eq.iterrows():
    if r['pnl'] < 0: c += 1; mx_c = max(mx_c, c)
    else: c = 0
print("  Max pertes consec: {}".format(mx_c))

conn.close()
print("\n" + "=" * 80)
