"""Derniers 100 trades backtest — stats et detail"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from collections import defaultdict
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

SL, ACT, TRAIL, MX = 1.5, 0.3, 0.3, 12
def sim_exit(cdf, pos, entry, d, atr):
    best = entry; stop = entry + SL*atr if d == 'short' else entry - SL*atr; ta = False
    for j in range(1, MX+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= ACT*atr: ta = True
            if ta: stop = max(stop, best - TRAIL*atr)
            if b['low'] <= stop: return j, stop
            if b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= ACT*atr: ta = True
            if ta: stop = min(stop, best + TRAIL*atr)
            if b['high'] >= stop: return j, stop
            if b['close'] > stop: return j, b['close']
    if pos+MX < len(cdf): return MX, cdf.iloc[pos+MX]['close']
    return MX, entry

all_trades = []
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
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        all_trades.append({'date':str(today),'strat':sn,'dir':d,'time':ct.strftime('%H:%M'),
                           'entry':round(e,2),'exit':round(ex,2),'pnl_oz':round(pnl-get_sp(today),3),'bars':b})
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
    if 0.0<=hour<6.0 and 'V' not in trig and len(tok)>=7:
        last6=tok.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: add('V','long',row['close']); trig['V']=True
        elif n_bull<=1: add('V','short',row['close']); trig['V']=True
    if 0.0<=hour<6.0 and 'AC' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('AC','long' if row['close']>row['open'] else 'short',row['close']); trig['AC']=True

last100 = all_trades[-100:]
pnls = [t['pnl_oz'] for t in last100]
wins = [p for p in pnls if p > 0]
losses = [p for p in pnls if p < 0]
gp = sum(wins); gl = abs(sum(losses))+0.001

print("="*100)
print(f"DERNIERS 100 TRADES — TRp SL=1.5 ACT=0.3 TRAIL=0.3 T12")
print(f"Periode: {last100[0]['date']} a {last100[-1]['date']}")
print("="*100)
print(f"  WR: {len(wins)}/100 = {len(wins)}%")
print(f"  PF: {gp/gl:.2f}")
print(f"  Avg win:  {np.mean(wins):+.3f} oz" if wins else "  Avg win: --")
print(f"  Avg loss: {np.mean(losses):+.3f} oz" if losses else "  Avg loss: --")
print(f"  Total PnL: {sum(pnls):+.2f} oz")
print()

strat_stats = defaultdict(list)
for t in last100: strat_stats[t['strat']].append(t['pnl_oz'])
print(f"{'Strat':>5s} {'n':>4s} {'W':>3s} {'L':>3s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s}")
for sn in sorted(strat_stats.keys()):
    pl = strat_stats[sn]
    w = sum(1 for p in pl if p > 0); l = sum(1 for p in pl if p <= 0)
    gps = sum(p for p in pl if p > 0); gls = abs(sum(p for p in pl if p < 0))+0.001
    print(f"{sn:>5s} {len(pl):4d} {w:3d} {l:3d} {w/len(pl)*100:4.0f}% {gps/gls:6.2f} {np.mean(pl):+8.3f} {sum(pl):+8.2f}")

print()
print("DETAIL 100 TRADES:")
print(f"{'Date':>12s} {'Strat':>5s} {'Dir':>5s} {'Heure':>6s} {'Entry':>9s} {'Exit':>9s} {'PnL oz':>8s} {'Bars':>4s}")
for t in last100:
    marker = "  W" if t['pnl_oz'] > 0 else "  L"
    print(f"{t['date']:>12s} {t['strat']:>5s} {t['dir']:>5s} {t['time']:>6s} {t['entry']:9.2f} {t['exit']:9.2f} {t['pnl_oz']:+8.3f} {t['bars']:4d}{marker}")
