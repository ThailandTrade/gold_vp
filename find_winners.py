"""
find_winners.py - Trouve les strats "gagnantes long terme" pour un broker.

Pour chaque (instrument, strat):
  1. Teste toutes les configs d'exit (TPSL/TRAIL/BE_TP grilles)
  2. Cost-r applique au strat (par trade)
  3. Choisit l'exit qui maximise avg_R_trim
  4. Garde la strat si elle passe les 7 criteres "gagnante long terme":
     - n >= 80
     - avg_R_trim > 0 (full)
     - median_R > 0 (full)
     - outlier_share < 30%
     - M+ >= 7/12
     - avg_R_trim 1ere moitie > 0
     - avg_R_trim 2eme moitie > 0 (pas de degradation)

Output: portfolio + STRAT_EXITS prets a coller.

Usage:
  python find_winners.py pepperstone --tf 15m
  python find_winners.py pepperstone --tf 15m --symbol nas100
"""
import warnings; warnings.filterwarnings('ignore')
import sys, os, argparse, importlib
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
import numpy as np, pandas as pd
from collections import defaultdict
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn
from backtest_engine import load_data, prev_trading_day, _make_day_data
from strats import detect_all, sim_exit_custom, compute_indicators, REMOVED_STRATS

parser = argparse.ArgumentParser()
parser.add_argument('account', choices=['ftmo','5ers','pepperstone'])
parser.add_argument('--tf', default='15m')
parser.add_argument('--symbol', default=None)
parser.add_argument('--cost-r', type=float, default=0.05)
parser.add_argument('--n-min', type=int, default=80)
parser.add_argument('--mpos-min', type=int, default=7)
parser.add_argument('--outlier-max', type=float, default=0.30)
parser.add_argument('--avgr-min', type=float, default=0.05, help='Edge tangible minimum (apres cost)')
parser.add_argument('--tpsl-only', action='store_true')
args = parser.parse_args()

# Source de verite: pairs_<account>.txt (= tous les instruments disponibles)
pairs_file = f'pairs_{args.account}.txt'
INSTRUMENTS = []
if os.path.exists(pairs_file):
    with open(pairs_file) as f:
        next(f)  # skip header
        for line in f:
            line = line.strip()
            if line and ',' in line:
                INSTRUMENTS.append(line.split(',')[1])
else:
    cfg = importlib.import_module(f'config_{args.account}')
    INSTRUMENTS = list(getattr(cfg, 'ALL_INSTRUMENTS', cfg.INSTRUMENTS).keys())
    print(f"WARN: {pairs_file} introuvable, fallback sur config")

if args.symbol:
    sym_up = args.symbol.upper()
    INSTRUMENTS = [s for s in INSTRUMENTS if s.upper() == sym_up]
    if not INSTRUMENTS:
        print(f"ERROR: {args.symbol} non trouve dans pairs/config")
        sys.exit(1)

# Strats a tester (toutes sauf REMOVED + duplicates)
DUPLICATE_STRATS = {'IDX_KC_BRK','IDX_ENGULF','ALL_ROC_ZERO','IDX_NR4'}

# Grilles d'exits (memes que optimize_all)
TPSL_GRID = [(sl, tp) for sl in [0.5,0.75,1.0,1.25,1.5,2.0,2.5,3.0] for tp in [0.5,0.75,1.0,1.5,2.0,2.5,3.0,4.0,5.0]]
TRAIL_GRID = [] if args.tpsl_only else [(sl, act, trail) for sl in [1.0,1.5,2.0,2.5,3.0]
              for act in [0.3,0.5,0.75,1.0] for trail in [0.3,0.5,0.75]]
BE_TP_GRID = [] if args.tpsl_only else [(sl, be_act, tp) for sl in [1.0,1.5,2.0,2.5,3.0]
              for be_act in [0.3,0.5,0.75] for tp in [0.75,1.0,1.5,2.0,3.0]
              if be_act < tp]

print(f"Cost-r {args.cost_r}R/trade | Filtres: n>={args.n_min} M+>={args.mpos_min} OS<{args.outlier_max:.0%} | grilles TPSL={len(TPSL_GRID)} TRAIL={len(TRAIL_GRID)} BE_TP={len(BE_TP_GRID)}")


