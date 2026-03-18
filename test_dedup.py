"""
Comparaison : portfolio avec doublons vs deduplique (1 trade par ei+dir)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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
print("Done.", flush=True)

strats = ['A','C','D','E','F','G','H','I','J','O','P','Q','R','S','V','Z','AA','AC']

def run_portfolio(combined, label, capital=1000.0, risk=0.01, dedup=False):
    combined.sort(key=lambda x: (x['ei'], x['strat']))
    # Conflict resolution
    al = []; acc = []
    seen_ei_dir = set()
    for t in combined:
        al = [(xi, d) for xi, d in al if xi >= t['ei']]
        if any(d != t['dir'] for _, d in al): continue
        if dedup:
            key = (t['ei'], t['dir'])
            if key in seen_ei_dir: continue
            seen_ei_dir.add(key)
        acc.append(t); al.append((t['xi'], t['dir']))
    # Equity
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    for t in acc:
        pnl = t['pnl_oz'] * (cap * risk) / (t['sl_atr'] * t['atr'])
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        if mo not in months: months[mo] = {'pnl':0,'n':0,'wins':0}
        months[mo]['pnl'] += pnl; months[mo]['n'] += 1
        if pnl > 0: months[mo]['wins'] += 1
    n = len(acc); mdd = max_dd*100; ret = (cap-capital)/capital*100
    pf = gp/(gl+0.01); wr = wins/n*100 if n else 0
    pm = sum(1 for v in months.values() if v['pnl'] > 0)
    return acc, months, {'label':label,'n':n,'tpd':n/n_td,'capital':cap,'ret':ret,'mdd':mdd,
                         'cal':ret/abs(mdd) if mdd<0 else 0,'pf':pf,'wr':wr,'pm':pm,'tm':len(months)}

combined_all = []
for sn in strats:
    for t in S.get(sn, []): combined_all.append({**t, 'strat': sn})

_, months_dup, r_dup = run_portfolio(list(combined_all), "AVEC doublons (18 strats)", dedup=False)
_, months_dedup, r_dedup = run_portfolio(list(combined_all), "SANS doublons (deduplique)", dedup=True)

print(f"\n{'='*100}")
print(f"  COMPARAISON — $1000, Risk 1%")
print(f"{'='*100}")
print(f"  {'Label':40s} {'n':>5s} {'t/j':>5s} {'Capital':>14s} {'Rend%':>10s} {'DD%':>7s} {'Cal':>10s} {'PF':>5s} {'WR%':>4s} {'M+':>5s}")
for r in [r_dup, r_dedup]:
    print(f"  {r['label']:40s} {r['n']:5.0f} {r['tpd']:5.1f} {r['capital']:14,.0f}$ {r['ret']:+9.0f}% {r['mdd']:+6.1f}% {r['cal']:10.1f} {r['pf']:.2f} {r['wr']:3.0f}% {r['pm']:2.0f}/{r['tm']:.0f}")

# Detail mois par mois
print(f"\n{'='*100}")
print(f"  DETAIL MOIS PAR MOIS")
print(f"{'='*100}")
print(f"  {'Mois':8s}  {'--- AVEC DOUBLONS ---':^30s}  {'--- DEDUPLIQUE ---':^30s}")
print(f"  {'':8s}  {'n':>5s} {'WR':>5s} {'PF':>6s} {'PnL%':>8s}    {'n':>5s} {'WR':>5s} {'PF':>6s} {'PnL%':>8s}")

all_months = sorted(set(list(months_dup.keys()) + list(months_dedup.keys())))
for mo in all_months:
    md = months_dup.get(mo, {'n':0,'pnl':0,'wins':0})
    mdd_mo = months_dedup.get(mo, {'n':0,'pnl':0,'wins':0})
    wr_d = md['wins']/md['n']*100 if md['n'] else 0
    wr_dd = mdd_mo['wins']/mdd_mo['n']*100 if mdd_mo['n'] else 0
    print(f"  {mo:8s}  {md['n']:5d} {wr_d:4.0f}% {'--':>6s} {'':>8s}    {mdd_mo['n']:5d} {wr_dd:4.0f}% {'--':>6s} {'':>8s}")

# Risque reel
print(f"\n{'='*100}")
print(f"  RISQUE REEL")
print(f"{'='*100}")
_, _, r1 = run_portfolio(list(combined_all), "risk 1% avec doublons", capital=1000, risk=0.01, dedup=False)
_, _, r2 = run_portfolio(list(combined_all), "risk 1% deduplique", capital=1000, risk=0.01, dedup=True)
# Dedup mais risk 2% pour simuler "meme exposure totale"
_, _, r3 = run_portfolio(list(combined_all), "risk 2% deduplique (meme expo)", capital=1000, risk=0.02, dedup=True)
# Avec doublons mais risk 0.5%
_, _, r4 = run_portfolio(list(combined_all), "risk 0.5% avec doublons", capital=1000, risk=0.005, dedup=False)

print(f"  {'Label':45s} {'n':>5s} {'Capital':>14s} {'DD%':>7s} {'Cal':>10s} {'PF':>5s}")
for r in [r1, r2, r3, r4]:
    print(f"  {r['label']:45s} {r['n']:5.0f} {r['capital']:14,.0f}$ {r['mdd']:+6.1f}% {r['cal']:10.1f} {r['pf']:.2f}")

print(f"\n{'='*100}")
