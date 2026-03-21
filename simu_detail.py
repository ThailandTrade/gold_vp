"""
Simulation detaillee mois par mois — 11 strats, noms par session.
Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout (sur CLOSE)
Usage: python simu_detail.py [capital] [risk%]
  Ex: python simu_detail.py 100000 0.1
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import SL, ACT, TRAIL, STRATS, sim_exit, detect_all

capital = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0
risk = float(sys.argv[2]) / 100 if len(sys.argv) > 2 else 0.02

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

S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = candles[candles['date']==prev_d]
            if len(yc) > 0:
                prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                                 'high': float(yc['high'].max()), 'low': float(yc['low'].min())}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b,'strat':sn})
    detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add)

combined = []
for sn in STRATS:
    for t in S.get(sn, []): combined.append(t)
combined.sort(key=lambda x: (x['ei'], x['strat']))
al = []; acc = []
for t in combined:
    al = [(xi, d) for xi, d in al if xi >= t['ei']]
    if any(d != t['dir'] for _, d in al): continue
    acc.append(t); al.append((t['xi'], t['dir']))

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
print(f"  11 strats -- ${capital:,.0f}, Risk {risk*100:.2f}%")
print(f"  Config: TRAIL SL={SL} ACT={ACT} TRAIL={TRAIL}, pas de timeout (sur CLOSE)")
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
    print(f"    {'Strat':>12s} {'Trades':>7s} {'W':>3s} {'L':>3s} {'WR':>5s} {'PnL $':>14s}")
    for sn in sorted(m['strats'].keys()):
        ss = m['strats'][sn]
        wr_s = ss['w']/ss['n']*100 if ss['n'] else 0
        print(f"    {sn:>12s} {ss['n']:7d} {ss['w']:3d} {ss['n']-ss['w']:3d} {wr_s:4.0f}% ${ss['pnl']:+14,.2f}")

pm = sum(1 for m in months.values() if sum(m['pnls']) > 0)
gp_all = sum(m['gp'] for m in months.values())
gl_all = sum(m['gl'] for m in months.values()) + 0.01
print()
print("="*140)
print(f"  RESUME")
print(f"  Capital: ${capital:,.0f} -> ${cap:,.2f} ({(cap-capital)/capital*100:+.1f}%)")
print(f"  Trades: {len(acc)} | WR: {sum(m['wins'] for m in months.values())/len(acc)*100:.0f}% | PF: {gp_all/gl_all:.2f}")
print(f"  Max DD: {global_dd:.1f}%")
print(f"  Mois positifs: {pm}/{len(months)}")
print("="*140)
