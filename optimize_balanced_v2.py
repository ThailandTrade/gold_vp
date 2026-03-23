"""
Re-optimise les exits avec la logique TPSL corrigee (TP sur HIGH/LOW au TARGET).
Cherche le sweet spot WR 45-80% + PF > 1.1.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import compute_indicators, detect_all, sim_exit_custom
from strat_exits import DEFAULT_EXIT

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

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

# Collect ALL signals
print("Precalcul...", flush=True)
c = candles.copy()
c = compute_indicators(c)

print("Collecte signaux...", flush=True)
S = {}  # sn -> list of (ci, dir, entry, atr, date)
prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
for ci in range(200, len(c)):
    row = c.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
            if len(yc) > 0:
                prev2_day_data = prev_day_data
                prev_day_data = {'open':float(yc.iloc[0]['open']),'close':float(yc.iloc[-1]['close']),
                                 'high':float(yc['high'].max()),'low':float(yc['low'].min()),
                                 'range':float(yc['high'].max()-yc['low'].min()),
                                 'body':float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = c[(c['ts_dt']>=ds)&(c['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    def add(sn, d, e):
        S.setdefault(sn,[]).append({'ci':ci,'dir':d,'entry':e,'atr':atr,'date':today})
    detect_all(c, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

print(f"Done. {len(S)} strats, {sum(len(v) for v in S.values())} signaux total.\n")

# Test configs — TPSL + TRAIL
SL_VALS = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_VALS = [0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
TRAIL_SL = [0.5, 1.0, 1.5, 2.0]
TRAIL_ACT = [0.3, 0.5, 0.75]
TRAIL_TR = [0.3, 0.5, 0.75, 1.0]

print("="*100)
print("OPTIMISATION EXITS — LOGIQUE TPSL CORRIGEE (TP sur HIGH/LOW au TARGET)")
print("="*100)
print(f"\n{'Strat':>22s} {'Type':>5s} {'SL':>5s} {'P2':>5s} {'P3':>5s} {'PF':>6s} {'WR':>5s} {'n':>5s} {'Avg':>7s} {'Split':>5s}")
print("-"*85)

best_configs = {}

for sn in sorted(S.keys()):
    sigs = S[sn]
    if len(sigs) < 20: continue
    is_open = sn in OPEN_STRATS
    best = None

    # TPSL configs
    for sl in SL_VALS:
        for tp in TP_VALS:
            if tp >= sl: continue
            pnls = []
            for sig in sigs:
                ci = sig['ci']; d = sig['dir']; entry = sig['entry']; atr = sig['atr']
                b, ex = sim_exit_custom(c, ci, entry, d, atr, 'TPSL', sl, tp, 0, check_entry_candle=is_open)
                pnl = ((ex-entry) if d=='long' else (entry-ex)) - get_sp(sig['date'])
                pnls.append(pnl)

            n = len(pnls)
            if n < 20: continue
            wins = sum(1 for p in pnls if p > 0)
            wr = wins/n*100
            gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
            pf = gp/gl
            mid = n//2; split = np.mean(pnls[:mid])>0 and np.mean(pnls[mid:])>0
            if pf >= 1.05 and split:
                score = pf * min(wr, 80) / 100
                if best is None or score > best['score']:
                    best = {'type':'TPSL','sl':sl,'p2':tp,'p3':0,'pf':pf,'wr':wr,'n':n,'avg':np.mean(pnls),'split':split,'score':score}

    # TRAIL configs
    for sl in TRAIL_SL:
        for act in TRAIL_ACT:
            for trail in TRAIL_TR:
                if trail > sl: continue
                pnls = []
                for sig in sigs:
                    ci = sig['ci']; d = sig['dir']; entry = sig['entry']; atr = sig['atr']
                    b, ex = sim_exit_custom(c, ci, entry, d, atr, 'TRAIL', sl, act, trail, check_entry_candle=is_open)
                    pnl = ((ex-entry) if d=='long' else (entry-ex)) - get_sp(sig['date'])
                    pnls.append(pnl)

                n = len(pnls)
                if n < 20: continue
                wins = sum(1 for p in pnls if p > 0)
                wr = wins/n*100
                gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
                pf = gp/gl
                mid = n//2; split = np.mean(pnls[:mid])>0 and np.mean(pnls[mid:])>0
                if pf >= 1.05 and split:
                    score = pf * min(wr, 80) / 100
                    if best is None or score > best['score']:
                        best = {'type':'TRAIL','sl':sl,'p2':act,'p3':trail,'pf':pf,'wr':wr,'n':n,'avg':np.mean(pnls),'split':split,'score':score}

    if best:
        sp = 'OK' if best['split'] else '!!'
        marker = ' <--' if best['pf'] >= 1.15 and best['wr'] >= 45 else ''
        print(f"{sn:>22s} {best['type']:>5s} {best['sl']:5.1f} {best['p2']:5.2f} {best['p3']:5.2f} {best['pf']:6.2f} {best['wr']:4.0f}% {best['n']:5d} {best['avg']:+7.3f} {sp:>5s}{marker}")
        best_configs[sn] = best

# Rebuild with best configs for combo
print(f"\n{'='*100}")
print(f"CONSTRUCTION COMBO EQUILIBRE V2 (logique corrigee)")
print(f"{'='*100}")

valid = [sn for sn in best_configs if best_configs[sn]['pf'] >= 1.1 and best_configs[sn]['split'] and best_configs[sn]['wr'] >= 40]
print(f"\n  {len(valid)} strats valides (PF>=1.1 + split + WR>=40%)")

# Re-simulate with best configs to get per-trade data
trade_data = {}
for sn in valid:
    cfg = best_configs[sn]
    trades = []
    is_open = sn in OPEN_STRATS
    for sig in S[sn]:
        ci = sig['ci']; d = sig['dir']; entry = sig['entry']; atr = sig['atr']
        b, ex = sim_exit_custom(c, ci, entry, d, atr, cfg['type'], cfg['sl'], cfg['p2'], cfg['p3'], check_entry_candle=is_open)
        pnl = ((ex-entry) if d=='long' else (entry-ex)) - get_sp(sig['date'])
        mo = str(sig['date'].year)+"-"+str(sig['date'].month).zfill(2)
        di = 1 if d=='long' else -1
        trades.append((ci, ci+b, di, pnl, cfg['sl'], atr, mo, sn))
    trade_data[sn] = trades

# Correlation
daily_pnl = {}
for sn in valid:
    dp = {}
    for sig, tr in zip(S[sn], trade_data[sn]):
        d = str(sig['date']); dp[d] = dp.get(d,0) + tr[3]
    daily_pnl[sn] = dp
all_dates = sorted(set(d for dp in daily_pnl.values() for d in dp.keys()))
df_c = pd.DataFrame(index=all_dates)
for sn in valid: df_c[sn] = pd.Series(daily_pnl[sn])
df_c = df_c.fillna(0)
corr = df_c.corr()

def eval_combo(strats, capital=1000.0, risk=0.01):
    combined = []
    for sn in strats:
        if sn in trade_data: combined.extend(trade_data[sn])
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
    has_l = False; has_s = False
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in accepted:
        pnl = pnl_oz * (cap * risk) / (sl_atr * atr)
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        months[mo] = months.get(mo, 0.0) + pnl
        if di == 1: has_l = True
        else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    pm = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'ret': ret, 'mdd': mdd, 'cal': ret/abs(mdd) if mdd<0 else 0,
            'pf': gp/(gl+0.01), 'wr': wins/n*100, 'both': has_s and has_l, 'pm': pm, 'tm': len(months)}

# Greedy combo
ranked = sorted(valid, key=lambda sn: best_configs[sn]['score'], reverse=True)
combo = [ranked[0]]; remaining = set(ranked[1:])

r = eval_combo(combo)
if r: print(f"\n  Start: {combo[0]} n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}%")

for step in range(25):
    best_add = None; best_score = -1e9
    for sn in remaining:
        if sn not in corr.columns: continue
        mc = max([corr.loc[sn,s] for s in combo if s in corr.columns] or [0])
        if mc > 0.4: continue
        test = combo + [sn]; r = eval_combo(test)
        if r and r['both']:
            ac = np.mean([corr.loc[sn,s] for s in combo if s in corr.columns])
            score = r['cal'] * (r['wr']/50) * (1 - ac)
            if score > best_score: best_score = score; best_add = sn; best_r = r
    if best_add is None: break
    combo.append(best_add); remaining.remove(best_add); r = best_r
    cfg = best_configs[best_add]
    print(f"  +{best_add:22s} ({len(combo):2d}) n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']} [{cfg['type']} SL={cfg['sl']} {cfg['p2']:.2f}/{cfg['p3']:.2f}]")

# Final comparison
print(f"\n{'='*100}")
print(f"COMPARATIF (1% risk)")
print(f"{'='*100}")
print(f"\n  {'Combo':>25s} {'n':>6s} {'PF':>6s} {'WR':>5s} {'DD':>8s} {'Rend':>10s} {'M+':>5s}")
print(f"  {'-'*68}")
for sz in [5, 8, 10, min(len(combo), 15)]:
    if sz > len(combo): continue
    r = eval_combo(combo[:sz])
    if r:
        print(f"  {'EQUILIBRE V2 '+str(sz):>25s} {r['n']:6d} {r['pf']:6.2f} {r['wr']:4.0f}% {r['mdd']:+7.1f}% {r['ret']:+9.0f}% {r['pm']}/{r['tm']}")

print(f"\n  Composition:")
for sn in combo[:15]:
    cfg = best_configs[sn]
    p2l = 'TP' if cfg['type']=='TPSL' else 'ACT'
    p3l = '' if cfg['type']=='TPSL' else f" TR={cfg['p3']:.2f}"
    print(f"    {sn:22s} {cfg['type']:>5s} SL={cfg['sl']:.1f} {p2l}={cfg['p2']:.2f}{p3l} PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")
print()
