"""Test: portfolio AA+D+E+F+H+O + strats NY"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

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
n_td = len(set(candles['date'].unique()))

SL, ACT, TRAIL, MX = 1.0, 0.5, 0.75, 12
def sim_exit(cdf, pos, entry, d, atr):
    best = entry; stop = entry + SL*atr if d == 'short' else entry - SL*atr; ta = False
    for j in range(1, MX+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['close'] > best: best = b['close']
            if not ta and (best-entry) >= ACT*atr: ta = True
            if ta: stop = max(stop, best - TRAIL*atr)
            if b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['close'] < best: best = b['close']
            if not ta and (entry-best) >= ACT*atr: ta = True
            if ta: stop = min(stop, best + TRAIL*atr)
            if b['close'] > stop: return j, b['close']
    if pos+MX < len(cdf): return MX, cdf.iloc[pos+MX]['close']
    return MX, entry

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]; ny = tv[tv['ts_dt']>=ns]
    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})
    # Base strats
    if 8.0<=hour<14.5 and 'AA' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('AA','long',row['close']); trig['AA']=True
            elif pir<=0.1: add('AA','short',row['close']); trig['AA']=True
    if 8.0<=hour<8.1 and 'D' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',row['open']); trig['D']=True
    if 10.0<=hour<10.1 and 'E' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: add('E','short' if m>0 else 'long',row['open']); trig['E']=True
    if 0.0<=hour<6.0 and 'F' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('F','long' if b2b>0 else 'short',b2['close']); trig['F']=True
    if 8.0<=hour<8.1 and 'H' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('H','long' if m>0 else 'short',row['open']); trig['H']=True
    if 0.0<=hour<6.0 and 'O' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('O','long' if body>0 else 'short',row['close']); trig['O']=True
    # NY strats
    if 14.5<=hour<14.6 and 'NY6' not in trig and len(lon)>=5:
        gap=(row['open']-lon.iloc[-1]['close'])/atr
        if abs(gap)>=0.5: add('NY6','long' if gap>0 else 'short',row['open']); trig['NY6']=True
    if 15.0<=hour<21.0 and 'NY11' not in trig:
        if 'NY11_h' not in trig:
            orb=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['NY11_h']=float(orb['high'].max()); trig['NY11_l']=float(orb['low'].min())
        if 'NY11_h' in trig:
            if row['close']>trig['NY11_h']: add('NY11','long',row['close']); trig['NY11']=True
            elif row['close']<trig['NY11_l']: add('NY11','short',row['close']); trig['NY11']=True
    if 14.5<=hour<14.6 and 'NY16' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('NY16','long' if m>0 else 'short',row['open']); trig['NY16']=True
    if 14.5<=hour<14.6 and 'NY17' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=0.5: add('NY17','long' if m>0 else 'short',row['open']); trig['NY17']=True
    if 14.5<=hour<21.0 and 'NY23' not in trig and len(ny)>=3:
        c1=ny.iloc[-3];c2=ny.iloc[-2];c3=ny.iloc[-1]
        b1n=c1['close']-c1['open'];b2n=c2['close']-c2['open'];b3n=c3['close']-c3['open']
        if b1n*b2n>0 and b2n*b3n>0 and min(abs(b1n),abs(b2n),abs(b3n))>0.1*atr and abs(b1n+b2n+b3n)>=0.5*atr:
            add('NY23','long' if b3n>0 else 'short',c3['close']); trig['NY23']=True
    if 14.5<=hour<21.0 and 'NY24' not in trig and len(ny)>=4:
        prev3_h_ny=ny.iloc[-4:-1]['high'].max();prev3_l_ny=ny.iloc[-4:-1]['low'].min()
        body_ny=abs(row['close']-row['open'])
        if row['high']>=prev3_h_ny and row['low']<=prev3_l_ny and body_ny>=0.5*atr:
            add('NY24','long' if row['close']>row['open'] else 'short',row['close']); trig['NY24']=True

print("Done.", flush=True)

# Build arrays
strat_arrays = {}
for sn in S:
    rows = []
    for t in S[sn]:
        di = 1 if t['dir'] == 'long' else -1
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t['xi'], di, t['pnl_oz'], t['sl_atr'], t['atr'], mo, sn))
    strat_arrays[sn] = rows

def eval_combo(combo, capital=1000.0, risk=0.01):
    combined = []
    for sn in combo:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    if len(combined) < 50: return None
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    if n < 50: return None
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; pnls = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in accepted:
        pnl = pnl_oz * (cap * risk) / (sl_atr * atr)
        cap += pnl; pnls.append(pnl)
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        months[mo] = months.get(mo, 0.0) + pnl
        if di == 1: has_l = True
        else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    pm = sum(1 for v in months.values() if v > 0)
    return {
        'combo': '+'.join(combo), 'ns': len(combo), 'n': n, 'tpd': n / n_td,
        'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
        'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
        'split': p1 > 0 and p2 > 0,
        'tiers': sum(1 for x in [t1, t2, t3] if x > 0),
        'both': has_s and has_l, 'pm': pm, 'tm': len(months),
    }

base = ['AA','D','E','F','H','O']
ny_strats = ['NY6','NY11','NY16','NY17','NY23','NY24']

print()
print("="*130)
print("  PORTFOLIO DE BASE + STRATS NY")
print("="*130)

r = eval_combo(tuple(base))
print(f"\n  BASE: AA+D+E+F+H+O")
print(f"    n={r['n']:.0f} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Calmar={r['cal']:.1f} Rend={r['ret']:+.0f}% M+={r['pm']:.0f}/{r['tm']:.0f}")

print(f"\n  {'Ajout':20s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>9s} {'M+':>5s} {'Split':>5s} {'T':>3s}")
print(f"  {'-'*100}")

# +1 NY
for ny in ny_strats:
    combo = tuple(sorted(base + [ny]))
    r = eval_combo(combo)
    if r:
        sp = "OK" if r['split'] else "!!"
        print(f"  +{ny:19s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+8.0f}% {r['pm']:.0f}/{r['tm']:.0f} {sp:>5s} {r['tiers']}/3")

print(f"\n  +2 NY (top 10 Calmar, split OK):")
print(f"  {'Ajout':20s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>9s} {'M+':>5s} {'T':>3s}")
print(f"  {'-'*100}")
res2 = []
for ny_combo in combinations(ny_strats, 2):
    combo = tuple(sorted(base + list(ny_combo)))
    r = eval_combo(combo)
    if r and r['split'] and r['both']: res2.append((ny_combo, r))
res2.sort(key=lambda x: x[1]['cal'], reverse=True)
for ny_combo, r in res2[:10]:
    print(f"  +{'+'.join(ny_combo):19s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+8.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

print(f"\n  +3 NY (top 5 Calmar, split OK):")
print(f"  {'Ajout':20s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>9s} {'M+':>5s} {'T':>3s}")
print(f"  {'-'*100}")
res3 = []
for ny_combo in combinations(ny_strats, 3):
    combo = tuple(sorted(base + list(ny_combo)))
    r = eval_combo(combo)
    if r and r['split'] and r['both']: res3.append((ny_combo, r))
res3.sort(key=lambda x: x[1]['cal'], reverse=True)
for ny_combo, r in res3[:5]:
    print(f"  +{'+'.join(ny_combo):19s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+8.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

print()