def compute_metrics(pnls_R_arr, dates_arr, cost_r):
    """Calcule metriques sur trades. Cost-r applique au pnl_R."""
    if len(pnls_R_arr) == 0: return None
    pnls_cost = pnls_R_arr - cost_r
    n = len(pnls_cost)
    sorted_pnls = np.sort(pnls_cost)
    k5 = int(n * 0.05)
    trimmed = sorted_pnls[k5:n-k5] if k5 > 0 and n > 2*k5 else sorted_pnls
    avg_R_trim = float(trimmed.mean()) if len(trimmed) > 0 else 0.0
    median_R = float(np.median(pnls_cost))
    avg_R = float(pnls_cost.mean())
    pos = pnls_cost[pnls_cost > 0]
    gp = float(pos.sum())
    gl = float(abs(pnls_cost[pnls_cost < 0].sum()))
    pf = gp / (gl + 1e-6) if gl > 0 else (99.99 if gp > 0 else 0)
    wr = float((pnls_cost > 0).mean() * 100)
    pos_sorted = np.sort(pos)[::-1] if len(pos) > 0 else np.array([])
    kp = max(1, int(len(pos_sorted) * 0.05)) if len(pos_sorted) > 0 else 0
    outlier_share = float(pos_sorted[:kp].sum() / gp) if gp > 0 and kp > 0 else 0.0
    months = defaultdict(float)
    for pn, d in zip(pnls_cost, dates_arr):
        months[f"{d.year}-{d.month:02d}"] += float(pn)
    m_pos = sum(1 for v in months.values() if v > 0)
    m_total = len(months)
    return {'n':n,'pf':pf,'wr':wr,'avg_R':avg_R,'avg_R_trim':avg_R_trim,'median_R':median_R,
            'outlier_share':outlier_share,'m_pos':m_pos,'m_total':m_total}


def split_metrics(pnls_R_arr, dates_arr, cost_r):
    """Calcule avg_R_trim sur 1ere moitie et 2eme moitie (split par date au median)."""
    n = len(pnls_R_arr)
    if n < 20: return None, None
    # Sort by date pour split chronologique
    order = np.argsort(dates_arr)
    sorted_pnls = pnls_R_arr[order]
    sorted_dates = dates_arr[order]
    half = n // 2
    h1 = compute_metrics(sorted_pnls[:half], sorted_dates[:half], cost_r)
    h2 = compute_metrics(sorted_pnls[half:], sorted_dates[half:], cost_r)
    return (h1['avg_R_trim'] if h1 else 0), (h2['avg_R_trim'] if h2 else 0)


def collect_signals(candles, daily_atr, global_atr, trading_days, all_strats):
    """Detect all signals per strat. Returns SIG dict {sn: [(ci, di, entry, atr, date)]}."""
    SIG = defaultdict(list)
    prev_d = None; trig = {}; day_atr = None
    prev_day_data = None; prev2_day_data = None
    portfolio_set = set(all_strats)

    for ci in range(200, len(candles)):
        row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
        hour = ct.hour + ct.minute / 60.0
        if today != prev_d:
            if prev_d:
                yc = candles[candles['date'] == prev_d]
                if len(yc) > 0:
                    prev2_day_data = prev_day_data
                    prev_day_data = _make_day_data(yc)
            prev_d = today; trig = {}
            pd_ = prev_trading_day(today, trading_days)
            day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        atr = day_atr
        if atr == 0 or atr is None: continue
        ds = pd.Timestamp(today.year, today.month, today.day, 0, 0, tz='UTC')
        te = pd.Timestamp(today.year, today.month, today.day, 6, 0, tz='UTC')
        ls = pd.Timestamp(today.year, today.month, today.day, 8, 0, tz='UTC')
        ns = pd.Timestamp(today.year, today.month, today.day, 14, 30, tz='UTC')
        tv = candles[(candles['ts_dt'] >= ds) & (candles['ts_dt'] <= ct)]
        tok = tv[tv['ts_dt'] < te]
        lon = tv[(tv['ts_dt'] >= ls) & (tv['ts_dt'] < ns)]

        def add_sig(sn, d_dir, e):
            if sn in portfolio_set:
                di = 1 if d_dir == 'long' else -1
                SIG[sn].append((ci, di, e, atr, today))

        detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon,
                   prev_day_data, add_sig, prev2_day_data)
    return SIG


def evaluate_exit(candles, signals, etype, p1, p2, p3):
    """Simule tous les trades pour cette config. Retourne (pnls_R_arr, dates_arr)."""
    pnls = []; dates = []
    for ci, di, entry, atr, date in signals:
        d_str = 'long' if di == 1 else 'short'
        b, ex = sim_exit_custom(candles, ci, entry, d_str, atr, etype, p1, p2, p3, check_entry_candle=False)
        pnl_oz = (ex - entry) if di == 1 else (entry - ex)
        risk_1r = p1 * atr
        if risk_1r <= 0: continue
        pnls.append(pnl_oz / risk_1r)
        dates.append(date)
    return np.array(pnls), np.array(dates)


# === MAIN ===
all_results = {}  # sym -> [(sn, exit_cfg, metrics)]
config_blocks = []
exits_blocks = []

