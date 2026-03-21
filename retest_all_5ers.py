"""Retest complet sur donnees 5ers — toutes les strats."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import SL, ACT, TRAIL, ALL_STRATS, sim_exit, detect_all

SPREAD = 0.20  # spread fixe 5ers

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
conn.close()
n_td = len(set(candles['date'].unique()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

print("Collecte de TOUTES les strats...", flush=True)
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
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-SPREAD,'atr':atr,'ei':ci,'xi':ci+b})
    detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

print(f"Done. {len(S)} strats.", flush=True)

# Stats individuelles
print("\n" + "="*120)
print(f"TOUTES LES STRATS — Donnees 5ers (spread fixe {SPREAD} pts)")
print("="*120)
print(f"{'Strat':>14s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*120)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 15: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1, t2, t3] if x > 0)
    split = f1 > 0 and f2 > 0
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>14s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good)}")

# Combos
if len(good) >= 3:
    strat_arrays = {}
    for sn in good:
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
        t1s = sum(pnls[:n//3]); t2s = sum(pnls[n//3:2*n//3]); t3s = sum(pnls[2*n//3:])
        pm = sum(1 for v in months.values() if v > 0)
        return {
            'combo': '+'.join(combo), 'ns': len(combo), 'n': n,
            'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
            'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
            'split': p1 > 0 and p2 > 0,
            'tiers': sum(1 for x in [t1s, t2s, t3s] if x > 0),
            'both': has_s and has_l, 'pm': pm, 'tm': len(months),
        }

    print(f"\n{'='*130}")
    print(f"MEILLEUR COMBO PAR TAILLE (Calmar, split OK, L+S)")
    print(f"{'='*130}")
    for sz in range(3, min(len(good)+1, 12)):
        best = None
        for combo in combinations(good, sz):
            r = eval_combo(combo)
            if r and r['split'] and r['tiers']>=2 and r['both']:
                if best is None or r['cal'] > best['cal']:
                    best = r
        if best:
            print(f"  {sz:2d} strats: {best['combo'][:70]:70s} n={best['n']:5.0f} PF={best['pf']:.2f} WR={best['wr']:.0f}% DD={best['mdd']:+.1f}% Cal={best['cal']:.1f} Rend={best['ret']:+.0f}% M+={best['pm']:.0f}/{best['tm']:.0f}")

    print(f"\n  TOP 15 CALMAR (split OK, L+S):")
    print(f"  {'Combo':60s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>10s} {'M+':>5s} {'T':>3s}")
    results = []
    for sz in range(3, min(len(good)+1, 10)):
        for combo in combinations(good, sz):
            r = eval_combo(combo)
            if r and r['split'] and r['tiers']>=2 and r['both']:
                results.append(r)
    results.sort(key=lambda x: x['cal'], reverse=True)
    for r in results[:15]:
        print(f"  {r['combo'][:60]:60s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

print()
