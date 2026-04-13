"""
Backtest complet — multi-instrument.
Utilise backtest_engine.py (moteur unique, meme code que compare_today et live).

Usage:
  python bt_portfolio.py 5ers                    → tous instruments
  python bt_portfolio.py 5ers --symbol XAUUSD    → un seul instrument
  python bt_portfolio.py icm -c 100000           → avec capital
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, importlib
sys.stdout.reconfigure(encoding='utf-8')
from phase1_poc_calculator import get_conn
from strat_exits import STRAT_EXITS
from backtest_engine import load_data, collect_trades, eval_portfolio

parser = argparse.ArgumentParser(description='Backtest portfolio')
parser.add_argument('account', choices=['icm', 'ftmo', '5ers'])
parser.add_argument('-c', '--capital', type=float, default=None)
parser.add_argument('-r', '--risk', type=float, default=None)
parser.add_argument('--symbol', default=None, help='Single instrument (default: all)')
parser.add_argument('--tf', default='5m', help='Timeframe: 5m or 15m')
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = getattr(cfg, 'ALL_INSTRUMENTS', cfg.INSTRUMENTS)

if args.symbol:
    sym = args.symbol.upper()
    if sym in INSTRUMENTS:
        INSTRUMENTS = {sym: INSTRUMENTS[sym]}
    else:
        print(f"ERROR: {sym} not in config. Available: {list(cfg.ALL_INSTRUMENTS.keys())}")
        sys.exit(1)

CAPITAL = args.capital or 100000.0

W = 90
print(f"\n{'='*W}")
print(f"  BACKTEST {BROKER} — ${CAPITAL:,.0f}")
print(f"{'='*W}")

conn = get_conn()
all_sym_trades = []

for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    risk = args.risk / 100 if args.risk else icfg['risk_pct']
    if not portfolio:
        print(f"\n  {sym}: portfolio vide"); continue

    sym_exits = STRAT_EXITS.get((args.account, sym), {})

    print(f"\n  Loading {sym}...", end='', flush=True)
    candles, daily_atr, global_atr, trading_days = load_data(conn, sym, tf=args.tf)
    print(f" {len(candles)} bars, {len(trading_days)} days", flush=True)

    trades = collect_trades(candles, daily_atr, global_atr, trading_days, portfolio, sym_exits)
    r = eval_portfolio(trades, risk, CAPITAL)
    if not r:
        print(f"  {sym}: 0 trades"); continue

    print(f"{'-'*W}")
    print(f"  {sym} — {len(portfolio)} strats @ {risk*100:.2f}%")
    print(f"{'-'*W}")
    print(f"  Trades: {r['n']:,d} | PF: {r['pf']:.2f} | WR: {r['wr']:.0f}% | DD: {r['mdd']:+.1f}% | Rend: {r['ret']:+,.0f}% | M+: {r['pm']}/{r['tm']}")
    print(f"  Capital: ${r['capital']:,.0f}")

    print(f"\n  {'Strat':>22s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'PnL':>10s}")
    for sn in portfolio:
        ss = r['strat_stats'].get(sn, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
        if ss['n'] > 0:
            pf = ss['gp'] / (ss['gl'] + 0.01)
            wr = ss['w'] / ss['n'] * 100
            pnl = ss['gp'] - ss['gl']
            print(f"  {sn:>22s} {ss['n']:>5d} {wr:>4.0f}% {pf:>5.2f} ${pnl:>+9,.0f}")

    print(f"\n  {'Mois':>8s} {'PnL':>10s}")
    for mo in sorted(r['months'].keys()):
        v = r['months'][mo]
        print(f"  {mo:>8s} ${v:>+9,.0f}")

    all_sym_trades.append({'sym': sym, 'accepted': trades, 'risk': risk})

# ── AGGREGATE ──
if len(all_sym_trades) > 1:
    print(f"\n{'='*W}")
    print(f"  AGREGE — {len(all_sym_trades)} instruments — compte unique ${CAPITAL:,.0f}")
    print(f"{'='*W}")

    filtered = []
    for st in all_sym_trades:
        for t in st['accepted']:
            filtered.append((*t, st['risk'], st['sym']))

    events = [(ei, 0, idx) for idx, (ei, *_) in enumerate(filtered)] + \
             [(xi, 1, idx) for idx, (_, xi, *__) in enumerate(filtered)]
    events.sort()

    cap = CAPITAL; peak = cap; max_dd = 0
    entry_caps = {}; mo_stats = {}; dd_per_month = {}

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
            if mo not in dd_per_month or dd < dd_per_month[mo]:
                dd_per_month[mo] = dd
            ms = mo_stats.setdefault(mo, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0, 'pnl': 0})
            ms['n'] += 1
            if pnl > 0: ms['w'] += 1; ms['gp'] += pnl
            else: ms['gl'] += abs(pnl)
            ms['pnl'] += pnl
            ms['cap'] = cap; ms['peak'] = peak; ms['max_dd'] = max_dd

    sorted_months = sorted(mo_stats.keys())
    print(f"\n  {'Mois':>8s} {'Trades':>7s} {'Wins':>6s} {'WR':>5s} {'PF':>6s} {'PnL':>10s} {'Capital':>12s} {'Rend cum':>9s} {'DD mois':>8s} {'MaxDD':>7s}")
    print(f"  {'-'*87}")
    for mo in sorted_months:
        ms = mo_stats[mo]
        wr = ms['w'] / ms['n'] * 100 if ms['n'] > 0 else 0
        pf = ms['gp'] / (ms['gl'] + 0.01)
        rend_cum = (ms['cap'] - CAPITAL) / CAPITAL * 100
        mo_dd = dd_per_month.get(mo, 0)
        print(f"  {mo:>8s} {ms['n']:>7d} {ms['w']:>6d} {wr:>4.0f}% {pf:>5.2f} ${ms['pnl']:>+9,.0f} ${ms['cap']:>11,.0f} {rend_cum:>+8.1f}% {mo_dd:>+7.2f}% {ms['max_dd']:>+6.2f}%")

    tot_n = sum(ms['n'] for ms in mo_stats.values())
    tot_w = sum(ms['w'] for ms in mo_stats.values())
    tot_gp = sum(ms['gp'] for ms in mo_stats.values())
    tot_gl = sum(ms['gl'] for ms in mo_stats.values())
    pm = sum(1 for ms in mo_stats.values() if ms['pnl'] > 0)

    print(f"  {'-'*85}")
    print(f"  Trades: {tot_n:,d} | WR: {tot_w/tot_n*100:.0f}% | PF: {tot_gp/(tot_gl+0.01):.2f} | Max DD: {max_dd:+.2f}% | Rend: {(cap-CAPITAL)/CAPITAL*100:+.1f}% | M+: {pm}/{len(sorted_months)}")
    print(f"  Capital: ${CAPITAL:,.0f} -> ${cap:,.0f} ({(cap-CAPITAL)/CAPITAL*100:+.1f}%)")

conn.close()
print(f"\n{'='*W}")
