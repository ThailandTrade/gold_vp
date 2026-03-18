"""
Test v10 : 4 nouveaux signaux vs champion 16 strats
AA=CloseExtreme_lon, AB=TwinCandles_tok, AC=Absorption_tok, AD=TwinCandles_lon
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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

# ══════ Reutiliser les strats champion depuis test_v9.py (copie) ══════
print("Building 16 champion strats...", flush=True)

# A
t=[];
for day in trading_days:
    p=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))];
    if len(p)<18: continue
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    lvl=p.iloc[:12]['high'].max()
    for i in range(12,len(p)):
        if p.iloc[i]['close']>lvl:
            pi=candles.index.get_loc(p.index[i]); e=p.iloc[i]['close']
            b,ex=sim_trail(candles,pi,e,'long',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['A']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    tok=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok)<10: continue
    m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
    if abs(m)<1.0: continue
    lon=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon)<6: continue
    pi=candles.index.get_loc(lon.index[0]); e=lon.iloc[0]['open']
    d='short' if m>0 else 'long'
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['C']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    tc=candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc)<5: continue
    lon=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon)<6: continue
    gap=(lon.iloc[0]['open']-tc.iloc[-1]['close'])/atr
    if abs(gap)<0.5: continue
    pi=candles.index.get_loc(lon.index[0]); e=lon.iloc[0]['open']
    d='long' if gap>0 else 'short'
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['D']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    kz=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz)<20: continue
    m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
    if abs(m)<0.5: continue
    post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
    if len(post)<6: continue
    pi=candles.index.get_loc(post.index[0]); e=post.iloc[0]['open']
    d='short' if m>0 else 'long'
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['E']=t

t=[];
for day in trading_days:
    p=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p)<8: continue
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    for i in range(1,len(p)):
        b1b=p.iloc[i-1]['close']-p.iloc[i-1]['open']; b2b=p.iloc[i]['close']-p.iloc[i]['open']
        if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
        if b1b*b2b>=0 or abs(b2b)<=abs(b1b): continue
        pi=candles.index.get_loc(p.index[i]); e=p.iloc[i]['close']
        d='long' if b2b>0 else 'short'
        b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
        pnl=(ex-e) if d=='long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['F']=t

t=[];
for day in trading_days:
    p=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(p)<6: continue
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    body=p.iloc[0]['close']-p.iloc[0]['open']
    if abs(body)<0.3*atr or len(p)<2: continue
    d='long' if body>0 else 'short'
    pi=candles.index.get_loc(p.index[1]); e=p.iloc[1]['open']
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['G']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    tok=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok)<9: continue
    l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
    if abs(m)<1.0: continue
    lon=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon)<6: continue
    pi=candles.index.get_loc(lon.index[0]); e=lon.iloc[0]['open']
    d='long' if m>0 else 'short'
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['H']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    ny1=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1)<10: continue
    m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
    if abs(m)<1.0: continue
    post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
    if len(post)<6: continue
    pi=candles.index.get_loc(post.index[0]); e=post.iloc[0]['open']
    d='short' if m>0 else 'long'
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['I']=t

t=[];
for day in trading_days:
    p=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(p)<6: continue
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    body=p.iloc[0]['close']-p.iloc[0]['open']
    if abs(body)<0.3*atr or len(p)<2: continue
    d='long' if body>0 else 'short'
    pi=candles.index.get_loc(p.index[1]); e=p.iloc[1]['open']
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['J']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(len(sess)):
        body=sess.iloc[i]['close']-sess.iloc[i]['open']
        if abs(body)>=1.0*atr:
            d='long' if body>0 else 'short'
            pi=candles.index.get_loc(sess.index[i]); e=sess.iloc[i]['close']
            b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
            pnl=(ex-e) if d=='long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['O']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    ny=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(ny)<12: continue
    oh=ny.iloc[:6]['high'].max(); ol=ny.iloc[:6]['low'].min()
    for i in range(6,len(ny)):
        r=ny.iloc[i]
        if r['close']>oh:
            pi=candles.index.get_loc(ny.index[i]); e=r['close']
            b,ex=sim_trail(candles,pi,e,'long',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        elif r['close']<ol:
            pi=candles.index.get_loc(ny.index[i]); e=r['close']
            b,ex=sim_trail(candles,pi,e,'short',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['P']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(1,len(sess)):
        pb=sess.iloc[i-1]; cb=sess.iloc[i]; hit=False
        if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            pi=candles.index.get_loc(sess.index[i]); e=cb['close']
            b,ex=sim_trail(candles,pi,e,'long',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); hit=True
        if not hit and pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            pi=candles.index.get_loc(sess.index[i]); e=cb['close']
            b,ex=sim_trail(candles,pi,e,'short',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); hit=True
        if hit: break
S['Q']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(2,len(sess)):
        c1=sess.iloc[i-2];c2=sess.iloc[i-1];c3=sess.iloc[i]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            d='long' if b3>0 else 'short'
            pi=candles.index.get_loc(sess.index[i]); e=c3['close']
            b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
            pnl=(ex-e) if d=='long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['R']=t

t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(2,len(sess)):
        c1=sess.iloc[i-2];c2=sess.iloc[i-1];c3=sess.iloc[i]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            d='short' if b3>0 else 'long'
            pi=candles.index.get_loc(sess.index[i]); e=c3['close']
            b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
            pnl=(ex-e) if d=='long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['S']=t

# V: Candle ratio 5/6 Tokyo
t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess)<12: continue
    for i in range(6,len(sess)):
        last6=sess.iloc[i-6:i]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5:
            pi=candles.index.get_loc(sess.index[i]); e=sess.iloc[i]['open']
            b,ex=sim_trail(candles,pi,e,'long',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        elif n_bull<=1:
            pi=candles.index.get_loc(sess.index[i]); e=sess.iloc[i]['open']
            b,ex=sim_trail(candles,pi,e,'short',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['V']=t

# Z: 3 jours consec → reversal
daily_data = {}
for day in trading_days:
    dc=candles[candles['date']==day]
    if len(dc)>=10: daily_data[day]={'dir':1 if dc.iloc[-1]['close']>dc.iloc[0]['open'] else -1}
t=[];
for di,day in enumerate(trading_days):
    if di<3: continue
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    dirs=[]
    for k in range(3):
        dk=trading_days[di-3+k]
        if dk in daily_data: dirs.append(daily_data[dk]['dir'])
    if len(dirs)<3 or len(set(dirs))>1: continue
    lon=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon)<6: continue
    pi=candles.index.get_loc(lon.index[0]); e=lon.iloc[0]['open']
    d='short' if dirs[0]>0 else 'long'
    b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
    pnl=(ex-e) if d=='long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['Z']=t

print("Building v10 strats...", flush=True)

# AA: Close near extreme London
t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(len(sess)):
        r=sess.iloc[i]; rng=r['high']-r['low']
        if rng<0.3*atr: continue
        body=abs(r['close']-r['open'])
        if body<0.2*atr: continue
        pos_in_range=(r['close']-r['low'])/rng
        if pos_in_range>=0.9:
            pi=candles.index.get_loc(sess.index[i])
            b,ex=sim_trail(candles,pi,r['close'],'long',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-r['close'])-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
        if pos_in_range<=0.1:
            pi=candles.index.get_loc(sess.index[i])
            b,ex=sim_trail(candles,pi,r['close'],'short',SL,atr,24,ACT,TRAIL)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(r['close']-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['AA']=t; print(f"  AA:{len(t)}", flush=True)

# AB: Twin candles Tokyo
t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(1,len(sess)):
        b1=sess.iloc[i-1]['close']-sess.iloc[i-1]['open']
        b2=sess.iloc[i]['close']-sess.iloc[i]['open']
        if b1*b2>0 and abs(b1)>=0.3*atr and abs(b2)>=0.3*atr:
            ratio=abs(b1)/abs(b2) if abs(b2)>0 else 99
            if 0.7<=ratio<=1.3:
                d='long' if b2>0 else 'short'
                pi=candles.index.get_loc(sess.index[i]); e=sess.iloc[i]['close']
                b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
                pnl=(ex-e) if d=='long' else (e-ex)
                t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['AB']=t; print(f"  AB:{len(t)}", flush=True)

# AC: Absorption Tokyo
t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(3,len(sess)):
        prev3_h=sess.iloc[i-3:i]['high'].max()
        prev3_l=sess.iloc[i-3:i]['low'].min()
        r=sess.iloc[i]; body=abs(r['close']-r['open'])
        if r['high']>=prev3_h and r['low']<=prev3_l and body>=0.5*atr:
            d='long' if r['close']>r['open'] else 'short'
            pi=candles.index.get_loc(sess.index[i])
            b,ex=sim_trail(candles,pi,r['close'],d,SL,atr,24,ACT,TRAIL)
            pnl=(ex-r['close']) if d=='long' else (r['close']-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['AC']=t; print(f"  AC:{len(t)}", flush=True)

# AD: Twin candles London
t=[];
for day in trading_days:
    pd_=prev_day(day); atr=daily_atr.get(pd_,global_atr) if pd_ else global_atr
    if atr==0: continue
    sess=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess)<6: continue
    for i in range(1,len(sess)):
        b1=sess.iloc[i-1]['close']-sess.iloc[i-1]['open']
        b2=sess.iloc[i]['close']-sess.iloc[i]['open']
        if b1*b2>0 and abs(b1)>=0.3*atr and abs(b2)>=0.3*atr:
            ratio=abs(b1)/abs(b2) if abs(b2)>0 else 99
            if 0.7<=ratio<=1.3:
                d='long' if b2>0 else 'short'
                pi=candles.index.get_loc(sess.index[i]); e=sess.iloc[i]['close']
                b,ex=sim_trail(candles,pi,e,d,SL,atr,24,ACT,TRAIL)
                pnl=(ex-e) if d=='long' else (e-ex)
                t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['AD']=t; print(f"  AD:{len(t)}", flush=True)

conn.close()

# ══════ EVALUATION ══════
def eval_portfolio(strat_keys, label, capital=1000.0, risk=0.01):
    combined=[]
    for sn in strat_keys:
        for t in S[sn]: combined.append({**t,'strat':sn})
    if len(combined)<10: return None
    combined.sort(key=lambda x:(x['ei'],x['strat']))
    al=[]; acc=[]
    for t in combined:
        al=[(xi,d) for xi,d in al if xi>=t['ei']]
        if any(d!=t['dir'] for _,d in al): continue
        acc.append(t); al.append((t['xi'],t['dir']))
    if len(acc)<10: return None
    cap=capital; peak=cap; max_dd=0; gp=0; gl=0; wins=0; months={}
    for t in acc:
        pnl=t['pnl_oz']*(cap*risk)/(t['sl_atr']*t['atr'])
        cap+=pnl
        if cap>peak: peak=cap
        dd=(cap-peak)/peak
        if dd<max_dd: max_dd=dd
        if pnl>0: gp+=pnl; wins+=1
        else: gl+=abs(pnl)
        mo=str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        months[mo]=months.get(mo,0)+pnl
    n=len(acc); mdd=max_dd*100; ret=(cap-capital)/capital*100
    pm=sum(1 for v in months.values() if v>0)
    return {'label':label,'n':n,'tpd':n/n_td,'capital':cap,'ret':ret,'mdd':mdd,
            'cal':ret/abs(mdd) if mdd<0 else 0,'pf':gp/(gl+0.01),'wr':wins/n*100,'pm':pm,'tm':len(months)}

champion = ['A','C','D','E','F','G','H','I','J','O','P','Q','R','S','V','Z']
new = ['AA','AB','AC','AD']
LEGEND = {'AA':'CloseExtreme_lon','AB':'TwinCandles_tok','AC':'Absorption_tok','AD':'TwinCandles_lon'}

print(f"\n{'='*110}")
print(f"  COMPARAISON — $1000, Risk 1%")
print(f"{'='*110}")
print(f"  {'Portfolio':60s} {'n':>5s} {'t/j':>5s} {'Capital':>12s} {'Rend%':>9s} {'DD%':>7s} {'Cal':>8s} {'PF':>5s} {'WR%':>4s} {'M+':>5s}")

tests = [(champion, "CHAMPION v6 (16 strats)")]
for s in new:
    tests.append((champion+[s], f"CHAMPION + {s} ({LEGEND[s]})"))
tests.append((champion+new, "CHAMPION + AA+AB+AC+AD (20 strats)"))
for combo in combinations(new,2):
    tests.append((champion+list(combo), f"CHAMPION + {'+'.join(combo)}"))

for keys,label in tests:
    r=eval_portfolio(keys,label)
    if r:
        print(f"  {label:60s} {r['n']:5.0f} {r['tpd']:5.1f} {r['capital']:12,.0f}$ {r['ret']:+8.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['pf']:.2f} {r['wr']:3.0f}% {r['pm']:2.0f}/{r['tm']:.0f}")

print(f"\n  LEGENDE: {LEGEND}")
print(f"{'='*110}")
