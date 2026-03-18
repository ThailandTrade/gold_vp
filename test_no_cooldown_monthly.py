"""
Sans cooldown — detail mois par mois
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
SL, ACT, TRAIL = 0.75, 0.5, 0.3

strats_list = ['A','C','D','E','F','G','H','I','J','O','P','Q','R','S']

def collect(cooldown):
    S = {}
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

        # A
        if len(tok) >= 18:
            lvl = tok.iloc[:12]['high'].max()
            for i in range(12, len(tok)):
                if tok.iloc[i]['close'] > lvl:
                    add('A','long',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
        # C
        if len(tok) >= 10:
            m = (tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                l2 = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
                if len(l2)>=6: add('C','short' if m>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        # D
        tc = candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
        if len(tc)>=5:
            l2 = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6:
                gap=(l2.iloc[0]['open']-tc.iloc[-1]['close'])/atr
                if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        # E
        kz = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5:
                post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
                if len(post)>=6: add('E','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
        # F
        if len(tok)>=8:
            for i in range(1,len(tok)):
                b1b=tok.iloc[i-1]['close']-tok.iloc[i-1]['open']; b2b=tok.iloc[i]['close']-tok.iloc[i]['open']
                if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
                if b1b*b2b>=0 or abs(b2b)<=abs(b1b): continue
                add('F','long' if b2b>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i]))
                if cooldown: break
        # G
        if len(ny)>=6:
            body=ny.iloc[0]['close']-ny.iloc[0]['open']
            if abs(body)>=0.3*atr and len(ny)>=2:
                add('G','long' if body>0 else 'short',ny.iloc[1]['open'],candles.index.get_loc(ny.index[1]))
        # H
        if len(tok)>=9:
            l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
                if len(l2)>=6: add('H','long' if m>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        # I
        ny1=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
        if len(ny1)>=10:
            m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
                if len(post)>=6: add('I','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
        # J
        if len(lon)>=6:
            body=lon.iloc[0]['close']-lon.iloc[0]['open']
            if abs(body)>=0.3*atr and len(lon)>=2:
                add('J','long' if body>0 else 'short',lon.iloc[1]['open'],candles.index.get_loc(lon.index[1]))
        # O
        if len(tok)>=6:
            for i in range(len(tok)):
                body=tok.iloc[i]['close']-tok.iloc[i]['open']
                if abs(body)>=1.0*atr:
                    add('O','long' if body>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i]))
                    if cooldown: break
        # P
        if len(ny)>=12:
            oh=ny.iloc[:6]['high'].max(); ol=ny.iloc[:6]['low'].min()
            for i in range(6,len(ny)):
                r=ny.iloc[i]
                if r['close']>oh:
                    add('P','long',r['close'],candles.index.get_loc(ny.index[i]))
                    if cooldown: break
                elif r['close']<ol:
                    add('P','short',r['close'],candles.index.get_loc(ny.index[i]))
                    if cooldown: break
        # Q
        if len(lon)>=6:
            for i in range(1,len(lon)):
                pb=lon.iloc[i-1]; cb=lon.iloc[i]; hit=False
                if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                    add('Q','long',cb['close'],candles.index.get_loc(lon.index[i])); hit=True
                elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                    add('Q','short',cb['close'],candles.index.get_loc(lon.index[i])); hit=True
                if hit and cooldown: break
        # R
        if len(tok)>=6:
            for i in range(2,len(tok)):
                c1=tok.iloc[i-2];c2=tok.iloc[i-1];c3=tok.iloc[i]
                b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
                if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                    add('R','long' if b3>0 else 'short',c3['close'],candles.index.get_loc(tok.index[i]))
                    if cooldown: break
        # S
        if len(lon)>=6:
            for i in range(2,len(lon)):
                c1=lon.iloc[i-2];c2=lon.iloc[i-1];c3=lon.iloc[i]
                b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
                if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                    add('S','short' if b3>0 else 'long',c3['close'],candles.index.get_loc(lon.index[i]))
                    if cooldown: break
    return S

def run_portfolio(S, label, capital=1000.0, risk=0.01):
    combined = []
    for sn in strats_list:
        for t in S.get(sn, []): combined.append({**t, 'strat': sn})
    combined.sort(key=lambda x: (x['ei'], x['strat']))
    al = []; acc = []
    for t in combined:
        al = [(xi, d) for xi, d in al if xi >= t['ei']]
        if any(d != t['dir'] for _, d in al): continue
        acc.append(t); al.append((t['xi'], t['dir']))
    cap = capital; months = {}
    peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0
    for t in acc:
        pnl = t['pnl_oz'] * (cap * risk) / (t['sl_atr'] * t['atr'])
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        if mo not in months: months[mo] = {'pnl':0,'n':0,'wins':0,'gp':0,'gl':0,'cap_start':cap-pnl}
        months[mo]['pnl'] += pnl; months[mo]['n'] += 1
        if pnl > 0: months[mo]['wins'] += 1; months[mo]['gp'] += pnl
        else: months[mo]['gl'] += abs(pnl)
    return acc, months, len(acc), cap, max_dd*100, gp/(gl+0.01), wins/len(acc)*100 if acc else 0

print("Cooldown...", flush=True)
S_cd = collect(True)
print("No cooldown...", flush=True)
S_nocd = collect(False)
conn.close()

for label, S_data in [("AVEC COOLDOWN", S_cd), ("SANS COOLDOWN", S_nocd)]:
    acc, months, n, cap, mdd, pf, wr = run_portfolio(S_data, label)
    ret = (cap - 1000) / 1000 * 100
    print(f"\n{'='*90}")
    print(f"  {label} — {n} trades, Capital ${cap:,.0f}, Rend {ret:+.0f}%, DD {mdd:+.1f}%, PF {pf:.2f}, WR {wr:.0f}%")
    print(f"{'='*90}")
    print(f"  {'Mois':8s} {'Trades':>6s} {'WR':>5s} {'PF':>6s} {'PnL':>12s} {'Cap fin':>12s}")
    cap_run = 1000.0
    for mo in sorted(months.keys()):
        m = months[mo]
        cap_run += m['pnl']
        mo_wr = m['wins']/m['n']*100 if m['n']>0 else 0
        mo_pf = m['gp']/(m['gl']+0.01) if m['gl']>0 else 99
        print(f"  {mo:8s} {m['n']:6d} {mo_wr:4.0f}% {mo_pf:6.2f} {m['pnl']:+12,.2f} {cap_run:12,.2f}")
    pm = sum(1 for m in months.values() if m['pnl'] > 0)
    print(f"  Mois positifs: {pm}/{len(months)}")
