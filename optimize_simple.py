"""
optimize_simple.py — Filtre "all-edge" pour Pepperstone (et autres).

PRE-REQUIS: optimize_all doit avoir tourne avec SPREAD_R = cost-r (cost applique
au niveau strat lors du choix des exits -> les pkl best_configs ont les metrics
deja sous cost).

Approche:
- Lit best_configs et strat_arrays des pkl optim_data
- Filtre par criteres user (PF, WR, n, M+) — metrics deja sous cost
- Toutes les strats passant -> portfolio (pas de beam search, pas de cleanup)
- Confluences (signaux simultanes meme direction) acceptees

Usage:
  python optimize_simple.py pepperstone --tf 15m
  python optimize_simple.py pepperstone --tf 15m --pf-min 1.15 --mpos-min 7
"""
import warnings; warnings.filterwarnings('ignore')
import sys, os, pickle, argparse, importlib
sys.stdout.reconfigure(encoding='utf-8')
from collections import defaultdict

parser = argparse.ArgumentParser()
parser.add_argument('account', choices=['icm','ftmo','5ers','pepperstone'])
parser.add_argument('--tf', default='15m')
parser.add_argument('--symbol', default=None, help='Si fourni, ne traite qu\'un sym')
parser.add_argument('--pf-min', type=float, default=1.15)
parser.add_argument('--wr-min', type=float, default=60.0)
parser.add_argument('--n-min', type=int, default=80)
parser.add_argument('--mpos-min', type=int, default=7)
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
INSTRUMENTS = list(getattr(cfg, 'ALL_INSTRUMENTS', cfg.INSTRUMENTS).keys())
if args.symbol:
    sym = args.symbol.upper()
    if sym not in [s.upper() for s in INSTRUMENTS]:
        print(f"ERROR: {sym} not in config")
        sys.exit(1)
    INSTRUMENTS = [s for s in INSTRUMENTS if s.upper() == sym]

W = 100
print('='*W)
print(f"  OPTIMIZE SIMPLE — {args.account.upper()} (lecture pkl, metrics deja sous cost)")
print(f"  Filtres: PF >= {args.pf_min}  WR >= {args.wr_min}%  n >= {args.n_min}  M+ >= {args.mpos_min}")
print('='*W)


def metrics_from_strat_arrays(trades):
    """Recompute metrics directly from strat_arrays (pnl deja sous cost si SPREAD_R applique)."""
    if not trades: return None
    n, wins, gp, gl = 0, 0, 0.0, 0.0
    months = defaultdict(float)
    for tup in trades:
        if len(tup) < 7: continue
        ci, xi, di, pnl_oz, sl_atr, atr, mo = tup[:7]
        risk_1r = sl_atr * atr
        if risk_1r <= 0: continue
        pnl_r = pnl_oz / risk_1r
        n += 1
        if pnl_r > 0: wins += 1; gp += pnl_r
        else: gl += abs(pnl_r)
        months[mo] += pnl_r
    if n == 0: return None
    pf = gp / (gl + 1e-6) if gl > 0 else (99.99 if gp > 0 else 0)
    wr = wins / n * 100
    m_pos = sum(1 for v in months.values() if v > 0)
    m_neg = sum(1 for v in months.values() if v <= 0)
    m_total = len(months)
    avg_r = (gp - gl) / n
    return {'n':n,'pf':pf,'wr':wr,'m_pos':m_pos,'m_neg':m_neg,'m_total':m_total,'avg_r':avg_r}


# Output buffers
config_block = []
exits_block = []
total_pass = 0
total_strats_tested = 0
all_results = {}

for sym in INSTRUMENTS:
    sym_lower = sym.lower().replace('.','_')
    pkl_path = f'data/{args.account}/{sym_lower}/optim_data.pkl'
    if not os.path.exists(pkl_path):
        print(f"\n  {sym}: pkl manquant ({pkl_path})")
        continue
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f)
    strat_arrays = data.get('strat_arrays', {})
    best_configs = data.get('best_configs', {})
    if not strat_arrays:
        print(f"\n  {sym}: strat_arrays vide")
        continue

    print(f"\n  {sym}  ({len(strat_arrays)} strats testees)")
    print(f"  {'-'*W}")
    print(f"  {'Strat':>22s} {'n':>5s} {'PF':>5s} {'WR':>5s} {'M+/Tot':>7s} {'avgR':>6s}  Status")

    passing = []
    for sn, trades in sorted(strat_arrays.items()):
        m = metrics_from_strat_arrays(trades)
        if not m: continue
        total_strats_tested += 1
        ok = (m['pf'] >= args.pf_min and m['wr'] >= args.wr_min and m['n'] >= args.n_min and m['m_pos'] >= args.mpos_min)
        status = ''
        if ok:
            passing.append((sn, m))
            status = 'PASS'
        else:
            reasons = []
            if m['pf'] < args.pf_min: reasons.append(f"PF<{args.pf_min}")
            if m['wr'] < args.wr_min: reasons.append(f"WR<{args.wr_min}")
            if m['n'] < args.n_min: reasons.append(f"n<{args.n_min}")
            if m['m_pos'] < args.mpos_min: reasons.append(f"M+<{args.mpos_min}")
            status = ' / '.join(reasons)
        # Print only PASS or marginal failures
        if ok or (m['pf'] >= 1.0 and m['n'] >= 50):
            print(f"  {sn:>22s} {m['n']:>5d} {m['pf']:>5.2f} {m['wr']:>4.0f}% {m['m_pos']:>2d}/{m['m_total']:<4d} {m['avg_r']:>+6.3f}  {status}")

    if passing:
        print(f"\n  → {len(passing)}/{len(strat_arrays)} strats PASS sur {sym}")
        total_pass += len(passing)
        all_results[sym] = passing
        # Genere les blocs
        portfolio = [sn for sn, _ in passing]
        config_block.append((sym, portfolio))
        sym_exits = {}
        for sn, _ in passing:
            cfg_e = best_configs.get(sn)
            if cfg_e:
                sym_exits[sn] = (cfg_e['type'], cfg_e['p1'], cfg_e['p2'], cfg_e['p3'])
        exits_block.append((sym, sym_exits))
    else:
        print(f"\n  → Aucune strat ne passe le filtre sur {sym}")

# === RESUME ===
print('\n' + '='*W)
print(f"  RESUME: {total_pass} strats PASS sur {total_strats_tested} testees ({len(all_results)} instruments avec >=1 strat)")
print('='*W)

# === Bloc config_<account>.py ===
print(f"\n=== Config ALL_INSTRUMENTS pour config_{args.account}.py ===\n")
for sym, portfolio in config_block:
    print(f"    '{sym}': {{")
    print(f"        'risk_pct': 0.005,")
    print(f"        'portfolio': {portfolio},")
    print(f"    }},")

# === Bloc strat_exits.py ===
print(f"\n=== STRAT_EXITS additions pour strat_exits.py ===\n")
for sym, sym_exits in exits_block:
    print(f"STRAT_EXITS[('{args.account}', '{sym}')] = {{")
    for sn, e in sym_exits.items():
        print(f"    '{sn}': {e},")
    print(f"}}")
    print()
