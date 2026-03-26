"""
Optimisation indices: strats_indices x tous les exits → meilleur combo.
Usage: python optimize_indices.py 5ers --symbol nas100
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats_indices import detect_all_idx, compute_indicators_idx
from strats import sim_exit_custom

# ── ARGS ──
parser = argparse.ArgumentParser()
parser.add_argument('account', nargs='?', default='icm')
parser.add_argument('--symbol', default='nas100')
args = parser.parse_args()
SYMBOL = args.symbol.lower()

# ── DATA ──
print(f"Loading data ({SYMBOL})...", flush=True)
conn = get_conn()
candles = load_candles_5m(conn, symbol=SYMBOL)
daily_atr, global_atr = compute_atr(conn, symbol=SYMBOL)
trading_days = get_trading_days(conn, symbol=SYMBOL)
tick_table = f"market_ticks_{SYMBOL}"
cur = conn.cursor()
try:
    cur.execute(f"""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM {tick_table} WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
    monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
except Exception:
    conn.rollback()
    monthly_spread = {}
    print(f"  WARNING: pas de ticks pour {SYMBOL}, spread=0")
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values())) if monthly_spread else 0

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(f"{day.year}-{str(day.month).zfill(2)}", avg_sp)

# ── PRECALCUL ──
print("Precalcul indicateurs...", flush=True)
c = candles.copy()
c = compute_indicators_idx(c)

# Pre-extract numpy arrays for fast exit simulation
hi = c['high'].values; lo = c['low'].values; cl = c['close'].values
N = len(c)

def sim_exit_np(pos, entry, d, atr, etype, p1, p2, p3, check_entry):
    sl_val = p1
    stop = entry + sl_val*atr if d == -1 else entry - sl_val*atr
    start = 0 if check_entry else 1
    max_bars = min(288, N - pos - 1)
    if max_bars <= 0: return 1, entry
    if etype == 0:  # TPSL
        target = entry + p2*atr if d == 1 else entry - p2*atr
        for j in range(start, max_bars):
            idx = pos + j
            if j == 0:
                if d == 1 and lo[idx] <= stop: return 0, stop
                if d == -1 and hi[idx] >= stop: return 0, stop
                continue
            if d == 1:
                if lo[idx] <= stop: return j, stop
                if hi[idx] >= target: return j, target
            else:
                if hi[idx] >= stop: return j, stop
                if lo[idx] <= target: return j, target
        return max_bars, cl[pos + max_bars]
    else:  # TRAIL
        best = entry; ta = False; act_val = p2; trail_val = p3
        for j in range(start, max_bars):
            idx = pos + j
            if j == 0:
                if d == 1 and lo[idx] <= stop: return 0, stop
                if d == -1 and hi[idx] >= stop: return 0, stop
                continue
            if d == 1:
                if lo[idx] <= stop: return j, stop
                if cl[idx] > best: best = cl[idx]
                if not ta and (best - entry) >= act_val * atr: ta = True
                if ta: stop = max(stop, best - trail_val * atr)
                if cl[idx] < stop: return j, cl[idx]
            else:
                if hi[idx] >= stop: return j, stop
                if cl[idx] < best: best = cl[idx]
                if not ta and (entry - best) >= act_val * atr: ta = True
                if ta: stop = min(stop, best + trail_val * atr)
                if cl[idx] > stop: return j, cl[idx]
        return 1, entry

# ── SIGNAL COLLECTION ──
print("Collecte signaux...", flush=True)
SIG = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None

for ci in range(200, len(c)):
    row = c.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
            if len(yc) > 0:
                prev_day_data = {'open':float(yc.iloc[0]['open']),'close':float(yc.iloc[-1]['close']),
                                 'high':float(yc['high'].max()),'low':float(yc['low'].min()),
                                 'range':float(yc['high'].max()-yc['low'].min())}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    sp = get_sp(today)
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    tv = c[(c['ts_dt']>=ds)&(c['ts_dt']<=ct)]

    def add_sig(sn, d, e):
        di = 1 if d == 'long' else -1
        SIG.setdefault(sn, []).append((ci, di, e, atr, today, sp))

    detect_all_idx(c, ci, row, ct, today, hour, atr, trig, tv, prev_day_data, add_sig)

