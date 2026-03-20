"""
Simulation Prop Firm — Capital $50K, Risk 0.1%
Combo: AA+AC+C+D+E+H (6 strats, PF 2.12)
Backtest no look-ahead bougie par bougie.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10; SL = 0.75; ACT = 0.5; TRAIL = 0.3
CAPITAL = 50000.0; RISK = 0.001  # 0.1%
STRATS = ['AA','AC','C','D','E','H']

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
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

# Collecte bougie par bougie
print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; ibs = {}; day_atr = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        prev_d = today; trig = {}; ibs = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    le = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<le)]
    def add(sn, d, e):
        b, ex = sim_trail(candles, ci, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})
    # AA
    if 8.0<=hour<14.5 and 'AA' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('AA','long',row['close']); trig['AA']=True
            elif pir<=0.1: add('AA','short',row['close']); trig['AA']=True
    # AC
    if 0.0<=hour<6.0 and 'AC' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('AC','long' if row['close']>row['open'] else 'short',row['close']); trig['AC']=True
    # C
    if 8.0<=hour<8.1 and 'C' not in trig and len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('C','short' if m>0 else 'long',row['open']); trig['C']=True
    # D
    if 8.0<=hour<8.1 and 'D' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',row['open']); trig['D']=True
    # E
    if 10.0<=hour<10.1 and 'E' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: add('E','short' if m>0 else 'long',row['open']); trig['E']=True
    # H
    if 8.0<=hour<8.1 and 'H' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('H','long' if m>0 else 'short',row['open']); trig['H']=True

print("Done.", flush=True)

# Portfolio avec conflict resolution
combined = []
for sn in STRATS:
    for t in S.get(sn, []): combined.append({**t, 'strat': sn})
combined.sort(key=lambda x: (x['ei'], x['strat']))
al = []; acc = []
for t in combined:
    al = [(xi, d) for xi, d in al if xi >= t['ei']]
    if any(d != t['dir'] for _, d in al): continue
    acc.append(t); al.append((t['xi'], t['dir']))

# Simulation mois par mois
cap = CAPITAL; peak = cap; global_dd = 0; months = {}
for t in acc:
    pnl = t['pnl_oz'] * (cap * RISK) / (t['sl_atr'] * t['atr'])
    cap += pnl
    if cap > peak: peak = cap
    dd = (cap - peak) / peak * 100
    if dd < global_dd: global_dd = dd
    mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
    if mo not in months:
        months[mo] = {'cap_start': cap-pnl, 'cap_end': cap, 'n': 0, 'wins': 0,
                       'gp': 0, 'gl': 0, 'pnls': [], 'dd_worst': 0, 'peak': peak}
    m = months[mo]; m['cap_end'] = cap; m['n'] += 1; m['pnls'].append(pnl)
    if pnl > 0: m['wins'] += 1; m['gp'] += pnl
    else: m['gl'] += abs(pnl)
    if dd < m['dd_worst']: m['dd_worst'] = dd
    if cap > peak: peak = cap
    m['peak'] = peak

print(f"\n{'='*110}")
print(f"  PROP FIRM — Capital ${CAPITAL:,.0f}, Risk {RISK*100:.1f}%, {len(STRATS)} strats ({'+'.join(STRATS)})")
print(f"  {len(acc)} trades, Capital final ${cap:,.2f}, DD global {global_dd:.2f}%")
print(f"{'='*110}")
print(f"  {'Mois':8s} {'Trades':>7s} {'Wins':>5s} {'WR':>5s} {'PF':>6s} {'Capital':>14s} {'PnL $':>12s} {'PnL%':>8s} {'Max DD':>8s} {'Avg trade':>10s}")
print(f"  {'-'*105}")

for mo in sorted(months.keys()):
    m = months[mo]
    wr = m['wins']/m['n']*100 if m['n'] else 0
    pf = m['gp']/(m['gl']+0.01)
    pnl_total = sum(m['pnls'])
    pnl_pct = pnl_total / m['cap_start'] * 100 if m['cap_start'] > 0 else 0
    avg = pnl_total / m['n'] if m['n'] else 0
    print(f"  {mo:8s} {m['n']:7d} {m['wins']:5d} {wr:4.0f}% {pf:6.2f} {m['cap_end']:14,.2f} {pnl_total:+12,.2f} {pnl_pct:+7.1f}% {m['dd_worst']:+7.2f}% {avg:+10,.2f}")

pm = sum(1 for m in months.values() if sum(m['pnls']) > 0)
print(f"  {'-'*105}")
print(f"  Capital: ${CAPITAL:,.0f} → ${cap:,.2f} ({(cap-CAPITAL)/CAPITAL*100:+.1f}%)")
print(f"  Trades: {len(acc)} | WR: {sum(m['wins'] for m in months.values())/len(acc)*100:.0f}%")
print(f"  Max DD: {global_dd:.2f}%")
print(f"  Mois positifs: {pm}/{len(months)}")
print(f"{'='*110}")
