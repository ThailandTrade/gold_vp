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
            'months': months, 'strat_stats': strat_stats, 'month_detail': month_detail}

# ── RUN ──
W = 90
print(f"\n{'='*W}")
print(f"  BACKTEST {BROKER} — ${CAPITAL:,.0f}")
print(f"{'='*W}")

all_results = []
for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    risk = args.risk / 100 if args.risk else icfg['risk_pct']
    if not portfolio:
        print(f"\n  {sym}: portfolio vide (TODO)"); continue

    sym_dir = f'/{sym.lower()}' if sym != 'XAUUSD' else ''
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

    # Collect for aggregate
    all_results.append({'sym': sym, 'r': r, 'risk': risk, 'portfolio': portfolio})

# ── AGGREGATE ALL INSTRUMENTS ──
if len(all_results) > 1:
    print(f"\n{'='*W}")
    print(f"  AGREGE — {len(all_results)} instruments @ ${CAPITAL:,.0f} chacun")
    print(f"{'='*W}")

    # Merge month_detail across all instruments
    all_months = set()
    for ar in all_results:
        all_months.update(ar['r']['month_detail'].keys())
    sorted_months = sorted(all_months)

    start_cap = CAPITAL * len(all_results)
    cap = start_cap; peak = cap; max_dd_pct = 0

    print(f"\n  {'Mois':>8s} {'Trades':>7s} {'Wins':>6s} {'WR':>5s} {'PF':>6s} {'PnL':>10s} {'Capital':>12s} {'Rend cum':>9s} {'DD':>7s} {'MaxDD':>7s}")
    print(f"  {'-'*85}")

    for mo in sorted_months:
        m_n = 0; m_w = 0; m_gp = 0; m_gl = 0; m_pnl = 0
        for ar in all_results:
            md = ar['r']['month_detail'].get(mo)
            if md:
                m_n += md['n']; m_w += md['w']; m_gp += md['gp']; m_gl += md['gl']
            m_pnl += ar['r']['months'].get(mo, 0)
        cap += m_pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak * 100
        if dd < max_dd_pct: max_dd_pct = dd
        rend_cum = (cap - start_cap) / start_cap * 100
        wr = m_w / m_n * 100 if m_n > 0 else 0
        pf = m_gp / (m_gl + 0.01) if m_gl > 0 else m_gp
        print(f"  {mo:>8s} {m_n:>7d} {m_w:>6d} {wr:>4.0f}% {pf:>5.2f} ${m_pnl:>+9,.0f} ${cap:>11,.0f} {rend_cum:>+8.1f}% {dd:>+6.2f}% {max_dd_pct:>+6.2f}%")

    # Totals
    tot_n = sum(ar['r']['n'] for ar in all_results)
    tot_w = sum(ss['w'] for ar in all_results for ss in ar['r']['strat_stats'].values())
    tot_gp = sum(ss['gp'] for ar in all_results for ss in ar['r']['strat_stats'].values())
    tot_gl = sum(ss['gl'] for ar in all_results for ss in ar['r']['strat_stats'].values())
    pm = sum(1 for mo in sorted_months if sum(ar['r']['months'].get(mo, 0) for ar in all_results) > 0)

    print(f"  {'-'*85}")
    print(f"  Trades: {tot_n:,d} | WR: {tot_w/tot_n*100:.0f}% | PF: {tot_gp/(tot_gl+0.01):.2f} | Max DD: {max_dd_pct:+.2f}% | Rend: {(cap-start_cap)/start_cap*100:+.1f}% | M+: {pm}/{len(sorted_months)}")
    print(f"  Capital: ${start_cap:,.0f} -> ${cap:,.0f} ({(cap-start_cap)/start_cap*100:+.1f}%)")

print(f"\n{'='*W}")