print(f"Done. {len(SIG)} strats, {sum(len(v) for v in SIG.values())} signaux total.", flush=True)

# ── EXIT OPTIMIZATION GRID ──
print("\nOptimisation exits...", flush=True)
TPSL_GRID = [(sl, tp) for sl in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0] for tp in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]]
TRAIL_GRID = [(sl, act, trail) for sl in [0.5, 1.0, 1.5, 2.0, 3.0]
              for act in [0.3, 0.5, 0.75, 1.0] for trail in [0.3, 0.5, 0.75, 1.0]]
MIN_MARGIN = 5.0

best_configs = {}
for sn in sorted(SIG.keys()):
    sigs = SIG[sn]
    best = None; best_score = -1e9

    for sl, tp in TPSL_GRID:
        results = []
        for ci, di, entry, atr, date, sp in sigs:
            b, ex = sim_exit_np(ci, entry, di, atr, 0, sl, tp, 0, False)
            pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp
            results.append(pnl)
        n = len(results)
        if n < 10: continue
        gp = sum(p for p in results if p > 0); gl = abs(sum(p for p in results if p < 0)) + 0.001
        pf = gp / gl; wr = sum(1 for p in results if p > 0) / n * 100
        mid = n // 2; split = np.mean(results[:mid]) > 0 and np.mean(results[mid:]) > 0
        if not split or pf < 1.05: continue
        score = pf * (wr / 100)
        if score > best_score:
            best_score = score; best = ('TPSL', sl, tp, 0, pf, wr, n, split, results)

    for sl, act, trail in TRAIL_GRID:
        results = []
        for ci, di, entry, atr, date, sp in sigs:
            b, ex = sim_exit_np(ci, entry, di, atr, 1, sl, act, trail, False)
            pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp
            results.append(pnl)
        n = len(results)
        if n < 10: continue
        gp = sum(p for p in results if p > 0); gl = abs(sum(p for p in results if p < 0)) + 0.001
        pf = gp / gl; wr = sum(1 for p in results if p > 0) / n * 100
        mid = n // 2; split = np.mean(results[:mid]) > 0 and np.mean(results[mid:]) > 0
        if not split or pf < 1.05: continue
        score = pf * (wr / 100)
        if score > best_score:
            best_score = score; best = ('TRAIL', sl, act, trail, pf, wr, n, split, results)

    if best:
        etype, p1, p2, p3, pf, wr, n, split, pnls = best
        best_configs[sn] = {'type': etype, 'p1': p1, 'p2': p2, 'p3': p3,
                            'pf': pf, 'wr': wr, 'n': n, 'split': split}
        print(f"  {sn:22s} {etype:5s} SL={p1:.1f} {'TP' if etype=='TPSL' else 'ACT'}={p2:.2f} "
              f"{'   ' if etype=='TPSL' else f'TR={p3:.2f}'} PF={pf:.2f} WR={wr:.0f}% n={n:4d}")
    else:
        print(f"  {sn:22s} --- AUCUNE CONFIG VIABLE ---")

print(f"\n  {len(best_configs)}/{len(SIG)} strats avec config viable")

# ── FILTRE MARGE WR ──
print("\nFiltre marge WR > 5%...", flush=True)
safe_configs = {}
for sn, cfg in best_configs.items():
    etype = 0 if cfg['type'] == 'TPSL' else 1
    pnls = []
    for ci, di, entry, atr, date, sp in SIG[sn]:
        b, ex = sim_exit_np(ci, entry, di, atr, etype, cfg['p1'], cfg['p2'], cfg['p3'], False)
        pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp
        pnls.append(pnl)
    wins = [p for p in pnls if p > 0]; losses = [p for p in pnls if p <= 0]
    if not wins or not losses: continue
    wr = len(wins) / len(pnls) * 100
    avg_w = sum(wins) / len(wins); avg_l = abs(sum(losses) / len(losses))
    rr = avg_w / avg_l if avg_l > 0 else 0
    wr_min = 1 / (1 + rr) * 100 if rr > 0 else 100
    marge = wr - wr_min
    tag = "OK" if marge > MIN_MARGIN else "SKIP"
    print(f"  {sn:22s} WR={wr:.0f}% RR={rr:.2f} WRmin={wr_min:.0f}% marge={marge:+.1f}% {tag}")
    if marge > MIN_MARGIN:
        safe_configs[sn] = cfg

