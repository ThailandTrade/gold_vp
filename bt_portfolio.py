"""
Backtest complet — multi-instrument.
Usage:
  python bt_portfolio.py 5ers                    → tous instruments
  python bt_portfolio.py 5ers --symbol XAUUSD    → un seul instrument
  python bt_portfolio.py icm -c 100000           → avec capital
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd, pickle, importlib
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

parser = argparse.ArgumentParser(description='Backtest portfolio')
parser.add_argument('account', nargs='?', default='icm', choices=['icm','ftmo','5ers'])
parser.add_argument('-c', '--capital', type=float, default=None)
parser.add_argument('-r', '--risk', type=float, default=None)
parser.add_argument('--symbol', default=None, help='Single instrument (default: all)')
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = cfg.INSTRUMENTS

# Filter to single symbol if specified
if args.symbol:
    sym = args.symbol.upper()
    if sym in INSTRUMENTS:
        INSTRUMENTS = {sym: INSTRUMENTS[sym]}
    else:
        print(f"ERROR: {sym} not in config. Available: {list(cfg.INSTRUMENTS.keys())}")
        sys.exit(1)

CAPITAL = args.capital or 100000.0

def eval_combo(strat_arrays, portfolio, risk):
    combined = []
    for sn in portfolio:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    if not combined: return None
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    if n == 0: return None
    events = [(ei, 0, idx) for idx, (ei,*_) in enumerate(accepted)] + \
             [(xi, 1, idx) for idx, (_,xi,*__) in enumerate(accepted)]
    events.sort()
    cap = CAPITAL; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0
    months = {}; entry_caps = {}; strat_stats = {}
    # Per-month detailed stats
    month_detail = {}  # mo -> {'n','w','gp','gl','cap','peak','dd'}
    for bar, evt, idx in events:
        if evt == 0: entry_caps[idx] = cap
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
            md = month_detail.setdefault(mo, {'n':0,'w':0,'gp':0,'gl':0})
            md['n'] += 1
            if pnl > 0: md['w'] += 1; md['gp'] += pnl
            else: md['gl'] += abs(pnl)
            month_detail[mo]['cap'] = cap
            month_detail[mo]['peak'] = peak
            month_detail[mo]['dd'] = max_dd
            ss = strat_stats.setdefault(_sn, {'n':0,'w':0,'gp':0,'gl':0})
            ss['n'] += 1
            if pnl > 0: ss['w'] += 1; ss['gp'] += pnl
            else: ss['gl'] += abs(pnl)
    pm = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'pf': gp/(gl+0.01), 'wr': wins/n*100, 'mdd': max_dd*100,
            'ret': (cap-CAPITAL)/CAPITAL*100, 'capital': cap, 'pm': pm, 'tm': len(months),
            'months': months, 'strat_stats': strat_stats, 'month_detail': month_detail,
            'accepted': accepted}

# ── RUN ──
W = 90
print(f"\n{'='*W}")
print(f"  BACKTEST {BROKER} — ${CAPITAL:,.0f}")
print(f"{'='*W}")

all_results = []
all_sym_trades = []
for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    risk = args.risk / 100 if args.risk else icfg['risk_pct']
    if not portfolio:
        print(f"\n  {sym}: portfolio vide (TODO)"); continue

    import re
    sym_san = re.sub(r"[^a-z0-9]+", "_", sym.lower()).strip("_")
    sym_dir = f'/{sym_san}' if sym != 'XAUUSD' else ''
    pkl_file = f'data/{args.account}{sym_dir}/optim_data.pkl'
    try:
        with open(pkl_file, 'rb') as f:
            data = pickle.load(f)
        strat_arrays = data['strat_arrays']
    except FileNotFoundError:
        print(f"\n  {sym}: {pkl_file} not found. Run optimize_all.py {args.account} --symbol {sym.lower()}")
        continue

    missing = [s for s in portfolio if s not in strat_arrays]
    if missing:
        print(f"\n  {sym}: WARNING strats missing: {missing}")

    r = eval_combo(strat_arrays, portfolio, risk)
    if not r:
        print(f"\n  {sym}: 0 trades"); continue

    print(f"\n{'-'*W}")
    print(f"  {sym} — {len(portfolio)} strats @ {risk*100:.2f}%")
    print(f"{'-'*W}")
    print(f"  Trades: {r['n']:,d} | PF: {r['pf']:.2f} | WR: {r['wr']:.0f}% | DD: {r['mdd']:+.1f}% | Rend: {r['ret']:+,.0f}% | M+: {r['pm']}/{r['tm']}")
    print(f"  Capital: ${r['capital']:,.0f}")

    # Per strat
    print(f"\n  {'Strat':>22s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'PnL':>10s}")
    for sn in portfolio:
        ss = r['strat_stats'].get(sn, {'n':0,'w':0,'gp':0,'gl':0})
        if ss['n'] > 0:
            pf = ss['gp']/(ss['gl']+0.01)
            wr = ss['w']/ss['n']*100
            pnl = ss['gp'] - ss['gl']
            print(f"  {sn:>22s} {ss['n']:>5d} {wr:>4.0f}% {pf:>5.2f} ${pnl:>+9,.0f}")

    # Per month
    print(f"\n  {'Mois':>8s} {'PnL':>10s}")
    for mo in sorted(r['months'].keys()):
        v = r['months'][mo]
        print(f"  {mo:>8s} ${v:>+9,.0f}")

    # Collect accepted trades for aggregate (with symbol tag)
    all_sym_trades.append({'sym': sym, 'accepted': r['accepted'], 'risk': risk})

# ── AGGREGATE: single account, all instruments, trade-by-trade ──
if len(all_sym_trades) > 1:
    print(f"\n{'='*W}")
    print(f"  AGREGE — {len(all_sym_trades)} instruments — compte unique ${CAPITAL:,.0f}")
    print(f"{'='*W}")

    # Merge all trades (already conflict-filtered per instrument in eval_combo)
    filtered = []
    for st in all_sym_trades:
        for t in st['accepted']:
            filtered.append((*t, st['risk'], st['sym']))

    # Event-based simulation on single capital
    events = [(ei, 0, idx) for idx, (ei,*_) in enumerate(filtered)] + \
             [(xi, 1, idx) for idx, (_,xi,*__) in enumerate(filtered)]
    events.sort()

    cap = CAPITAL; peak = cap; max_dd = 0
    entry_caps = {}
    # Monthly aggregation
    mo_stats = {}
    cur_mo = None; mo_worst_dd = 0

    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, sn, risk, sym = filtered[idx]
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak * 100
            if dd < max_dd: max_dd = dd

            # Track worst DD vs all-time peak per month
            if mo != cur_mo:
                cur_mo = mo; mo_worst_dd = 0
            if dd < mo_worst_dd: mo_worst_dd = dd

            ms = mo_stats.setdefault(mo, {'n':0,'w':0,'gp':0,'gl':0,'pnl':0})
            ms['n'] += 1
            if pnl > 0: ms['w'] += 1; ms['gp'] += pnl
            else: ms['gl'] += abs(pnl)
            ms['pnl'] += pnl
            ms['cap'] = cap
            ms['peak'] = peak
            ms['max_dd'] = max_dd
            ms['mo_dd'] = mo_worst_dd

    sorted_months = sorted(mo_stats.keys())
    print(f"\n  {'Mois':>8s} {'Trades':>7s} {'Wins':>6s} {'WR':>5s} {'PF':>6s} {'PnL':>10s} {'Capital':>12s} {'Rend cum':>9s} {'DD mois':>8s} {'MaxDD':>7s}")
    print(f"  {'-'*87}")

    for mo in sorted_months:
        ms = mo_stats[mo]
        wr = ms['w'] / ms['n'] * 100 if ms['n'] > 0 else 0
        pf = ms['gp'] / (ms['gl'] + 0.01)
        rend_cum = (ms['cap'] - CAPITAL) / CAPITAL * 100
        print(f"  {mo:>8s} {ms['n']:>7d} {ms['w']:>6d} {wr:>4.0f}% {pf:>5.2f} ${ms['pnl']:>+9,.0f} ${ms['cap']:>11,.0f} {rend_cum:>+8.1f}% {ms['mo_dd']:>+7.2f}% {ms['max_dd']:>+6.2f}%")

    tot_n = sum(ms['n'] for ms in mo_stats.values())
    tot_w = sum(ms['w'] for ms in mo_stats.values())
    tot_gp = sum(ms['gp'] for ms in mo_stats.values())
    tot_gl = sum(ms['gl'] for ms in mo_stats.values())
    pm = sum(1 for ms in mo_stats.values() if ms['pnl'] > 0)

    print(f"  {'-'*85}")
    print(f"  Trades: {tot_n:,d} | WR: {tot_w/tot_n*100:.0f}% | PF: {tot_gp/(tot_gl+0.01):.2f} | Max DD: {max_dd:+.2f}% | Rend: {(cap-CAPITAL)/CAPITAL*100:+.1f}% | M+: {pm}/{len(sorted_months)}")
    print(f"  Capital: ${CAPITAL:,.0f} -> ${cap:,.0f} ({(cap-CAPITAL)/CAPITAL*100:+.1f}%)")

print(f"\n{'='*W}")
