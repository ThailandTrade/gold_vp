"""
Simulation custom — utilise les trades de portfolio_final_clean.py
Parametres: capital et risque en arguments.
Usage: python simu_custom.py [capital] [risk_pct]
Exemple: python simu_custom.py 1000 2.0
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

# ── Params ──
CAPITAL = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0
RISK_PCT = float(sys.argv[2]) / 100 if len(sys.argv) > 2 else 0.02
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

# Spread
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))

# VA
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

# Collecte trades (identique a portfolio_final_clean.py)
candidates = []

# A
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
    if pd_ != prev_va_ref:
        prev_d = None; prev_va_ref = pd_
    rm = rolling_med(day)
    if rm is None:
        prev_d = classify(price, dv['vah'], dv['val']); continue
    pos = classify(price, dv['vah'], dv['val'])
    if pos == 'below' and prev_d == 'inside' and (dv['width']/atr) <= rm and idx > cd:
        bear = (candles.iloc[idx-3:idx]['close'] < candles.iloc[idx-3:idx]['open']).sum()
        if bear >= 2:
            bars, ex = sim_std(candles, idx, price, 'short', price-2.0*atr, price+1.25*atr, 48)
            mk = str(day.year) + "-" + str(day.month).zfill(2)
            sp = 2 * monthly_spread.get(mk, avg_sp)
            candidates.append({'date': day, 'strat': 'A', 'dir': 'short',
                'sl_atr': 1.25, 'pnl_oz': (price-ex) - sp, 'atr': atr,
                'ei': idx, 'xi': idx+bars, 'month': mk})
            cd = idx + max(bars, 6)
    prev_d = pos

for sn, sh, eh, sm, em, ib_b, d, sl, act, trail in [
    ('B', 0, 6, 0, 0, 12, 'long', 0.75, 0.5, 0.3),
    ('C', 0, 6, 0, 0, 6, 'short', 0.75, 0.5, 0.3),
    ('D', 5, 6, 0, 0, 3, 'long', 1.0, 1.0, 0.5),
    ('E', 14, 21, 30, 30, 12, 'long', 1.0, 0.75, 0.5),
]:
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
                mk = str(day.year) + "-" + str(day.month).zfill(2)
                sp = 2 * monthly_spread.get(mk, avg_sp)
                candidates.append({'date': day, 'strat': sn, 'dir': d,
                    'sl_atr': sl, 'pnl_oz': pnl_oz - sp, 'atr': atr,
                    'ei': pos_i, 'xi': pos_i+bars, 'month': mk})
                break

# Conflits
cdf = pd.DataFrame(candidates).sort_values('ei').reset_index(drop=True)
act_list = []; acc = []
for _, t in cdf.iterrows():
    act_list = [(ei, d) for ei, d in act_list if ei >= t['ei']]
    if not any(d != t['dir'] for _, d in act_list):
        acc.append(t.to_dict())
        act_list.append((t['xi'], t['dir']))
df = pd.DataFrame(acc).sort_values('ei').reset_index(drop=True)

# Simulation
capital = CAPITAL
recs = []
for _, t in df.iterrows():
    pos_oz = (capital * RISK_PCT) / (t['sl_atr'] * t['atr'])
    pnl = t['pnl_oz'] * pos_oz
    capital += pnl
    recs.append({'capital': capital, 'pnl': pnl, 'date': t['date'],
                 'strat': t['strat'], 'month': t['month']})

eq = pd.DataFrame(recs)
pk = eq['capital'].cummax()
dd = eq['capital'] - pk
dd_pct = (dd / pk) * 100
max_dd = dd_pct.min()
max_dd_date = eq.loc[dd_pct.idxmin(), 'date']
wins = eq[eq['pnl'] > 0]
losses = eq[eq['pnl'] < 0]
gp = wins['pnl'].sum() if len(wins) > 0 else 0
gl = abs(losses['pnl'].sum()) + 0.01
ret = (capital - CAPITAL) / CAPITAL * 100

print("=" * 70)
print("SIMULATION — Capital ${:,.0f} | Risque {:.1f}% par trade".format(CAPITAL, RISK_PCT*100))
print("Code identique a portfolio_final_clean.py (DST corrige, ATR J-1, rolling median)")
print("=" * 70)
print()
print("  Capital initial  : ${:,.2f}".format(CAPITAL))
print("  Capital final    : ${:,.2f}".format(capital))
print("  Rendement        : {:+.1f}%".format(ret))
print("  Trades           : {}".format(len(eq)))
print("  Win rate         : {:.1f}%".format(len(wins)/len(eq)*100))
print("  Profit Factor    : {:.2f}".format(gp/gl))
print("  Max Drawdown     : {:.2f}% (${:,.2f}) le {}".format(max_dd, dd.min(), max_dd_date))
print("  Calmar           : {:.1f}".format(ret/abs(max_dd) if max_dd < 0 else 0))

print()
print("  {:>8s} {:>4s} {:>5s} {:>10s} {:>10s} {:>12s}".format(
    "Mois", "n", "WR", "PnL", "DD max", "Capital"))
print("  " + "-" * 55)
for month in eq['month'].unique():
    m = eq[eq['month'] == month]
    pnl_m = m['pnl'].sum()
    wr_m = (m['pnl'] > 0).mean() * 100
    cap = m['capital'].iloc[-1]
    m_pk = m['capital'].cummax()
    m_dd = ((m['capital'] - m_pk) / m_pk).min() * 100
    bar = "+" * min(int(pnl_m / max(capital/200, 1)), 25) if pnl_m > 0 else "-" * min(int(-pnl_m / max(capital/200, 1)), 25)
    print("  {:>8s} {:4d} {:4.0f}% {:>+10.2f} {:>9.1f}% {:>12,.2f} {}".format(
        month, len(m), wr_m, pnl_m, m_dd, cap, bar))

mp = eq.groupby('month')['pnl'].sum()
print()
print("  Mois positifs    : {}/{} ({:.0f}%)".format((mp>0).sum(), len(mp), (mp>0).mean()*100))
print("  Meilleur mois    : ${:+,.2f}".format(mp.max()))
print("  Pire mois        : ${:+,.2f}".format(mp.min()))

mx_c = 0; c = 0
for _, r in eq.iterrows():
    if r['pnl'] < 0: c += 1; mx_c = max(mx_c, c)
    else: c = 0
print("  Max pertes consec: {}".format(mx_c))

print()
print("  {:>10s} {:>5s} {:>10s} {:>6s}".format("Strat", "n", "PnL", "Part"))
for strat in sorted(eq['strat'].unique()):
    s = eq[eq['strat'] == strat]
    pnl_s = s['pnl'].sum()
    pct = pnl_s / eq['pnl'].sum() * 100 if eq['pnl'].sum() != 0 else 0
    print("  {:>10s} {:5d} {:>+10.2f} {:5.0f}%".format(strat, len(s), pnl_s, pct))

conn.close()
print()
print("=" * 70)
