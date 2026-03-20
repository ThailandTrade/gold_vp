"""
Compare backtest AVANT vs APRES fix trailing.
Fix: apres trailing update, si close deja au-dela du stop → exit au close.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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
SL, ACT, TRAIL = 0.75, 0.5, 0.3
SLIPPAGE = 0.10

def sim_trail_OLD(cdf, pos, entry, d, sl, atr, mx, act, trail):
    """ANCIEN: pas de re-check apres trailing"""
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

def sim_trail_NEW(cdf, pos, entry, d, sl, atr, mx, act, trail):
    """NOUVEAU: apres trailing update, re-check close vs stop"""
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
            # FIX: close deja sous le nouveau stop → exit au close
            if b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
            # FIX: close deja au-dessus du nouveau stop → exit au close
            if b['close'] > stop: return j, b['close']
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

daily_data = {}
for day in trading_days:
    dc = candles[candles['date'] == day]
    if len(dc) >= 10: daily_data[day] = {'dir': 1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1}

# Collecter trades bougie par bougie (no look-ahead) avec les 2 methodes
print("Collecte bougie par bougie...", flush=True)
S_old = {}; S_new = {}
n_td = len(set(candles['date'].unique()))

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
    le = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<le)]

    def add(sn, d, e):
        # OLD
        b_o, ex_o = sim_trail_OLD(candles, ci, e, d, SL, atr, 24, ACT, TRAIL)
        pnl_o = (ex_o-e) if d=='long' else (e-ex_o)
        S_old.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl_o-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b_o})
        # NEW
        b_n, ex_n = sim_trail_NEW(candles, ci, e, d, SL, atr, 24, ACT, TRAIL)
        pnl_n = (ex_n-e) if d=='long' else (e-ex_n)
        S_new.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl_n-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b_n})

    if 8.0<=hour<8.1 and 'C' not in trig and len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('C','short' if m>0 else 'long',row['open']); trig['C']=True
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
        b1=tok.iloc[-2];b2=tok.iloc[-1]
        b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('F','long' if b2b>0 else 'short',b2['close']); trig['F']=True
    if 14.5<=hour<14.6 and 'G' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: add('G','long' if body>0 else 'short',row['close']); trig['G']=True
    if 8.0<=hour<8.1 and 'H' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('H','long' if m>0 else 'short',row['open']); trig['H']=True
    if 15.5<=hour<15.6 and 'I' not in trig:
        ny1=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1)>=10:
            m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
            if abs(m)>=1.0: add('I','short' if m>0 else 'long',row['open']); trig['I']=True
    if 8.0<=hour<8.1 and 'J' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: add('J','long' if body>0 else 'short',row['close']); trig['J']=True
    if 0.0<=hour<6.0 and 'O' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('O','long' if body>0 else 'short',row['close']); trig['O']=True
    if 15.0<=hour<21.5 and 'P' not in trig:
        if 'P_h' not in trig:
            orb=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['P_h']=float(orb['high'].max()); trig['P_l']=float(orb['low'].min())
        if 'P_h' in trig:
            if row['close']>trig['P_h']: add('P','long',row['close']); trig['P']=True
            elif row['close']<trig['P_l']: add('P','short',row['close']); trig['P']=True
    if 8.0<=hour<14.5 and 'Q' not in trig and len(lon)>=2:
        pb=lon.iloc[-2];cb=lon.iloc[-1]
        if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('Q','long',cb['close']); trig['Q']=True
        elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('Q','short',cb['close']); trig['Q']=True
    if 0.0<=hour<6.0 and 'R' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            add('R','long' if b3>0 else 'short',c3['close']); trig['R']=True
    if 8.0<=hour<14.5 and 'S' not in trig and len(lon)>=3:
        c1=lon.iloc[-3];c2=lon.iloc[-2];c3=lon.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            add('S','short' if b3>0 else 'long',c3['close']); trig['S']=True
    if 0.0<=hour<6.0 and 'V' not in trig and len(tok)>=7:
        last6=tok.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: add('V','long',row['close']); trig['V']=True
        elif n_bull<=1: add('V','short',row['close']); trig['V']=True
    if 8.0<=hour<14.5 and 'AA' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('AA','long',row['close']); trig['AA']=True
            elif pir<=0.1: add('AA','short',row['close']); trig['AA']=True
    if 0.0<=hour<6.0 and 'AC' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('AC','long' if row['close']>row['open'] else 'short',row['close']); trig['AC']=True

print("Done.", flush=True)

STRATS = ['AA','AC','C','D','E','F','G','H','I','J','O','P','Q','R','S','V']

def eval_portfolio(S_data, label, capital=1000.0, risk=0.01):
    combined = []
    for sn in STRATS:
        for t in S_data.get(sn, []): combined.append({**t, 'strat': sn})
    combined.sort(key=lambda x: (x['ei'], x['strat']))
    al = []; acc = []
    for t in combined:
        al = [(xi, d) for xi, d in al if xi >= t['ei']]
        if any(d != t['dir'] for _, d in al): continue
        acc.append(t); al.append((t['xi'], t['dir']))
    n = len(acc)
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
        months[mo] = months.get(mo, 0.0) + pnl
    pm = sum(1 for v in months.values() if v > 0)
    return n, cap, max_dd*100, gp/(gl+0.01), wins/n*100 if n else 0, pm, len(months)

# Stats par strat
print(f"\n{'='*90}")
print(f"STATS PAR STRAT — OLD vs NEW")
print(f"{'='*90}")
print(f"  {'Strat':5s} {'OLD n':>6s} {'OLD PF':>7s} {'NEW n':>6s} {'NEW PF':>7s} {'Diff':>6s}")
for sn in sorted(STRATS):
    old = pd.DataFrame(S_old.get(sn,[]))
    new = pd.DataFrame(S_new.get(sn,[]))
    if len(old) < 5: continue
    old_gp = old[old['pnl_oz']>0]['pnl_oz'].sum(); old_gl = abs(old[old['pnl_oz']<0]['pnl_oz'].sum())+0.001
    new_gp = new[new['pnl_oz']>0]['pnl_oz'].sum(); new_gl = abs(new[new['pnl_oz']<0]['pnl_oz'].sum())+0.001
    old_pf = old_gp/old_gl; new_pf = new_gp/new_gl
    print(f"  {sn:5s} {len(old):6d} {old_pf:7.2f} {len(new):6d} {new_pf:7.2f} {new_pf-old_pf:+6.2f}")

# Portfolio
print(f"\n{'='*90}")
print(f"PORTFOLIO PERSO (16 strats) — $1000, Risk 1%")
print(f"{'='*90}")
n_o, cap_o, dd_o, pf_o, wr_o, pm_o, tm_o = eval_portfolio(S_old, "OLD")
n_n, cap_n, dd_n, pf_n, wr_n, pm_n, tm_n = eval_portfolio(S_new, "NEW")
print(f"  {'':15s} {'Trades':>7s} {'Capital':>14s} {'DD%':>7s} {'PF':>6s} {'WR%':>5s} {'M+':>5s}")
print(f"  {'AVANT (bug)':15s} {n_o:7d} {cap_o:14,.0f}$ {dd_o:+6.1f}% {pf_o:6.2f} {wr_o:4.0f}% {pm_o}/{tm_o}")
print(f"  {'APRES (fix)':15s} {n_n:7d} {cap_n:14,.0f}$ {dd_n:+6.1f}% {pf_n:6.2f} {wr_n:4.0f}% {pm_n}/{tm_n}")

# Compter combien de trades sont affectes
n_affected = 0
for sn in STRATS:
    old_list = S_old.get(sn, [])
    new_list = S_new.get(sn, [])
    for i in range(min(len(old_list), len(new_list))):
        if abs(old_list[i]['pnl_oz'] - new_list[i]['pnl_oz']) > 0.01:
            n_affected += 1
total = sum(len(S_old.get(sn,[])) for sn in STRATS)
print(f"\n  Trades affectes par le fix: {n_affected}/{total} ({n_affected/total*100:.1f}%)")
print(f"{'='*90}")
