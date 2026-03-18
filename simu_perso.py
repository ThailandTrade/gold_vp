"""
Simulation compte perso — portfolio champion 2BAR+B+D2+FADE+GAP+KZ.
Usage: python simu_perso.py [capital] [risk%]
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import (
    get_conn, compute_vp, load_ticks_for_period, compute_atr, get_trading_days
)
from phase3_analyze import load_candles_5m

CAPITAL = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0
RISK = float(sys.argv[2]) / 100 if len(sys.argv) > 2 else 0.02
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

S = {}

# B
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

# GAP
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
    d = 'long' if gap > 0 else 'short'
    bars, ex = sim_trail(candles, pi, entry, d, 0.75, atr, 24, 0.5, 0.3)
    pnl = (ex-entry) if d == 'long' else (entry-ex)
    t.append({'date': day, 'dir': d, 'sl_atr': 0.75, 'pnl_oz': pnl-get_sp(day), 'atr': atr, 'ei': pi, 'xi': pi+bars})
S['GAP'] = t

# KZ
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

# 2BAR
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

# Combiner + conflits
combined = []
for sn in S:
    for t in S[sn]:
        combined.append({**t, 'strat': sn})
cdf = pd.DataFrame(combined).sort_values('ei').reset_index(drop=True)
al = []; acc = []
for _, t in cdf.iterrows():
    al = [(ei, d) for ei, d in al if ei >= t['ei']]
    if not any(d != t['dir'] for _, d in al):
        acc.append(t.to_dict())
        al.append((t['xi'], t['dir']))
df = pd.DataFrame(acc).sort_values('ei').reset_index(drop=True)

# Simulation
capital = CAPITAL; recs = []
for _, t in df.iterrows():
    pos_oz = (capital * RISK) / (t['sl_atr'] * t['atr'])
    pnl = t['pnl_oz'] * pos_oz
    capital += pnl
    recs.append({'capital': capital, 'pnl': pnl, 'date': t['date'], 'strat': t['strat'],
                 'month': str(t['date'].year)+"-"+str(t['date'].month).zfill(2)})

eq = pd.DataFrame(recs)
pk = eq['capital'].cummax()
dd = eq['capital'] - pk
dd_pct = (dd/pk)*100
wins = eq[eq['pnl']>0]; losses = eq[eq['pnl']<0]
gp = wins['pnl'].sum() if len(wins)>0 else 0
gl = abs(losses['pnl'].sum())+0.01
ret = (capital-CAPITAL)/CAPITAL*100

print("=" * 70)
print("SIMULATION — ${:,.0f} | Risque {:.1f}% | Portfolio 2BAR+B+D2+FADE+GAP+KZ".format(CAPITAL, RISK*100))
print("=" * 70)
print("\n  ${:,.2f} -> ${:,.2f} ({:+.1f}%)".format(CAPITAL, capital, ret))
print("  Trades: {} | WR: {:.1f}% | PF: {:.2f}".format(len(eq), len(wins)/len(eq)*100, gp/gl))
print("  Max DD: {:.2f}% | Calmar: {:.1f}".format(dd_pct.min(), ret/abs(dd_pct.min())))
print("  Max pertes consec: {}".format(max((sum(1 for _ in g) for k,g in
    __import__('itertools').groupby(eq['pnl']<0) if k), default=0)))

print("\n  {:>8s} {:>4s} {:>5s} {:>12s} {:>12s} {:>7s}".format("Mois","n","WR","PnL","Capital","DD"))
print("  "+"-"*55)
for month in eq['month'].unique():
    m = eq[eq['month']==month]
    pnl_m = m['pnl'].sum(); wr_m = (m['pnl']>0).mean()*100; cap = m['capital'].iloc[-1]
    m_dd = ((m['capital']-m['capital'].cummax())/m['capital'].cummax()).min()*100
    bar = "+"*min(int(pnl_m/max(capital/500,1)),25) if pnl_m>0 else "-"*min(int(-pnl_m/max(capital/500,1)),25)
    print("  {:>8s} {:4d} {:4.0f}% {:>+12.2f} {:>12,.2f} {:>6.1f}% {}".format(
        month, len(m), wr_m, pnl_m, cap, m_dd, bar))

mp = eq.groupby('month')['pnl'].sum()
print("\n  Mois+: {}/{} | Best: ${:+,.2f} | Worst: ${:+,.2f}".format(
    (mp>0).sum(), len(mp), mp.max(), mp.min()))
print("\n  Par strat:")
for s in sorted(eq['strat'].unique()):
    sub = eq[eq['strat']==s]
    print("    {:6s}: n={:4d} ${:+,.2f} ({:.0f}%)".format(s, len(sub), sub['pnl'].sum(),
        sub['pnl'].sum()/eq['pnl'].sum()*100))

conn.close()
print("\n" + "=" * 70)
