"""
Analyse combinatoire exhaustive des strategies.
Charge optim_data.pkl (genere par optimize_all.py) et evalue:
1. Correlations pairwise entre toutes les strats
2. Combos greedy avec PLUSIEURS criteres (Calmar, PF, min DD, Sharpe, diversifie)
3. Comparatif final de tous les meilleurs combos
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pickle, json
from itertools import combinations

# ── LOAD DATA ──
import argparse
import importlib
_parser = argparse.ArgumentParser(); _parser.add_argument('account', nargs='?', default='icm')
_parser.add_argument('--symbol', default='xauusd')
_args = _parser.parse_args()
import re
_sym = re.sub(r"[^a-z0-9]+", "_", _args.symbol.lower()).strip("_")
_sym_dir = f'/{_sym}' if _sym != 'xauusd' else ''
_pkl = f'data/{_args.account}{_sym_dir}/optim_data.pkl'
print(f"Loading {_pkl}...", flush=True)
with open(_pkl, 'rb') as f:
    data = pickle.load(f)
strat_arrays = data['strat_arrays']
best_configs = data['best_configs']
OPEN_STRATS = set(data['OPEN_STRATS'])
MIN_MARGIN = 8.0  # marge WR minimum (WR - WR_breakeven)

# Filtre: pas d'open strats + marge WR > 10% en solo
_all_candidates = sorted(sn for sn in strat_arrays.keys() if sn not in OPEN_STRATS)
all_strats = []
_skipped_margin = []
for _sn in _all_candidates:
    _trades = strat_arrays[_sn]
    _pnls = [t[3] for t in _trades]
    _wins = [p for p in _pnls if p > 0]
    _losses = [p for p in _pnls if p <= 0]
    if not _wins or not _losses: _skipped_margin.append(_sn); continue
    _wr = len(_wins) / len(_pnls) * 100
    _avg_w = sum(_wins) / len(_wins)
    _avg_l = abs(sum(_losses) / len(_losses))
    _rr = _avg_w / _avg_l if _avg_l > 0 else 0
    _wr_min = 1 / (1 + _rr) * 100 if _rr > 0 else 100
    _marge = _wr - _wr_min
    if _marge >= MIN_MARGIN:
        all_strats.append(_sn)
    else:
        _skipped_margin.append(_sn)

# Load capital & risk from config
_cfg = importlib.import_module(f'config_{_args.account}')
_sym_upper = _sym.upper()
if hasattr(_cfg, 'INSTRUMENTS') and _sym_upper in _cfg.INSTRUMENTS:
    RISK = _cfg.INSTRUMENTS[_sym_upper]['risk_pct']
elif hasattr(_cfg, 'ALL_INSTRUMENTS') and _sym_upper in _cfg.ALL_INSTRUMENTS:
    RISK = _cfg.ALL_INSTRUMENTS[_sym_upper]['risk_pct']
else:
    RISK = getattr(_cfg, 'RISK_PCT', 0.0005)
CAPITAL = 100000.0
print(f"  {len(all_strats)} strats viable (marge>{MIN_MARGIN}%), {len(_skipped_margin)} filtrees. Capital=${CAPITAL:,.0f} Risk={RISK*100:.2f}%")
if _skipped_margin:
    print(f"  Filtrees: {', '.join(_skipped_margin)}")

# ── EVAL COMBO (event-based, identique a optimize_all.py) ──
def eval_combo(strats, capital=CAPITAL, risk=RISK):
    combined = []
    for sn in strats:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    if len(combined) < 20: return None
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    if n < 20: return None
    events = []
    for idx, (ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn) in enumerate(accepted):
        events.append((ei, 0, idx))
        events.append((xi, 1, idx))
    events.sort()
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; entry_caps = {}; pnl_by_entry = []
    daily_pnl = {}
    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = accepted[idx]
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl; pnl_by_entry.append((ei, pnl))
            if cap > peak: peak = cap
            dd = (cap - peak) / peak
            if dd < max_dd: max_dd = dd
            if pnl > 0: gp += pnl; wins += 1
            else: gl += abs(pnl)
            months[mo] = months.get(mo, 0.0) + pnl
            daily_pnl[ei // 288] = daily_pnl.get(ei // 288, 0) + pnl
            if di == 1: has_l = True
            else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    pnl_by_entry.sort(); pnls = [p for _, p in pnl_by_entry]
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    pm = sum(1 for v in months.values() if v > 0)
    # Sharpe approx (daily returns)
    daily_rets = list(daily_pnl.values())
    sharpe = np.mean(daily_rets) / (np.std(daily_rets) + 1e-10) * np.sqrt(252) if daily_rets else 0
    return {'n': n, 'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
            'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
            'split': p1 > 0 and p2 > 0, 'both': has_s and has_l, 'pm': pm, 'tm': len(months),
            'sharpe': sharpe}

# ══════════════════════════════════════════════════════════════════════════
# 1. CORRELATIONS PAIRWISE
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*130}")
print("1. CORRELATIONS PAIRWISE")
print(f"{'='*130}")

# Build daily PnL series per strat
def get_daily_pnl(sn):
    """Get daily PnL series for a strat (day_index -> pnl_oz)."""
    dpnl = {}
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in strat_arrays[sn]:
        day = ei // 288
        dpnl[day] = dpnl.get(day, 0) + pnl_oz
    return dpnl

daily_pnls = {sn: get_daily_pnl(sn) for sn in all_strats}
all_days = sorted(set(d for dpnl in daily_pnls.values() for d in dpnl))

# Build matrix
pnl_matrix = np.zeros((len(all_strats), len(all_days)))
for i, sn in enumerate(all_strats):
    for j, day in enumerate(all_days):
        pnl_matrix[i, j] = daily_pnls[sn].get(day, 0)

# Correlation matrix
corr = np.corrcoef(pnl_matrix)

# Print high correlations (>0.3)
print("\n  Paires fortement correlees (>0.3):")
high_corr = []
for i in range(len(all_strats)):
    for j in range(i+1, len(all_strats)):
        if abs(corr[i, j]) > 0.3:
            high_corr.append((all_strats[i], all_strats[j], corr[i, j]))
high_corr.sort(key=lambda x: -abs(x[2]))
for s1, s2, c in high_corr[:30]:
    print(f"    {s1:22s} x {s2:22s}  corr={c:+.3f}")
print(f"  Total paires >0.3: {len(high_corr)}")

# Average correlation per strat
avg_corr = {}
for i, sn in enumerate(all_strats):
    others = [abs(corr[i, j]) for j in range(len(all_strats)) if j != i]
    avg_corr[sn] = np.mean(others)

print("\n  Strats les plus decorrelees (avg |corr| faible):")
for sn, ac in sorted(avg_corr.items(), key=lambda x: x[1])[:15]:
    cfg = best_configs[sn]
    print(f"    {sn:22s} avg|corr|={ac:.3f}  PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")

print("\n  Strats les plus correlees (avg |corr| forte):")
for sn, ac in sorted(avg_corr.items(), key=lambda x: -x[1])[:10]:
    cfg = best_configs[sn]
    print(f"    {sn:22s} avg|corr|={ac:.3f}  PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")

# ══════════════════════════════════════════════════════════════════════════
# 2. EVALUATE ALL PAIRS
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*130}")
print("2. MEILLEURES PAIRES")
print(f"{'='*130}")

pair_results = []
for s1, s2 in combinations(all_strats, 2):
    r = eval_combo([s1, s2])
    if r and r['both']:
        c12 = corr[all_strats.index(s1), all_strats.index(s2)]
        pair_results.append((s1, s2, r, c12))

# Top pairs by PF
print("\n  Top 15 paires par PF:")
for s1, s2, r, c12 in sorted(pair_results, key=lambda x: -x[2]['pf'])[:15]:
    print(f"    {s1:20s} + {s2:20s}  PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% n={r['n']:4d} corr={c12:+.3f}")

# Top pairs by Calmar
print("\n  Top 15 paires par Calmar:")
for s1, s2, r, c12 in sorted(pair_results, key=lambda x: -x[2]['cal'])[:15]:
    print(f"    {s1:20s} + {s2:20s}  Cal={r['cal']:.1f} PF={r['pf']:.2f} DD={r['mdd']:+.1f}% n={r['n']:4d} corr={c12:+.3f}")

# Top pairs by Sharpe
print("\n  Top 15 paires par Sharpe:")
for s1, s2, r, c12 in sorted(pair_results, key=lambda x: -x[2]['sharpe'])[:15]:
    print(f"    {s1:20s} + {s2:20s}  Sharpe={r['sharpe']:.2f} PF={r['pf']:.2f} DD={r['mdd']:+.1f}% corr={c12:+.3f}")

# Top pairs low correlation + profitable
print("\n  Top 15 paires decorrelees + rentables (PF>1.3, |corr|<0.1):")
decor_pairs = [(s1, s2, r, c12) for s1, s2, r, c12 in pair_results if r['pf'] > 1.3 and abs(c12) < 0.1]
for s1, s2, r, c12 in sorted(decor_pairs, key=lambda x: -x[2]['pf'])[:15]:
    print(f"    {s1:20s} + {s2:20s}  PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% corr={c12:+.3f}")

# ══════════════════════════════════════════════════════════════════════════
# 3. GREEDY BUILDERS — MULTIPLE CRITERIA
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*130}")
print("3. GREEDY BUILDERS — 5 CRITERES")
print(f"{'='*130}")

def greedy_build(criterion, label, max_size=20, require_both=True):
    """Build greedy combo optimizing for criterion.
    criterion(combo, r) -> score to maximize
    """
    ranked = sorted(all_strats, key=lambda sn: best_configs[sn]['pf'], reverse=True)
    combo = [ranked[0]]; remaining = set(ranked[1:])
    checkpoints = {}

    for step in range(min(max_size, len(remaining))):
        best_add = None; best_score = -1e9
        for sn in remaining:
            test = combo + [sn]
            r = eval_combo(test)
            if r and r['split']:
                if require_both and not r['both']: continue
                score = criterion(test, r)
                if score > best_score:
                    best_score = score; best_add = sn; best_r = r
        if best_add is None: break
        combo.append(best_add); remaining.remove(best_add)
        checkpoints[len(combo)] = {'combo': list(combo), 'r': dict(best_r)}

    return checkpoints

def greedy_build_diverse(max_size=20):
    """Greedy diversifie: a chaque step, choisir la strat qui minimise la correlation moyenne avec le combo."""
    ranked = sorted(all_strats, key=lambda sn: best_configs[sn]['pf'], reverse=True)
    combo = [ranked[0]]; remaining = set(ranked[1:])
    checkpoints = {}

    for step in range(min(max_size, len(remaining))):
        best_add = None; best_score = -1e9
        for sn in remaining:
            test = combo + [sn]
            r = eval_combo(test)
            if r and r['split'] and r['both'] and r['pf'] > 1.1:
                # Score = PF * decorrelation bonus
                idx_sn = all_strats.index(sn)
                avg_c = np.mean([abs(corr[idx_sn, all_strats.index(s)]) for s in combo])
                score = r['pf'] * (1 - avg_c)  # higher PF + lower correlation = better
                if score > best_score:
                    best_score = score; best_add = sn; best_r = r
        if best_add is None: break
        combo.append(best_add); remaining.remove(best_add)
        checkpoints[len(combo)] = {'combo': list(combo), 'r': dict(best_r)}

    return checkpoints

criteria = {
    'Calmar':   (lambda c, r: r['cal'], "Calmar (return/|DD|)"),
    'PF':       (lambda c, r: r['pf'], "Profit Factor"),
    'MinDD':    (lambda c, r: -abs(r['mdd']), "Minimize Max DD"),
    'Sharpe':   (lambda c, r: r['sharpe'], "Sharpe Ratio"),
    'PF*WR':    (lambda c, r: r['pf'] * r['wr'] / 100, "PF * WR"),
}

all_results = {}
for name, (criterion, desc) in criteria.items():
    print(f"\n  ── {name}: {desc} ──")
    cp = greedy_build(criterion, name)
    all_results[name] = cp
    for sz in sorted(cp.keys()):
        r = cp[sz]['r']
        if sz <= 15 or sz % 5 == 0:
            print(f"    {sz:2d} strats  n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% "
                  f"Rend={r['ret']:+.0f}% Sharpe={r['sharpe']:.1f} M+={r['pm']}/{r['tm']}")

print(f"\n  ── Diversifie: PF * decorrelation ──")
cp = greedy_build_diverse()
all_results['Diverse'] = cp
for sz in sorted(cp.keys()):
    r = cp[sz]['r']
    if sz <= 15 or sz % 5 == 0:
        print(f"    {sz:2d} strats  n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% "
              f"Rend={r['ret']:+.0f}% Sharpe={r['sharpe']:.1f} M+={r['pm']}/{r['tm']}")

# ══════════════════════════════════════════════════════════════════════════
# 4. COMPARATIF FINAL — TOUS LES COMBOS A TAILLE 5, 8, 10, 12, 15
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*130}")
print("4. COMPARATIF FINAL")
print(f"{'='*130}")

for sz in [5, 8, 10, 12, 15]:
    print(f"\n  ── TAILLE {sz} ──")
    print(f"  {'Critere':>12s}  {'Trades':>7s}  {'PF':>5s}  {'WR':>5s}  {'DD':>8s}  {'Rend':>10s}  {'Sharpe':>7s}  {'M+':>5s}")
    print(f"  {'-'*12}  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*8}  {'-'*10}  {'-'*7}  {'-'*5}")
    for name in ['Calmar', 'PF', 'MinDD', 'Sharpe', 'PF*WR', 'Diverse']:
        cp = all_results.get(name, {})
        if sz in cp:
            r = cp[sz]['r']
            print(f"  {name:>12s}  {r['n']:7d}  {r['pf']:5.2f}  {r['wr']:4.0f}%  {r['mdd']:+7.1f}%  {r['ret']:+9.0f}%  {r['sharpe']:7.1f}  {r['pm']:2d}/{r['tm']}")
        else:
            # Find closest size
            available = sorted(cp.keys())
            closest = min(available, key=lambda x: abs(x - sz)) if available else None
            if closest:
                r = cp[closest]['r']
                print(f"  {name:>12s}  ({closest:2d}) {r['n']:5d}  {r['pf']:5.2f}  {r['wr']:4.0f}%  {r['mdd']:+7.1f}%  {r['ret']:+9.0f}%  {r['sharpe']:7.1f}  {r['pm']:2d}/{r['tm']}")

# ══════════════════════════════════════════════════════════════════════════
# 5. MEILLEUR COMBO PAR PROFIL DE RISQUE
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*130}")
print("5. MEILLEUR COMBO PAR PROFIL DE RISQUE")
print(f"{'='*130}")

# Collect all combos across all criteria and sizes
all_combos = []
for name, cp in all_results.items():
    for sz, data in cp.items():
        r = data['r']
        all_combos.append({
            'method': name, 'size': sz, 'combo': data['combo'], **r
        })

# Best for conservative (DD < -10%, 13/13 months)
print("\n  CONSERVATEUR (DD > -10%, 13/13 mois):")
conservative = [c for c in all_combos if c['mdd'] > -10 and c['pm'] == c['tm']]
if conservative:
    for c in sorted(conservative, key=lambda x: -x['pf'])[:5]:
        print(f"    [{c['method']:>8s} {c['size']:2d}]  PF={c['pf']:.2f} WR={c['wr']:.0f}% DD={c['mdd']:+.1f}% Rend={c['ret']:+.0f}% M+={c['pm']}/{c['tm']}")
        print(f"      Strats: {', '.join(c['combo'])}")
else:
    print("    Aucun combo DD > -10% avec 13/13 mois")

# Best for balanced (DD < -15%, PF > 1.4)
print("\n  EQUILIBRE (DD > -15%, PF > 1.4):")
balanced = [c for c in all_combos if c['mdd'] > -15 and c['pf'] > 1.4]
if balanced:
    for c in sorted(balanced, key=lambda x: -x['ret'])[:5]:
        print(f"    [{c['method']:>8s} {c['size']:2d}]  PF={c['pf']:.2f} WR={c['wr']:.0f}% DD={c['mdd']:+.1f}% Rend={c['ret']:+.0f}% M+={c['pm']}/{c['tm']}")
        print(f"      Strats: {', '.join(c['combo'])}")
else:
    print("    Aucun combo matching")

# Best for aggressive (PF > 1.3, maximize return)
print("\n  AGRESSIF (PF > 1.3, max rendement):")
aggressive = [c for c in all_combos if c['pf'] > 1.3]
if aggressive:
    for c in sorted(aggressive, key=lambda x: -x['ret'])[:5]:
        print(f"    [{c['method']:>8s} {c['size']:2d}]  PF={c['pf']:.2f} WR={c['wr']:.0f}% DD={c['mdd']:+.1f}% Rend={c['ret']:+.0f}% M+={c['pm']}/{c['tm']}")
        print(f"      Strats: {', '.join(c['combo'])}")

# Best Sharpe
print("\n  MEILLEUR SHARPE:")
for c in sorted(all_combos, key=lambda x: -x['sharpe'])[:5]:
    print(f"    [{c['method']:>8s} {c['size']:2d}]  Sharpe={c['sharpe']:.2f} PF={c['pf']:.2f} WR={c['wr']:.0f}% DD={c['mdd']:+.1f}% Rend={c['ret']:+.0f}%")
    print(f"      Strats: {', '.join(c['combo'])}")

# ══════════════════════════════════════════════════════════════════════════
# 5b. TOP 20 — SCORE COMPOSITE
# ══════════════════════════════════════════════════════════════════════════
import math
print(f"\n{'='*130}")
print("5b. TOP 20 — SCORE = PF x WR x Rend x M+/TM / (1+|DD|) x min(1, n/500)")
print(f"{'='*130}")

seen_top = set()
scored = []
for c in all_combos:
    key = tuple(sorted(c['combo']))
    if key in seen_top: continue
    seen_top.add(key)
    n = c['n']; pf = c['pf']; wr = c['wr']; ret = max(c['ret'], 0.1); dd = abs(c['mdd'])
    pm = c['pm']; tm = c['tm']
    trade_factor = min(1.0, n / 500.0)
    month_factor = pm / tm if tm > 0 else 0
    score = pf * (wr/100) * (ret/10) / (1 + dd) * month_factor * trade_factor
    c['score'] = score
    scored.append(c)

scored.sort(key=lambda x: -x['score'])
print(f"\n  {'#':>3s} {'Score':>6s} {'Nb':>3s} {'Trades':>7s} {'PF':>5s} {'WR':>4s} {'DD':>7s} {'Rend':>6s} {'M+':>5s} {'Combo':>6s} Strats")
print(f"  {'-'*120}")
for i, c in enumerate(scored[:20]):
    strats_str = ', '.join(c['combo'][:8])
    if len(c['combo']) > 8: strats_str += f' +{len(c["combo"])-8}'
    print(f"  {i+1:>3d} {c['score']:>6.2f} {len(c['combo']):>3d} {c['n']:>7d} {c['pf']:>5.2f} {c['wr']:>3.0f}% {c['mdd']:>+6.1f}% {c['ret']:>+5.0f}% {c['pm']}/{c['tm']:>2d} [{c['method']:>7s}] {strats_str}")

# ══════════════════════════════════════════════════════════════════════════
# 6. DETAIL DES MEILLEURES COMPOSITIONS
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*130}")
print("6. DETAIL DES MEILLEURES COMPOSITIONS")
print(f"{'='*130}")

# Identify unique top combos
seen = set()
top_combos = []
for c in sorted(all_combos, key=lambda x: (-x['pf'], x['mdd'])):
    key = tuple(sorted(c['combo']))
    if key not in seen and c['pf'] > 1.4 and c['pm'] >= 12 and len(c['combo']) >= 5:
        seen.add(key)
        top_combos.append(c)
    if len(top_combos) >= 10: break

for i, c in enumerate(top_combos):
    print(f"\n  #{i+1} [{c['method']} {c['size']}] PF={c['pf']:.2f} WR={c['wr']:.0f}% DD={c['mdd']:+.1f}% Rend={c['ret']:+.0f}% Sharpe={c['sharpe']:.1f} M+={c['pm']}/{c['tm']}")

    # Correlation matrix for this combo
    idxs = [all_strats.index(sn) for sn in c['combo']]
    sub_corr = corr[np.ix_(idxs, idxs)]
    avg_c = np.mean([abs(sub_corr[i, j]) for i in range(len(idxs)) for j in range(i+1, len(idxs))])
    max_c = max([abs(sub_corr[i, j]) for i in range(len(idxs)) for j in range(i+1, len(idxs))])
    print(f"  Correlation: avg={avg_c:.3f} max={max_c:.3f}")

    # Sessions
    sessions = {}
    for sn in c['combo']:
        if sn.startswith('TOK_'): s = 'Tokyo'
        elif sn.startswith('LON_'): s = 'London'
        elif sn.startswith('NY_'): s = 'New York'
        elif sn.startswith('PO3_'): s = 'London'
        else: s = 'All'
        sessions[s] = sessions.get(s, 0) + 1
    print(f"  Sessions: {dict(sessions)}")

    for sn in c['combo']:
        cfg = best_configs[sn]
        tp_str = f"TP={cfg['p2']:.2f}" if cfg['type'] == 'TPSL' else f"ACT={cfg['p2']:.2f} TR={cfg['p3']:.2f}"
        print(f"    {sn:22s} {cfg['type']:5s} SL={cfg['p1']:.1f} {tp_str:16s} PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")

# ══════════════════════════════════════════════════════════════════════════
# SAVE RESULTS
# ══════════════════════════════════════════════════════════════════════════
results_save = {}
for name, cp in all_results.items():
    results_save[name] = {}
    for sz, d in cp.items():
        results_save[name][sz] = {'combo': d['combo'],
            'n': d['r']['n'], 'pf': d['r']['pf'], 'wr': d['r']['wr'],
            'mdd': d['r']['mdd'], 'ret': d['r']['ret'],
            'sharpe': d['r']['sharpe'], 'pm': d['r']['pm'], 'tm': d['r']['tm']}
_json_file = f'data/{_args.account}{_sym_dir}/combo_results.json'
with open(_json_file, 'w') as f:
    json.dump(results_save, f, indent=2)
print(f"\nSaved {_json_file}")
print(f"{'='*130}")