print(f"\n  {len(safe_configs)}/{len(best_configs)} strats safe")
best_configs = safe_configs

# ── BUILD TRADE ARRAYS ──
print("\nConstruction arrays trades...", flush=True)
strat_arrays = {}
for sn in best_configs:
    cfg = best_configs[sn]
    etype = 0 if cfg['type'] == 'TPSL' else 1
    rows = []
    for ci, di, entry, atr, date, sp in SIG[sn]:
        b, ex = sim_exit_np(ci, entry, di, atr, etype, cfg['p1'], cfg['p2'], cfg['p3'], False)
        pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp
        mo = f"{date.year}-{str(date.month).zfill(2)}"
        rows.append((ci, ci + b, di, pnl, cfg['p1'], atr, mo, sn))
    strat_arrays[sn] = rows

# ── EVAL COMBO ──
def eval_combo(strats, capital=1000.0, risk=0.01):
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
        events.append((ei, 0, idx)); events.append((xi, 1, idx))
    events.sort()
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; entry_caps = {}; pnl_by_entry = []
    for bar, evt, idx in events:
        if evt == 0: entry_caps[idx] = cap
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
            if di == 1: has_l = True
            else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    pnl_by_entry.sort(); pnls = [p for _, p in pnl_by_entry]
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    pm = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
            'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
            'split': p1 > 0 and p2 > 0, 'both': has_s and has_l, 'pm': pm, 'tm': len(months)}

# ── GREEDY ──
valid = list(best_configs.keys())
if len(valid) == 0:
    print("\nAucune strat safe. Arret.")
    import os, pickle
    _dir = f'data/{args.account}/{SYMBOL}'
    os.makedirs(_dir, exist_ok=True)
    save_data = {'strat_arrays': {}, 'best_configs': {}}
    with open(f'{_dir}/optim_data.pkl', 'wb') as f: pickle.dump(save_data, f)
    print(f"Saved {_dir}/optim_data.pkl (vide)")
    sys.exit(0)

ranked = sorted(valid, key=lambda sn: best_configs[sn]['pf'], reverse=True)
print(f"\n{'='*100}")
print(f"GREEDY COMBO BUILDER ({len(valid)} strats) — {SYMBOL.upper()}")
print(f"{'='*100}")

combo = [ranked[0]]; remaining = set(ranked[1:])
r = eval_combo(combo)
if r:
    print(f"\n  Start: {combo[0]}")
    print(f"    n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")

checkpoints = {}
for step in range(min(20, len(remaining))):
    best_add = None; best_cal = -1e9
    for sn in remaining:
        test = combo + [sn]
        r = eval_combo(test)
        if r and r['split'] and r['both']:
            if r['cal'] > best_cal:
                best_cal = r['cal']; best_add = sn; best_r = r
    if best_add is None: break
    combo.append(best_add); remaining.remove(best_add)
    r = best_r
    cfg = best_configs[best_add]
    print(f"\n  +{best_add:22s} ({len(combo):2d}) n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% "
          f"DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")
    checkpoints[len(combo)] = {'combo': list(combo), 'r': dict(r)}

# ── REPORT ──
print(f"\n{'='*100}")
for sz in sorted(checkpoints.keys()):
    r = checkpoints[sz]['r']
    print(f"  Greedy {sz:2d}  n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")

for sz in [3, 5, 8, 10]:
    if sz in checkpoints:
        print(f"\n  Composition Greedy {sz}:")
        for sn in checkpoints[sz]['combo']:
            cfg = best_configs[sn]
            tp_str = f"TP={cfg['p2']:.2f}" if cfg['type'] == 'TPSL' else f"ACT={cfg['p2']:.2f} TR={cfg['p3']:.2f}"
            print(f"    {sn:22s} {cfg['type']:5s} SL={cfg['p1']:.1f} {tp_str:16s} PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")

# ── SAVE ──
import os, pickle
_dir = f'data/{args.account}/{SYMBOL}'
os.makedirs(_dir, exist_ok=True)
save_data = {'strat_arrays': strat_arrays, 'best_configs': best_configs}
with open(f'{_dir}/optim_data.pkl', 'wb') as f: pickle.dump(save_data, f)
print(f"\nSaved {_dir}/optim_data.pkl")
