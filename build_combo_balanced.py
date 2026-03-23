"""Build combo EQUILIBRE: WR 45-65%, PF>1.3, DD bas."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd

# Relancer collecte
exec(open('find_combo_greedy.py').read().split('# GREEDY')[0])

from strats import sim_exit_custom
OPEN_SET = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

# Configs intermediaires: SL modere + TP modere
SL_VALS = [1.5, 2.0, 2.5, 3.0]
TP_VALS = [0.5, 0.75, 1.0, 1.5]
# Also test trailing with tighter params
TRAIL_SL = [1.5, 2.0, 2.5]
TRAIL_ACT = [0.3, 0.5, 0.75]
TRAIL_TR = [0.5, 0.75, 1.0]

def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

print("="*100)
print("RECHERCHE CONFIGS EQUILIBREES (WR 40-70%, PF>1.2)")
print("="*100)

best_configs = {}

for sn in sorted(S.keys()):
    trades = S[sn]
    if len(trades) < 20: continue
    is_open = sn in OPEN_SET
    best = None

    # TPSL configs
    for sl in SL_VALS:
        for tp in TP_VALS:
            if tp >= sl: continue  # TP must be < SL
            pnls = []; wins = 0
            for t in trades:
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
                        if d=='long' and b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                        if d=='short' and b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                        continue
                    if d=='long':
                        if b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                        if b['close']>=target: pnls.append(b['close']-entry-spread); wins+=1; exited=True; break
                    else:
                        if b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                        if b['close']<=target: pnls.append(entry-b['close']-spread); wins+=1; exited=True; break
                if not exited:
                    nb = min(100, len(c)-ci-1)
                    if nb > 0:
                        ex = c.iloc[ci+nb]['close']
                        pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                        pnls.append(pnl)
                        if pnl > 0: wins += 1

            if len(pnls) < 20: continue
            wr = wins/len(pnls)*100
            gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
            pf = gp/gl
            mid = len(pnls)//2; split = np.mean(pnls[:mid])>0 and np.mean(pnls[mid:])>0
            if pf >= 1.2 and split and wr >= 40:
                # Score equilibre: on veut WR eleve ET PF eleve
                # Penalise les extremes (WR<45 ou WR>75)
                wr_bonus = min(wr, 70) / 100  # plafonne a 70%
                score = pf * wr_bonus
                if best is None or score > best['score']:
                    best = {'type':'TPSL','sl':sl,'tp':tp,'trail':0,'pf':pf,'wr':wr,
                            'n':len(pnls),'split':split,'score':score,'pnls':pnls}

    # TRAIL configs
    for sl in TRAIL_SL:
        for act in TRAIL_ACT:
            for trail in TRAIL_TR:
                if trail > sl: continue
                pnls = []; wins = 0
                for t in trades:
                    ci = t.get('ei')
                    if ci is None or ci >= len(c)-5: continue
                    d = t['dir']; atr = t.get('atr', 1.0)
                    if atr == 0: continue
                    entry = c.iloc[ci]['close']; spread = get_sp(t['date'])
                    best_p = entry; stop = entry-sl*atr if d=='long' else entry+sl*atr; ta = False
                    exited = False; start = 0 if is_open else 1
                    for j in range(start, min(100, len(c)-ci)):
                        b = c.iloc[ci+j]
                        if j==0 and is_open:
                            if d=='long' and b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                            if d=='short' and b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                            continue
                        if d=='long':
                            if b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                            if b['close']>best_p: best_p=b['close']
                            if not ta and (best_p-entry)>=act*atr: ta=True
                            if ta: stop=max(stop,best_p-trail*atr)
                            if b['close']<stop:
                                pnl = b['close']-entry-spread; pnls.append(pnl)
                                if pnl>0: wins+=1
                                exited=True; break
                        else:
                            if b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                            if b['close']<best_p: best_p=b['close']
                            if not ta and (entry-best_p)>=act*atr: ta=True
                            if ta: stop=min(stop,best_p+trail*atr)
                            if b['close']>stop:
                                pnl = entry-b['close']-spread; pnls.append(pnl)
                                if pnl>0: wins+=1
                                exited=True; break
                    if not exited:
                        nb = min(100, len(c)-ci-1)
                        if nb > 0:
                            ex = c.iloc[ci+nb]['close']
                            pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                            pnls.append(pnl)
                            if pnl > 0: wins += 1

                if len(pnls) < 20: continue
                wr = wins/len(pnls)*100
                gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
                pf = gp/gl
                mid = len(pnls)//2; split = np.mean(pnls[:mid])>0 and np.mean(pnls[mid:])>0
                if pf >= 1.2 and split and wr >= 40:
                    wr_bonus = min(wr, 70) / 100
                    score = pf * wr_bonus
                    if best is None or score > best['score']:
                        best = {'type':'TRAIL','sl':sl,'tp':act,'trail':trail,'pf':pf,'wr':wr,
                                'n':len(pnls),'split':split,'score':score,'pnls':pnls}

    if best:
        best_configs[sn] = best

# Print results sorted by score
print(f"\n{'Strat':>22s} {'Type':>5s} {'SL':>5s} {'P2':>5s} {'P3':>5s} {'PF':>6s} {'WR':>5s} {'n':>5s} {'Score':>6s}")
print("-"*80)
valid = []
for sn in sorted(best_configs.keys(), key=lambda x: -best_configs[x]['score']):
    cfg = best_configs[sn]
    p2 = cfg['tp']; p3 = cfg['trail']
    marker = ' <--' if cfg['wr'] >= 50 and cfg['pf'] >= 1.3 else ''
    print(f"{sn:>22s} {cfg['type']:>5s} {cfg['sl']:5.1f} {p2:5.2f} {p3:5.2f} {cfg['pf']:6.2f} {cfg['wr']:4.0f}% {cfg['n']:5d} {cfg['score']:6.2f}{marker}")
    if cfg['pf'] >= 1.2 and cfg['split'] and cfg['wr'] >= 45:
        valid.append(sn)

print(f"\n  {len(valid)} strats valides (WR>=45% + PF>=1.2 + split OK)")

# Correlation
daily_pnl = {}
for sn in valid:
    dp = {}
    cfg = best_configs[sn]
    # Resim to get per-trade data with date
    for t in S[sn]:
        ci = t.get('ei')
        if ci is None or ci >= len(c)-5: continue
        d_str = str(t['date'])
        # Use pnls from best_configs already computed - approximate daily via trade dates
        # We need actual trade-level pnls with dates, let's resim
    # Actually use the stored pnls - but we need dates. Let's rebuild.

# Rebuild with dates for correlation
BAL_HW = {}
for sn in valid:
    cfg = best_configs[sn]
    trades_out = []
    is_open = sn in OPEN_SET
    sl = cfg['sl']

    for t in S[sn]:
        ci = t.get('ei')
        if ci is None or ci >= len(c)-5: continue
        d = t['dir']; atr = t.get('atr', 1.0)
        if atr == 0: continue
        entry = c.iloc[ci]['close']; spread = get_sp(t['date'])

        if cfg['type'] == 'TPSL':
            tp = cfg['tp']
            stop = entry - sl*atr if d=='long' else entry + sl*atr
            target = entry + tp*atr if d=='long' else entry - tp*atr
            exited = False; start = 0 if is_open else 1
            for j in range(start, min(100, len(c)-ci)):
                b = c.iloc[ci+j]
                if j==0 and is_open:
                    if d=='long' and b['low']<=stop: trades_out.append({**t,'pnl_oz':stop-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    if d=='short' and b['high']>=stop: trades_out.append({**t,'pnl_oz':entry-stop-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    continue
                if d=='long':
                    if b['low']<=stop: trades_out.append({**t,'pnl_oz':stop-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    if b['close']>=target: trades_out.append({**t,'pnl_oz':b['close']-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                else:
                    if b['high']>=stop: trades_out.append({**t,'pnl_oz':entry-stop-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    if b['close']<=target: trades_out.append({**t,'pnl_oz':entry-b['close']-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
            if not exited:
                nb = min(100, len(c)-ci-1)
                if nb > 0:
                    ex = c.iloc[ci+nb]['close']
                    pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                    trades_out.append({**t,'pnl_oz':pnl,'sl_atr':sl,'xi':ci+nb})
        else:  # TRAIL
            act = cfg['tp']; trail = cfg['trail']
            best_p = entry; stop = entry-sl*atr if d=='long' else entry+sl*atr; ta = False
            exited = False; start = 0 if is_open else 1
            for j in range(start, min(100, len(c)-ci)):
                b = c.iloc[ci+j]
                if j==0 and is_open:
                    if d=='long' and b['low']<=stop: trades_out.append({**t,'pnl_oz':stop-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    if d=='short' and b['high']>=stop: trades_out.append({**t,'pnl_oz':entry-stop-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    continue
                if d=='long':
                    if b['low']<=stop: trades_out.append({**t,'pnl_oz':stop-entry-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    if b['close']>best_p: best_p=b['close']
                    if not ta and (best_p-entry)>=act*atr: ta=True
                    if ta: stop=max(stop,best_p-trail*atr)
                    if b['close']<stop:
                        pnl = b['close']-entry-spread
                        trades_out.append({**t,'pnl_oz':pnl,'sl_atr':sl,'xi':ci+j}); exited=True; break
                else:
                    if b['high']>=stop: trades_out.append({**t,'pnl_oz':entry-stop-spread,'sl_atr':sl,'xi':ci+j}); exited=True; break
                    if b['close']<best_p: best_p=b['close']
                    if not ta and (entry-best_p)>=act*atr: ta=True
                    if ta: stop=min(stop,best_p+trail*atr)
                    if b['close']>stop:
                        pnl = entry-b['close']-spread
                        trades_out.append({**t,'pnl_oz':pnl,'sl_atr':sl,'xi':ci+j}); exited=True; break
            if not exited:
                nb = min(100, len(c)-ci-1)
                if nb > 0:
                    ex = c.iloc[ci+nb]['close']
                    pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                    trades_out.append({**t,'pnl_oz':pnl,'sl_atr':sl,'xi':ci+nb})

    BAL_HW[sn] = trades_out

# Correlation matrix
daily_pnl = {}
for sn in valid:
    dp = {}
    for t in BAL_HW[sn]:
        d = str(t['date']); dp[d] = dp.get(d,0) + t['pnl_oz']
    daily_pnl[sn] = dp
all_dates = sorted(set(d for dp in daily_pnl.values() for d in dp.keys()))
df_c = pd.DataFrame(index=all_dates)
for sn in valid: df_c[sn] = pd.Series(daily_pnl[sn])
df_c = df_c.fillna(0)
corr = df_c.corr()

# Build arrays for combo eval
strat_arrays = {}
for sn in valid:
    rows = []
    for t in BAL_HW[sn]:
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
    # Event-based capital tracking (size at entry, PnL at exit)
    events = []
    for idx, (ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn) in enumerate(accepted):
        events.append((ei, 1, idx))   # 1 = entry
        events.append((xi, 0, idx))   # 0 = exit (sort before entry at same bar)
    events.sort()
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; entry_caps = {}
    for bar, evt, idx in events:
        if evt == 1:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = accepted[idx]
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
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

# Greedy diversifie - optimize for balanced score: Calmar * WR
ranked = sorted(valid, key=lambda sn: best_configs[sn]['score'], reverse=True)
combo = [ranked[0]]; remaining = set(ranked[1:])

print(f"\n{'='*100}")
print(f"GREEDY EQUILIBRE (WR 45-65%, PF>1.2, diversifie)")
print(f"{'='*100}")
r = eval_combo(combo)
if r: print(f"\n  Start: {combo[0]} n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}%")

for step in range(25):
    best_add = None; best_score = -1e9
    for sn in remaining:
        mc = max([corr.loc[sn,s] for s in combo if sn in corr.columns and s in corr.columns] or [0])
        if mc > 0.4: continue
        test = combo + [sn]; r = eval_combo(test)
        if r and r['both']:
            ac = np.mean([corr.loc[sn,s] for s in combo if sn in corr.columns and s in corr.columns])
            # Balanced score: Calmar weighted by WR and low correlation
            score = r['cal'] * (r['wr']/50) * (1 - ac)
            if score > best_score: best_score = score; best_add = sn; best_r = r
    if best_add is None: break
    combo.append(best_add); remaining.remove(best_add); r = best_r
    cfg = best_configs[best_add]
    print(f"  +{best_add:22s} ({len(combo):2d}) n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']} [{cfg['type']} SL={cfg['sl']} {cfg['tp']:.2f}/{cfg['trail']:.2f}]")

# Final comparison
print(f"\n{'='*100}")
print(f"COMPARATIF FINAL ($100k, 1% risk)")
print(f"{'='*100}")
import math
combos_compare = {
    'GREEDY BRUT 10': {'n':2333,'pf':1.77,'wr':27,'mdd':-57.4,'ret':2381361,'pm':11,'tm':13},
    'GREEDY DIVERS 10': {'n':2163,'pf':1.64,'wr':32,'mdd':-50.6,'ret':728430,'pm':11,'tm':13},
    'HIGH WR 10': {'n':1942,'pf':1.33,'wr':78,'mdd':-11.1,'ret':339,'pm':13,'tm':13},
}
for sz in [5, 8, 10, min(len(combo), 15)]:
    if sz > len(combo): continue
    r = eval_combo(combo[:sz])
    if r: combos_compare[f'EQUILIBRE {sz}'] = r

print(f"\n  {'Combo':>20s} {'Trades':>7s} {'PF':>5s} {'WR':>5s} {'DD 1%':>8s} {'Rend 1%':>12s} {'M+':>5s}")
print(f"  {'-'*70}")
for name, r in combos_compare.items():
    if isinstance(r, dict):
        dd = r['mdd'] if 'mdd' in r else r.get('dd',0)
        ret = r['ret'] if 'ret' in r else 0
        wr = r.get('wr', 0)
        print(f"  {name:>20s} {r['n']:7d} {r['pf']:5.2f} {wr:4.0f}% {dd:+7.1f}% {ret:+11.0f}% {r['pm']}/{r['tm']}")

# Detail strats du combo
print(f"\n  Composition EQUILIBRE {min(len(combo),15)}:")
for sn in combo[:15]:
    cfg = best_configs[sn]
    print(f"    {sn:22s} {cfg['type']:>5s} SL={cfg['sl']:.1f} {'TP' if cfg['type']=='TPSL' else 'ACT'}={cfg['tp']:.2f} {'TR='+str(cfg['trail']) if cfg['trail'] else ''} PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")

print()
