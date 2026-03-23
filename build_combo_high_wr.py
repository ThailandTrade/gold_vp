"""Build combo High WR (>60%) avec diversification."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd

# Relancer collecte
exec(open('find_combo_greedy.py').read().split('# GREEDY')[0])

from strats import sim_exit_custom
OPEN_SET = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

HW = {
    'LON_KZ':(3.0,0.30),'LON_GAP':(3.0,0.30),'ALL_FIB_618':(3.0,0.30),'TOK_BIG':(3.0,0.30),
    'ALL_CONSEC_REV':(3.0,0.30),'LON_BIGGAP':(3.0,0.30),'PO3_SWEEP':(3.0,0.75),
    'TOK_2BAR':(3.0,0.50),'TOK_WILLR':(3.0,0.50),'ALL_MACD_ADX':(3.0,0.50),
    'LON_TOKEND':(3.0,1.00),'ALL_PSAR_EMA':(3.0,1.00),'ALL_MACD_RSI':(3.0,1.00),
    'ALL_FVG_BULL':(3.0,1.00),'ALL_MACD_MED_SIG':(3.0,1.00),'ALL_MACD_STD_SIG':(3.0,0.75),
    'ALL_MOM_10':(3.0,0.75),'ALL_PIVOT_BRK':(3.0,1.00),'ALL_AO_SAUCER':(3.0,1.00),
}

def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

# Re-simulate with HW configs
S_HW = {}
for sn, (sl, tp) in HW.items():
    if sn not in S: continue
    trades = []
    is_open = sn in OPEN_SET
    for t in S[sn]:
        ci = t.get('ei')
        if ci is None or ci >= len(c)-5: continue
        d = t['dir']; atr = t.get('atr', 1.0)
        if atr == 0: continue
        entry = c.iloc[ci]['close']; spread = get_sp(t['date'])
        stop = entry - sl*atr if d=='long' else entry + sl*atr
        target = entry + tp*atr if d=='long' else entry - tp*atr
        exited = False; start = 0 if is_open else 1
        for j in range(start, min(100, len(c)-ci)):
            b = c.iloc[ci+j]
            if j==0 and is_open:
                if d=='long' and b['low']<=stop: trades.append({**t,'pnl_oz':stop-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                if d=='short' and b['high']>=stop: trades.append({**t,'pnl_oz':entry-stop-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                continue
            if d=='long':
                if b['low']<=stop: trades.append({**t,'pnl_oz':stop-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                if b['close']>=target: trades.append({**t,'pnl_oz':b['close']-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
            else:
                if b['high']>=stop: trades.append({**t,'pnl_oz':entry-stop-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                if b['close']<=target: trades.append({**t,'pnl_oz':entry-b['close']-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
        if not exited:
            nb = min(100, len(c)-ci-1)
            if nb > 0:
                ex = c.iloc[ci+nb]['close']
                pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                trades.append({**t,'pnl_oz':pnl,'sl_atr':sl,'xi':ci+nb})
    S_HW[sn] = trades

# Filter valid
valid = []
for sn in sorted(S_HW.keys()):
    t = S_HW[sn]
    if len(t) < 20: continue
    pnls = [x['pnl_oz'] for x in t]; n = len(pnls); wins = sum(1 for p in pnls if p>0)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    pf = gp/gl; wr = wins/n*100
    mid = n//2; split = np.mean(pnls[:mid])>0 and np.mean(pnls[mid:])>0
    if pf >= 1.1 and split and wr >= 60:
        valid.append(sn)
        sl, tp = HW[sn]
        print(f"  {sn:22s} WR={wr:.0f}% PF={pf:.2f} SL={sl} TP={tp}")

print(f"\n  {len(valid)} strats valides")

# Correlation
daily_pnl = {}
for sn in valid:
    dp = {}
    for t in S_HW[sn]:
        d = str(t['date']); dp[d] = dp.get(d,0) + t['pnl_oz']
    daily_pnl[sn] = dp
all_dates = sorted(set(d for dp in daily_pnl.values() for d in dp.keys()))
df_c = pd.DataFrame(index=all_dates)
for sn in valid: df_c[sn] = pd.Series(daily_pnl[sn])
df_c = df_c.fillna(0)
corr = df_c.corr()

# Build arrays
strat_arrays = {}
for sn in valid:
    rows = []
    for t in S_HW[sn]:
        di = 1 if t['dir']=='long' else -1
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t.get('xi',t['ei']+5), di, t['pnl_oz'], t['sl_atr'], t.get('atr',1), mo, sn))
    strat_arrays[sn] = rows

def eval_combo(strats, capital=1000.0, risk=0.01):
    combined = []
    for sn in strats:
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
            'pf': gp/(gl+0.01), 'wr': wins/n*100, 'capital': cap,
            'both': has_s and has_l, 'pm': pm, 'tm': len(months)}

# Greedy diversifie
ranked = sorted(valid, key=lambda sn: sum(p for p in [t['pnl_oz'] for t in S_HW[sn]] if p>0)/(abs(sum(p for p in [t['pnl_oz'] for t in S_HW[sn]] if p<0))+0.001), reverse=True)
combo = [ranked[0]]; remaining = set(ranked[1:])

print(f"\n{'='*100}")
print(f"GREEDY HIGH WR DIVERSIFIE")
print(f"{'='*100}")
r = eval_combo(combo)
if r: print(f"\n  Start: {combo[0]} n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}%")

for step in range(20):
    best_add = None; best_score = -1e9
    for sn in remaining:
        mc = max([corr.loc[sn,s] for s in combo if sn in corr.columns and s in corr.columns] or [0])
        if mc > 0.4: continue
        test = combo + [sn]; r = eval_combo(test)
        if r and r['both']:
            ac = np.mean([corr.loc[sn,s] for s in combo if sn in corr.columns and s in corr.columns])
            score = r['cal'] * (1 - ac)
            if score > best_score: best_score = score; best_add = sn; best_r = r
    if best_add is None: break
    combo.append(best_add); remaining.remove(best_add); r = best_r
    print(f"  +{best_add:22s} ({len(combo):2d}) n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")

print(f"\n{'='*100}")
print(f"COMPARATIF FINAL ($100k, 0.1% risk)")
print(f"{'='*100}")
import math
combos_compare = {
    'GREEDY BRUT 10': {'n':2333,'pf':1.77,'wr':27,'mdd':-57.4,'ret':2381361,'pm':11,'tm':13},
    'GREEDY DIVERS 10': {'n':2163,'pf':1.64,'wr':32,'mdd':-50.6,'ret':728430,'pm':11,'tm':13},
}
for sz in [5, 8, 10, min(len(combo), 15)]:
    if sz > len(combo): continue
    r = eval_combo(combo[:sz])
    if r: combos_compare[f'HIGH WR {sz}'] = r

print(f"\n  {'Combo':>20s} {'Trades':>7s} {'PF':>5s} {'WR':>5s} {'DD 1%':>7s} {'DD 0.1%':>8s} {'Rend 0.1%':>10s} {'M+':>5s}")
print(f"  {'-'*85}")
for name, r in combos_compare.items():
    if isinstance(r, dict):
        dd01 = r['mdd'] if 'mdd' in r else r.get('dd',0)
        dd01_pct = dd01 / 10
        ret01 = (math.pow(1 + r['ret']/100, 0.1) - 1) * 100 if r['ret'] > 0 else r['ret']/10
        wr = r.get('wr', 0)
        print(f"  {name:>20s} {r['n']:7d} {r['pf']:5.2f} {wr:4.0f}% {dd01:+6.1f}% {dd01_pct:+7.1f}% {ret01:+9.1f}% {r['pm']}/{r['tm']}")

print()