for sym in INSTRUMENTS:
    print(f"\n{'='*100}\n{sym}\n{'='*100}", flush=True)
    conn = get_conn()
    candles, daily_atr, global_atr, trading_days = load_data(conn, sym, tf=args.tf)
    conn.close()
    if len(candles) < 500:
        print(f"  Sample trop court ({len(candles)} bars), skip"); continue

    # Liste des strats a tester (toutes celles non removed/duplicates)
    from strats import STRAT_NAMES
    all_strats = [s for s in STRAT_NAMES if s not in REMOVED_STRATS and s not in DUPLICATE_STRATS]

    print(f"  Detect signals ({len(all_strats)} strats)...", flush=True)
    SIG = collect_signals(candles, daily_atr, global_atr, trading_days, all_strats)
    print(f"  {len(SIG)} strats avec >=1 signal", flush=True)

    sym_winners = []
    print(f"  {'Strat':>22s} {'Exit':>20s} {'n':>5s} {'medR':>7s} {'avgR':>7s} {'avgRt':>7s} {'OS':>5s} {'h1':>7s} {'h2':>7s} {'M+/Tot':>7s}  Status", flush=True)

    for sn in sorted(SIG.keys()):
        signals = SIG[sn]
        if len(signals) < args.n_min: continue

        best = None  # (metrics, etype, p1, p2, p3, h1, h2)
        # Test all exits
        for sl, tp in TPSL_GRID:
            pnls, dates = evaluate_exit(candles, signals, 'TPSL', sl, tp, 0)
            m = compute_metrics(pnls, dates, args.cost_r)
            if not m: continue
            h1, h2 = split_metrics(pnls, dates, args.cost_r)
            if best is None or m['avg_R_trim'] > best[0]['avg_R_trim']:
                best = (m, 'TPSL', sl, tp, 0, h1, h2)
        for sl, act, trail in TRAIL_GRID:
            pnls, dates = evaluate_exit(candles, signals, 'TRAIL', sl, act, trail)
            m = compute_metrics(pnls, dates, args.cost_r)
            if not m: continue
            h1, h2 = split_metrics(pnls, dates, args.cost_r)
            if best is None or m['avg_R_trim'] > best[0]['avg_R_trim']:
                best = (m, 'TRAIL', sl, act, trail, h1, h2)
        for sl, be_act, tp in BE_TP_GRID:
            pnls, dates = evaluate_exit(candles, signals, 'BE_TP', sl, be_act, tp)
            m = compute_metrics(pnls, dates, args.cost_r)
            if not m: continue
            h1, h2 = split_metrics(pnls, dates, args.cost_r)
            if best is None or m['avg_R_trim'] > best[0]['avg_R_trim']:
                best = (m, 'BE_TP', sl, be_act, tp, h1, h2)

        if best is None: continue
        m, etype, p1, p2, p3, h1, h2 = best

        # Filtre 8 criteres
        ok = (m['n'] >= args.n_min
              and m['avg_R'] >= args.avgr_min
              and m['avg_R_trim'] > 0
              and m['median_R'] > 0
              and m['outlier_share'] < args.outlier_max
              and m['m_pos'] >= args.mpos_min
              and h1 > 0
              and h2 > 0)
        status = ''
        if ok:
            sym_winners.append((sn, (etype, p1, p2, p3), m))
            status = 'WIN'
        else:
            r = []
            if m['n'] < args.n_min: r.append(f"n<{args.n_min}")
            if m['avg_R'] < args.avgr_min: r.append(f"avgR<{args.avgr_min}")
            if m['avg_R_trim'] <= 0: r.append("avgRt<=0")
            if m['median_R'] <= 0: r.append("medR<=0")
            if m['outlier_share'] >= args.outlier_max: r.append(f"OS={m['outlier_share']:.0%}")
            if m['m_pos'] < args.mpos_min: r.append(f"M+<{args.mpos_min}")
            if h1 <= 0: r.append("h1<=0")
            if h2 <= 0: r.append("h2<=0")
            status = ' / '.join(r)

        if ok or m['avg_R_trim'] > 0:
            ex_lbl = f"{etype} {p1}/{p2}/{p3}"
            print(f"  {sn:>22s} {ex_lbl:>20s} {m['n']:>5d} {m['median_R']:>+6.3f} {m['avg_R']:>+6.3f} {m['avg_R_trim']:>+6.3f} {m['outlier_share']:>4.0%} {h1:>+6.3f} {h2:>+6.3f} {m['m_pos']:>2d}/{m['m_total']:<4d}  {status}", flush=True)

    print(f"\n  → {len(sym_winners)} strats WIN sur {len(SIG)} testees")
    if sym_winners:
        all_results[sym] = sym_winners

# === OUTPUT ===
print(f"\n{'='*100}\n  RESUME\n{'='*100}")
total_winners = sum(len(v) for v in all_results.values())
print(f"  {total_winners} strats WIN sur {len(all_results)} instruments")

print(f"\n=== config_{args.account} ALL_INSTRUMENTS ===\n")
for sym, winners in all_results.items():
    portfolio = [sn for sn, _, _ in winners]
    print(f"    '{sym}': {{")
    print(f"        'risk_pct': 0.005,")
    print(f"        'portfolio': {portfolio},")
    print(f"    }},")

print(f"\n=== STRAT_EXITS ===\n")
for sym, winners in all_results.items():
    print(f"STRAT_EXITS[('{args.account}', '{sym}')] = {{")
    for sn, exit_cfg, _ in winners:
        print(f"    '{sn}': {exit_cfg},")
    print(f"}}\n")
