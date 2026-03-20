"""Simulation detaillee mois par mois — AA+D+E+F+H+O, SL=1.0 ACT=0.5 TRAIL=0.75 MX=12"""
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
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]
    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b,'strat':sn})
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

STRATS = ['AA','D','E','F','H','O']
combined = []
for sn in STRATS:
    for t in S.get(sn, []): combined.append(t)
combined.sort(key=lambda x: (x['ei'], x['strat']))
al = []; acc = []
for t in combined:
    al = [(xi, d) for xi, d in al if xi >= t['ei']]
    if any(d != t['dir'] for _, d in al): continue
    acc.append(t); al.append((t['xi'], t['dir']))

capital = 1000.0; risk = 0.01
cap = capital; peak = cap; global_dd = 0; months = {}
for t in acc:
    pnl = t['pnl_oz'] * (cap * risk) / (t['sl_atr'] * t['atr'])
    cap += pnl
    if cap > peak: peak = cap
    dd = (cap - peak) / peak * 100
    if dd < global_dd: global_dd = dd
    mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
    if mo not in months:
        months[mo] = {'cap_start': cap-pnl, 'cap_end': cap, 'n': 0, 'wins': 0,
                      'gp': 0, 'gl': 0, 'pnls': [], 'dd_worst': 0, 'strats': {}}
    m = months[mo]; m['cap_end'] = cap; m['n'] += 1; m['pnls'].append(pnl)
    sn = t['strat']
    if sn not in m['strats']: m['strats'][sn] = {'n':0,'w':0,'pnl':0}
    m['strats'][sn]['n'] += 1
    if pnl > 0: m['wins'] += 1; m['gp'] += pnl; m['strats'][sn]['w'] += 1
    else: m['gl'] += abs(pnl)
    m['strats'][sn]['pnl'] += pnl
    if dd < m['dd_worst']: m['dd_worst'] = dd
    if cap > peak: peak = cap

print("="*140)
print("  AA+D+E+F+H+O -- $1,000, Risk 1% -- Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75 MX=12 (sur CLOSE)")
print("="*140)

for mo in sorted(months.keys()):
    m = months[mo]
    wr = m['wins']/m['n']*100 if m['n'] else 0
    pf = m['gp']/(m['gl']+0.01)
    pnl_total = sum(m['pnls'])
    pnl_pct = pnl_total / m['cap_start'] * 100 if m['cap_start'] > 0 else 0
    marker = "+" if pnl_total > 0 else "---"
    print()
    print(f"  {marker} {mo}")
    print(f"    {m['n']} trades | {m['wins']}W {m['n']-m['wins']}L | WR {wr:.0f}% | PF {pf:.2f}")
    print(f"    PnL: ${pnl_total:+,.2f} ({pnl_pct:+.1f}%) | DD max: {m['dd_worst']:+.1f}%")
    print(f"    Capital: ${m['cap_start']:,.2f} -> ${m['cap_end']:,.2f}")
    print(f"    {'Strat':>5s} {'Trades':>7s} {'W':>3s} {'L':>3s} {'WR':>5s} {'PnL $':>12s}")
    for sn in sorted(m['strats'].keys()):
        ss = m['strats'][sn]
        wr_s = ss['w']/ss['n']*100 if ss['n'] else 0
        print(f"    {sn:>5s} {ss['n']:7d} {ss['w']:3d} {ss['n']-ss['w']:3d} {wr_s:4.0f}% ${ss['pnl']:+12,.2f}")

pm = sum(1 for m in months.values() if sum(m['pnls']) > 0)
gp_all = sum(m['gp'] for m in months.values())
gl_all = sum(m['gl'] for m in months.values()) + 0.01
print()
print("="*140)
print(f"  RESUME")
print(f"  Capital: $1,000 -> ${cap:,.2f} ({(cap-capital)/capital*100:+.1f}%)")
print(f"  Trades: {len(acc)} | WR: {sum(m['wins'] for m in months.values())/len(acc)*100:.0f}% | PF: {gp_all/gl_all:.2f}")
print(f"  Max DD: {global_dd:.1f}%")
print(f"  Mois positifs: {pm}/{len(months)}")
print("="*140)
