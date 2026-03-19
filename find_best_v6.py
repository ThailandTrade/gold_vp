"""
Optimisation v6 — 18 strategies sur donnees OHLC brut MT5.
Combos de 6 a 18 strats. $1000, risk 1%.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import time, numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10
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

daily_data = {}
for day in trading_days:
    dc = candles[candles['date'] == day]
    if len(dc) >= 10: daily_data[day] = {'dir': 1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1}

print("Collecte des 18 strats...", flush=True)
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    def add(sn, d, e, pi):
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn, []).append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})

    if len(tok)>=18:
        lvl=tok.iloc[:12]['high'].max()
        for i in range(12,len(tok)):
            if tok.iloc[i]['close']>lvl: add('A','long',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
    if len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: add('C','short' if m>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    tc=candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc)>=5:
        l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(l2)>=6:
            gap=(l2.iloc[0]['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    kz=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz)>=20:
        m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
        if abs(m)>=0.5:
            post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
            if len(post)>=6: add('E','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
    if len(tok)>=8:
        for i in range(1,len(tok)):
            b1b=tok.iloc[i-1]['close']-tok.iloc[i-1]['open'];b2b=tok.iloc[i]['close']-tok.iloc[i]['open']
            if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
            if b1b*b2b>=0 or abs(b2b)<=abs(b1b): continue
            add('F','long' if b2b>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
    if len(ny)>=6:
        body=ny.iloc[0]['close']-ny.iloc[0]['open']
        if abs(body)>=0.3*atr and len(ny)>=2: add('G','long' if body>0 else 'short',ny.iloc[1]['open'],candles.index.get_loc(ny.index[1]))
    if len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: add('H','long' if m>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    ny1=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1)>=10:
        m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
            if len(post)>=6: add('I','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
    if len(lon)>=6:
        body=lon.iloc[0]['close']-lon.iloc[0]['open']
        if abs(body)>=0.3*atr and len(lon)>=2: add('J','long' if body>0 else 'short',lon.iloc[1]['open'],candles.index.get_loc(lon.index[1]))
    if len(tok)>=6:
        for i in range(len(tok)):
            body=tok.iloc[i]['close']-tok.iloc[i]['open']
            if abs(body)>=1.0*atr: add('O','long' if body>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
    if len(ny)>=12:
        oh=ny.iloc[:6]['high'].max(); ol=ny.iloc[:6]['low'].min()
        for i in range(6,len(ny)):
            r=ny.iloc[i]
            if r['close']>oh: add('P','long',r['close'],candles.index.get_loc(ny.index[i])); break
            elif r['close']<ol: add('P','short',r['close'],candles.index.get_loc(ny.index[i])); break
    if len(lon)>=6:
        for i in range(1,len(lon)):
            pb=lon.iloc[i-1];cb=lon.iloc[i]; hit=False
            if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                add('Q','long',cb['close'],candles.index.get_loc(lon.index[i])); hit=True
            if not hit and pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                add('Q','short',cb['close'],candles.index.get_loc(lon.index[i])); hit=True
            if hit: break
    if len(tok)>=6:
        for i in range(2,len(tok)):
            c1=tok.iloc[i-2];c2=tok.iloc[i-1];c3=tok.iloc[i]
            b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                add('R','long' if b3>0 else 'short',c3['close'],candles.index.get_loc(tok.index[i])); break
    if len(lon)>=6:
        for i in range(2,len(lon)):
            c1=lon.iloc[i-2];c2=lon.iloc[i-1];c3=lon.iloc[i]
            b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                add('S','short' if b3>0 else 'long',c3['close'],candles.index.get_loc(lon.index[i])); break
    if len(tok)>=12:
        for i in range(6,len(tok)):
            last6=tok.iloc[i-6:i]; n_bull=(last6['close']>last6['open']).sum()
            if n_bull>=5: add('V','long',tok.iloc[i]['open'],candles.index.get_loc(tok.index[i])); break
            elif n_bull<=1: add('V','short',tok.iloc[i]['open'],candles.index.get_loc(tok.index[i])); break
    di=trading_days.index(day) if day in trading_days else -1
    if di>=3:
        dirs=[]
        for k in range(3):
            dk=trading_days[di-3+k]
            if dk in daily_data: dirs.append(daily_data[dk]['dir'])
        if len(dirs)==3 and len(set(dirs))==1:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: add('Z','short' if dirs[0]>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    if len(lon)>=6:
        for i in range(len(lon)):
            r=lon.iloc[i]; rng=r['high']-r['low']
            if rng<0.3*atr or abs(r['close']-r['open'])<0.2*atr: continue
            pir=(r['close']-r['low'])/rng
            if pir>=0.9: add('AA','long',r['close'],candles.index.get_loc(lon.index[i])); break
            if pir<=0.1: add('AA','short',r['close'],candles.index.get_loc(lon.index[i])); break
    if len(tok)>=6:
        for i in range(3,len(tok)):
            prev3_h=tok.iloc[i-3:i]['high'].max(); prev3_l=tok.iloc[i-3:i]['low'].min()
            r=tok.iloc[i]; body=abs(r['close']-r['open'])
            if r['high']>=prev3_h and r['low']<=prev3_l and body>=0.5*atr:
                add('AC','long' if r['close']>r['open'] else 'short',r['close'],candles.index.get_loc(tok.index[i])); break

conn.close()

LEGEND = {
    'A':'IB_tok_1h_UP','C':'FADE_tok_lon','D':'GAP_tok_lon','E':'KZ_lon_fade',
    'F':'2BAR_tok_rev','G':'NY1st_candle','H':'TOKEND_3b','I':'FADENY_1h',
    'J':'LON1st_candle','O':'BigCandle_tok','P':'ORB_NY30','Q':'Engulfing_lon',
    'R':'3soldiers_tok','S':'3soldiers_rev_lon','V':'CandleRatio_tok',
    'Z':'3days_rev','AA':'CloseExtreme_lon','AC':'Absorption_tok'
}

# Stats individuelles
print("\n" + "="*80, flush=True)
print("STATS INDIVIDUELLES (18 strats — OHLC brut)")
print("="*80)
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 10: print(f"  {sn:3s} ({LEGEND.get(sn,''):20s}): n={len(t)} --"); continue
    df = pd.DataFrame(t)
    gp = df[df['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(df[df['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (df['pnl_oz']>0).mean()*100
    ns = (df['dir']=='short').sum(); nl = (df['dir']=='long').sum()
    mid = len(df)//2; f1 = df.iloc[:mid]['pnl_oz'].mean(); f2 = df.iloc[mid:]['pnl_oz'].mean()
    ok = "OK" if f1>0 and f2>0 else "!!"
    print(f"  {sn:3s} ({LEGEND.get(sn,''):20s}): n={len(df):4d} ({nl:3d}L {ns:3d}S) WR={wr:.0f}% PF={gp/gl:.2f} [{f1:+.3f}|{f2:+.3f}] {ok}")

# Pre-conversion numpy
strat_arrays = {}
for sn in S:
    if len(S[sn]) == 0: continue
    rows = []
    for t in S[sn]:
        di = 1 if t['dir'] == 'long' else -1
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t['xi'], di, t['pnl_oz'], t['sl_atr'], t['atr'], 0, mo, sn))
    strat_arrays[sn] = rows

def eval_combo_fast(combo, capital=1000.0, risk=0.01):
    combined = []
    for sn in combo:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    if len(combined) < 50: return None
    combined.sort(key=lambda x: (x[0], x[8]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, do, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, do, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    if n < 50: return None
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; pnls = []
    for ei, xi, di, pnl_oz, sl_atr, atr, do, mo, _sn in accepted:
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
    mid = n // 2
    p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
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

all_n = sorted(strat_arrays.keys())
n_strats = len(all_n)
total_combos = sum(1 for sz in range(6, n_strats+1) for _ in combinations(all_n, sz))
print(f"\n{'='*80}", flush=True)
print(f"COMBINAISONS ({total_combos} combos, {n_strats} strats, taille 6-{n_strats})", flush=True)
print(f"{'='*80}", flush=True)

results = []
done = 0; t0 = time.time()
for size in range(6, n_strats+1):
    for combo in combinations(all_n, size):
        done += 1
        if done % 2000 == 0:
            elapsed = time.time() - t0
            speed = done / elapsed if elapsed > 0 else 0
            eta = (total_combos - done) / speed if speed > 0 else 0
            pct = done * 100 // total_combos
            print(f"\r  [{('#'*(pct//2)).ljust(50,'-')}] {pct:3d}% ({done}/{total_combos}) ETA {eta:.0f}s   ", end='', flush=True)
        r = eval_combo_fast(combo)
        if r is not None: results.append(r)

print(f"\n\n  {len(results)} combos valides", flush=True)

rdf = pd.DataFrame(results)
ok = rdf[(rdf['split']) & (rdf['tiers']==3)]

def show(title, sub, col, n=20):
    print(f"\n  {title}")
    print(f"  {'Combo':55s} {'n':>5s} {'t/j':>4s} {'Capital':>12s} {'Rend%':>9s} {'DD%':>7s} {'Cal':>8s} {'PF':>5s} {'WR%':>4s} {'M+':>5s}")
    for _, r in sub.sort_values(col, ascending=False).head(n).iterrows():
        d = "L+S" if r['both'] else "L"
        print(f"  {r['combo'][:55]:55s} {r['n']:5.0f} {r['tpd']:4.1f} {r['capital']:12,.0f}$ {r['ret']:+8.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['pf']:.2f} {r['wr']:3.0f}% {r['pm']:2.0f}/{r['tm']:.0f} {d}")

print("\n  LEGENDE:", flush=True)
for k in sorted(LEGEND.keys()):
    print(f"    {k} = {LEGEND[k]}")

show("TOP 20 CALMAR (split OK, tiers 3/3)", ok, 'cal', 20)
show("TOP 20 PF (split OK, tiers 3/3, n>=500)", ok[ok['n']>=500], 'pf', 20)
show("TOP 10 RENDEMENT (split OK, tiers 3/3)", ok, 'ret', 10)

print(f"\n{'='*80}")
