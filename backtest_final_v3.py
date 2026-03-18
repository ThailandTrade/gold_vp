"""
Portfolio FINAL v3 — Uniquement les strats PF >= 1.3
Strats retenues:
  A_VA_short      PF=1.21 -> ELIMINE
  B_tok_0h1h_UP   PF=1.34 -> GARDE
  C_tok_0h30m_DN  PF=1.19 -> ELIMINE
  D_tok_5h15m_UP  PF=1.52 -> GARDE
  E_ny_1h_UP      PF=1.14 -> ELIMINE
  F_tok_3bull     PF=1.43 -> GARDE
  G_lon_5bull     PF=1.31 -> GARDE
  H_tok_engulf    PF=1.34 -> GARDE
  I_lonHL_ny_UP   PF=1.46 -> GARDE
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

def get_spread(day):
    mk = str(day.year) + "-" + str(day.month).zfill(2)
    return 2 * monthly_spread.get(mk, avg_sp)

print("=" * 80)
print("PORTFOLIO FINAL v3 — PF >= 1.3 uniquement")
print("=" * 80)

candidates = []

# ── B: IB Tokyo 0h-1h UP (PF 1.34) ──
print("B_tok_0h1h_UP...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 18: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ib_high = period.iloc[:12]['high'].max()
    for i in range(12, len(period)):
        r = period.iloc[i]
        if r['close'] > ib_high:
            pos_i = candles.index.get_loc(period.index[i])
            entry = r['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'B_tok_0h1h_UP', 'dir': 'long',
                'sl_atr': 0.75, 'pnl_oz': (ex-entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            break

# ── D: IB Tokyo 5h-5h15 UP (PF 1.52) ──
print("D_tok_5h15m_UP...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 5, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 6: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ib_high = period.iloc[:3]['high'].max()
    for i in range(3, len(period)):
        r = period.iloc[i]
        if r['close'] > ib_high:
            pos_i = candles.index.get_loc(period.index[i])
            entry = r['close']
            bars, ex = sim_trail(candles, pos_i, entry, 'long', 1.0, atr, 24, 1.0, 0.5)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'D_tok_5h15m_UP', 'dir': 'long',
                'sl_atr': 1.0, 'pnl_oz': (ex-entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            break

# ── F: Tokyo 3 consec bullish (PF 1.43) ──
print("F_tok_3bull...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 9: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
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
                'sl_atr': 0.75, 'pnl_oz': (ex-entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            traded = True

# ── G: London 5 consec bullish (PF 1.31) ──
print("G_lon_5bull...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 11: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
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
                'sl_atr': 0.75, 'pnl_oz': (ex-entry) - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            traded = True

# ── H: Tokyo engulfing (PF 1.34) ──
print("H_tok_engulf...")
for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
    period = candles[mask]
    if len(period) < 8: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    traded = False
    for i in range(1, len(period)):
        if traded: break
        prev_c = period.iloc[i-1]; curr = period.iloc[i]
        prev_body = abs(prev_c['close'] - prev_c['open'])
        curr_body = abs(curr['close'] - curr['open'])
        bull = (prev_c['close'] < prev_c['open'] and curr['close'] > curr['open'] and
                curr_body > prev_body and curr['open'] <= prev_c['close'] and
                curr['close'] >= prev_c['open'])
        bear = (prev_c['close'] > prev_c['open'] and curr['close'] < curr['open'] and
                curr_body > prev_body and curr['open'] >= prev_c['close'] and
                curr['close'] <= prev_c['open'])
        if bull or bear:
            pos_i = candles.index.get_loc(period.index[i])
            entry = curr['close']
            d = 'long' if bull else 'short'
            bars, ex = sim_trail(candles, pos_i, entry, d, 0.75, atr, 24, 0.5, 0.3)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            sp = get_spread(day)
            candidates.append({'date': day, 'strat': 'H_tok_engulf', 'dir': d,
                'sl_atr': 0.75, 'pnl_oz': pnl - sp, 'atr': atr,
                'ei': pos_i, 'xi': pos_i+bars})
            traded = True

# ── I: London H/L -> NY UP (PF 1.46) ──
print("I_lonHL_ny_UP...")
for day in trading_days:
    lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
    lon_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
    lon_mask = (candles['ts_dt'] >= lon_s) & (candles['ts_dt'] < lon_e)
    lon = candles[lon_mask]
    if len(lon) < 10: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
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
                'sl_atr': 0.75, 'pnl_oz': (ex-entry) - sp, 'atr': atr,
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

# Simulation
print("\n" + "=" * 80)
print("RESULTATS")
print("=" * 80)

for risk in [0.002, 0.0025, 0.003, 0.004]:
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
    marker = " <-- PROP" if -5.5 < mdd < -3.5 else ""
    print("  Risk {:5.2f}%: Rend={:+6.1f}% DD={:+5.1f}% Cal={:5.1f} PF={:.2f} WR={:.0f}% n={} Mois+={}/{} [{:+.0f}|{:+.0f}] {}{}".format(
        risk*100, ret, mdd, ret/abs(mdd) if mdd < 0 else 0, gp/gl,
        len(wins)/len(eq)*100, len(eq), (mp>0).sum(), len(mp), p1, p2, ok, marker))

# Detail
print("\n" + "=" * 80)
print("DETAIL 0.25%")
print("=" * 80)

capital = 10000.0; recs = []
for _, t in df.iterrows():
    pos_oz = (capital * 0.0025) / (t['sl_atr'] * t['atr'])
    pnl = t['pnl_oz'] * pos_oz
    capital += pnl
    recs.append({'capital': capital, 'pnl': pnl, 'date': t['date'],
                 'strat': t['strat'],
                 'month': str(t['date'].year) + "-" + str(t['date'].month).zfill(2)})

eq = pd.DataFrame(recs)
pk = eq['capital'].cummax()
mdd = ((eq['capital'] - pk) / pk).min() * 100
wins = eq[eq['pnl'] > 0]; losses = eq[eq['pnl'] < 0]
gp = wins['pnl'].sum(); gl = abs(losses['pnl'].sum()) + 0.01
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
    bar = "+" * min(int(pnl_m / 15), 25) if pnl_m > 0 else "-" * min(int(-pnl_m / 15), 25)
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
