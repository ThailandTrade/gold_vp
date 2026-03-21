"""Test: portfolio existant + nouvelles strats v4"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import SL, ACT, TRAIL, STRATS, sim_exit, detect_all

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

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = candles[candles['date']==prev_d]
            if len(yc) > 0:
                prev2_day_data = prev_day_data
                prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                                 'high': float(yc['high'].max()), 'low': float(yc['low'].min()),
                                 'range': float(yc['high'].max()-yc['low'].min()),
                                 'body': float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
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
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

    # Base 11 strats
    detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add)

    # Nouvelles strats v4 (independantes, pas M1/M2 qui sont des sous-ensembles)
    if prev_day_data:
        pb = prev_day_data['body']; pr = prev_day_data['range']

        # D5: 2 jours consecutifs meme direction > 0.5 ATR → continuation London
        if 8.0<=hour<8.1 and 'D5' not in trig and prev2_day_data:
            if abs(pb) >= 0.5*atr and abs(prev2_day_data['body']) >= 0.5*atr:
                if pb > 0 and prev2_day_data['body'] > 0:
                    add('D5','long',row['open']); trig['D5']=True
                elif pb < 0 and prev2_day_data['body'] < 0:
                    add('D5','short',row['open']); trig['D5']=True

        # D6: 2 jours consecutifs direction opposee → last direction London
        if 8.0<=hour<8.1 and 'D6' not in trig and prev2_day_data:
            if abs(pb) >= 0.5*atr and abs(prev2_day_data['body']) >= 0.5*atr:
                if pb > 0 and prev2_day_data['body'] < 0:
                    add('D6','long',row['open']); trig['D6']=True
                elif pb < 0 and prev2_day_data['body'] > 0:
                    add('D6','short',row['open']); trig['D6']=True

        # D7: Prev day close near extreme → continuation Tokyo
        if 0.0<=hour<0.1 and 'D7' not in trig and pr > 0:
            pos_close = (prev_day_data['close'] - prev_day_data['low']) / pr
            if pos_close >= 0.9:
                add('D7','long',row['open']); trig['D7']=True
            elif pos_close <= 0.1:
                add('D7','short',row['open']); trig['D7']=True

        # D8: Previous inside day → breakout London
        if 8.0<=hour<14.5 and 'D8' not in trig and prev2_day_data:
            if prev_day_data['high'] < prev2_day_data['high'] and prev_day_data['low'] > prev2_day_data['low']:
                if row['close'] > prev_day_data['high']:
                    add('D8','long',row['close']); trig['D8']=True
                elif row['close'] < prev_day_data['low']:
                    add('D8','short',row['close']); trig['D8']=True

    # S6: GAP Tok→Lon > 1.0 ATR
    if 8.0<=hour<8.1 and 'S6' not in trig:
        tc = candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc) >= 5:
            gap = (row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap) >= 1.0: add('S6','long' if gap>0 else 'short',row['open']); trig['S6']=True

    # S7: London 4h momentum → continuation NY
    if 14.5<=hour<14.6 and 'S7' not in trig:
        l4h = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,12,0,tz='UTC'))]
        if len(l4h) >= 40:
            m = (l4h.iloc[-1]['close'] - l4h.iloc[0]['open']) / atr
            if abs(m) >= 1.0:
                add('S7','long' if m>0 else 'short',row['open']); trig['S7']=True

    # S8: Tokyo+London move >1.5ATR → continuation NY
    if 14.5<=hour<14.6 and 'S8' not in trig and len(tv) >= 100:
        day_move = (tv.iloc[-1]['close'] - tv.iloc[0]['open']) / atr
        if abs(day_move) >= 1.5:
            add('S8','long' if day_move>0 else 'short',row['open']); trig['S8']=True

    # V1: Low vol + big candle Tokyo
    if 0.0<=hour<6.0 and 'V1' not in trig:
        if atr < 3.0:
            body = row['close'] - row['open']
            if abs(body) >= 0.8*atr:
                add('V1','long' if body>0 else 'short',row['close']); trig['V1']=True

    # M3: Big candle dans le sens du day trend (1 trigger/jour)
    if 0.0<=hour<21.0 and 'M3' not in trig and len(tv)>=20:
        body = row['close'] - row['open']
        day_dir = tv.iloc[-1]['close'] - tv.iloc[0]['open']
        if abs(body) >= 1.0*atr and body * day_dir > 0:
            add('M3','long' if body>0 else 'short',row['close']); trig['M3']=True

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

base = list(STRATS)
new_strats = ['D5','D6','D7','D8','S6','S7','S8','V1','M3']

print("\n" + "="*130)
print("COMBOS: BASE 11 strats + nouvelles v4")
print("="*130)

r = eval_combo(tuple(base))
print(f"\n  BASE (11 strats):")
print(f"    n={r['n']:.0f} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Cal={r['cal']:.1f} Rend={r['ret']:+.0f}% M+={r['pm']:.0f}/{r['tm']:.0f}")

print(f"\n  +1 nouvelle:")
print(f"  {'Ajout':10s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>10s} {'M+':>5s} {'Split':>5s} {'T':>3s}")
print(f"  {'-'*95}")
for ns in new_strats:
    combo = tuple(sorted(base + [ns]))
    r = eval_combo(combo)
    if r:
        sp = "OK" if r['split'] else "!!"
        print(f"  +{ns:9s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {sp:>5s} {r['tiers']}/3")

print(f"\n  +2 nouvelles (top 10 Calmar, split OK):")
print(f"  {'Ajout':20s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>10s} {'M+':>5s} {'T':>3s}")
print(f"  {'-'*95}")
res2 = []
for nc in combinations(new_strats, 2):
    combo = tuple(sorted(base + list(nc)))
    r = eval_combo(combo)
    if r and r['split'] and r['both']: res2.append((nc, r))
res2.sort(key=lambda x: x[1]['cal'], reverse=True)
for nc, r in res2[:10]:
    print(f"  +{'+'.join(nc):19s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

print(f"\n  +3 nouvelles (top 5 Calmar, split OK):")
res3 = []
for nc in combinations(new_strats, 3):
    combo = tuple(sorted(base + list(nc)))
    r = eval_combo(combo)
    if r and r['split'] and r['both']: res3.append((nc, r))
res3.sort(key=lambda x: x[1]['cal'], reverse=True)
for nc, r in res3[:5]:
    print(f"  +{'+'.join(nc):28s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

# All
combo = tuple(sorted(base + new_strats))
r = eval_combo(combo)
if r:
    sp = "OK" if r['split'] else "!!"
    print(f"\n  +ALL ({len(combo)} strats): {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {sp} {r['tiers']}/3")

print()
