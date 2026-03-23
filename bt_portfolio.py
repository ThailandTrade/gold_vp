"""
Backtest d'un portfolio specifique.
Usage:
  python bt_portfolio.py                        → ICM, $1000, 1%
  python bt_portfolio.py ftmo                   → FTMO, $1000, 0.5%
  python bt_portfolio.py 5ers                   → 5ers, $1000, 0.5%
  python bt_portfolio.py icm --capital 100000   → ICM, $100k, 1%
  python bt_portfolio.py icm --risk 2           → ICM, $1000, 2%
  python bt_portfolio.py ftmo -c 200000 -r 0.5  → FTMO, $200k, 0.5%
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd, pickle
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

parser = argparse.ArgumentParser(description='Backtest portfolio')
parser.add_argument('account', nargs='?', default='icm', choices=['icm','ftmo','5ers'])
parser.add_argument('-c', '--capital', type=float, default=None, help='Capital initial (default: 1000)')
parser.add_argument('-r', '--risk', type=float, default=None, help='Risk %% par trade (ex: 1 pour 1%%)')
args = parser.parse_args()

# ── LOAD CONFIG ──
if args.account == 'ftmo':
    from config_ftmo import PORTFOLIO, RISK_PCT, BROKER
elif args.account == '5ers':
    from config_5ers import PORTFOLIO, RISK_PCT, BROKER
else:
    from config_icm import PORTFOLIO, RISK_PCT, BROKER

CAPITAL = args.capital if args.capital else 1000.0
RISK = args.risk / 100 if args.risk else RISK_PCT

print(f"Backtest {BROKER} — {len(PORTFOLIO)} strats @ {RISK*100:.1f}% risk — ${CAPITAL:,.0f}")
print(f"Portfolio: {', '.join(PORTFOLIO)}")
print()

# ── LOAD PRECOMPUTED DATA ──
try:
    with open('optim_data.pkl', 'rb') as f:
        data = pickle.load(f)
    strat_arrays = data['strat_arrays']
    best_configs = data['best_configs']
    print(f"Loaded optim_data.pkl ({len(strat_arrays)} strats)")
except FileNotFoundError:
    print("ERROR: optim_data.pkl not found. Run optimize_all.py first.")
    sys.exit(1)

# Check all portfolio strats exist
missing = [s for s in PORTFOLIO if s not in strat_arrays]
if missing:
    print(f"WARNING: strats missing from optim_data.pkl: {missing}")

# ── EVAL COMBO (event-based) ──
def eval_combo(strats, capital=CAPITAL, risk=RISK):
    combined = []
    for sn in strats:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    events = []
    for idx, (ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn) in enumerate(accepted):
        events.append((ei, 0, idx))
        events.append((xi, 1, idx))
    events.sort()
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0
    months = {}; entry_caps = {}; strat_stats = {}
    for bar, evt, idx in events:
        if evt == 0:
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
            ss = strat_stats.setdefault(_sn, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
            ss['n'] += 1
            if pnl > 0: ss['w'] += 1; ss['gp'] += pnl
            else: ss['gl'] += abs(pnl)
    pm = sum(1 for v in months.values() if v > 0)
    return {
        'n': n, 'pf': gp / (gl + 0.01), 'wr': wins / n * 100 if n > 0 else 0,
        'mdd': max_dd * 100, 'ret': (cap - capital) / capital * 100,
        'capital': cap, 'pm': pm, 'tm': len(months), 'months': months,
        'strat_stats': strat_stats
    }

r = eval_combo(PORTFOLIO)

# ── REPORT ──
print(f"\n{'='*80}")
print(f"RESULTATS {BROKER} — {len(PORTFOLIO)} strats @ {RISK_PCT*100:.1f}% risk")
print(f"{'='*80}")
print(f"  Trades:  {r['n']:,d} ({r['n']/(r['tm']*20):.1f}/jour)")
print(f"  PF:      {r['pf']:.2f}")
print(f"  WR:      {r['wr']:.0f}%")
print(f"  Max DD:  {r['mdd']:+.1f}%")
print(f"  Rend:    {r['ret']:+,.0f}%")
print(f"  Capital: ${r['capital']:,.0f} (start ${CAPITAL:,.0f})")
print(f"  Mois+:   {r['pm']}/{r['tm']}")

print(f"\n  Par strat:")
print(f"  {'Strat':>22s} {'Exit':>5s} {'SL':>4s} {'P2':>5s} {'P3':>5s} {'n':>5s} {'PF':>5s} {'WR':>4s}")
print(f"  {'-'*22} {'-'*5} {'-'*4} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*4}")
for sn in PORTFOLIO:
    cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
    ss = r['strat_stats'].get(sn, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
    pf = ss['gp'] / (ss['gl'] + 0.01) if ss['n'] > 0 else 0
    wr = ss['w'] / ss['n'] * 100 if ss['n'] > 0 else 0
    print(f"  {sn:>22s} {cfg[0]:>5s} {cfg[1]:4.1f} {cfg[2]:5.2f} {cfg[3]:5.2f} {ss['n']:5d} {pf:5.2f} {wr:3.0f}%")

print(f"\n  Par mois:")
for mo in sorted(r['months'].keys()):
    v = r['months'][mo]
    bar = '+' * int(max(0, v / 10)) if v > 0 else '-' * int(max(0, -v / 10))
    print(f"  {mo}  ${v:+10,.0f}  {bar}")

print(f"\n{'='*80}")
