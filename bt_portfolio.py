"""
Backtest complet — multi-instrument.
Utilise backtest_engine.py (moteur unique, meme code que compare_today et live).

Usage:
  python bt_portfolio.py ftmo                       → tous instruments, mensuel
  python bt_portfolio.py ftmo --weekly              → tous instruments, hebdo
  python bt_portfolio.py icm --symbol XAUUSD        → un seul instrument
  python bt_portfolio.py icm -c 50000 -r 0.5        → capital + risk custom
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
parser.add_argument('--weekly', action='store_true', help='Affichage hebdomadaire au lieu de mensuel')
parser.add_argument('--spread', action='store_true', help='Modelise le spread (-0.1R par trade)')
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
W = 100

print(f"\n{'='*W}")
spread_tag = ' — SPREAD -0.1R' if args.spread else ''
print(f"  BACKTEST {BROKER} — ${CAPITAL:,.0f} — {'hebdo' if args.weekly else 'mensuel'}{spread_tag}")
print(f"{'='*W}")

conn = get_conn()

# ── Load reference candles (for weekly date mapping) ──
ref_candles = None

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

    if ref_candles is None or len(candles) > len(ref_candles):
        ref_candles = candles

    trades = collect_trades(candles, daily_atr, global_atr, trading_days, portfolio, sym_exits)
    r = eval_portfolio(trades, risk, CAPITAL, spread=args.spread)
    if not r:
        print(f"  {sym}: 0 trades"); continue

    print(f"  {'-'*W}")
    print(f"  {sym} — {len(portfolio)} strats @ {risk*100:.2f}%")
    print(f"  Trades: {r['n']:,d}  PF: {r['pf']:.2f}  WR: {r['wr']:.0f}%  DD: {r['mdd']:+.1f}%  Rend: {r['ret']:+,.0f}%  M+: {r['pm']}/{r['tm']}")

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
    print(f"  AGREGE — {len(all_sym_trades)} instruments — ${CAPITAL:,.0f}")
    print(f"{'='*W}")

    filtered = []
    for st in all_sym_trades:
        for t in st['accepted']:
            filtered.append((*t, st['risk'], st['sym']))

    events = [(ei, 0, idx) for idx, (ei, *_) in enumerate(filtered)] + \
             [(xi, 1, idx) for idx, (_, xi, *__) in enumerate(filtered)]
    events.sort()

    cap = CAPITAL; peak = cap; max_dd = 0
    entry_caps = {}; period_stats = {}; dd_per_period = {}

    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, sn, risk, sym = filtered[idx]
            if args.spread:
                pnl_oz -= 0.1 * sl_atr * atr  # -0.1R par trade (spread)
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak * 100
            if dd < max_dd: max_dd = dd

            # Period key: semaine (lundi) si --weekly, sinon mois
            if args.weekly and ref_candles is not None and xi < len(ref_candles):
                from datetime import timedelta
                ts = ref_candles.iloc[xi]['ts_dt']
                period = (ts - timedelta(days=ts.weekday())).strftime('%Y-%m-%d')
            else:
                period = mo

            if period not in dd_per_period or dd < dd_per_period[period]:
                dd_per_period[period] = dd
            ps = period_stats.setdefault(period, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0, 'pnl': 0})
            ps['n'] += 1
            if pnl > 0: ps['w'] += 1; ps['gp'] += pnl
            else: ps['gl'] += abs(pnl)
            ps['pnl'] += pnl
            ps['cap'] = cap; ps['peak'] = peak; ps['max_dd'] = max_dd

    sorted_periods = sorted(period_stats.keys())
    label = 'Semaine' if args.weekly else 'Mois'

    print(f"\n  {label:>10s}  {'Trades':>6s}  {'Wins':>5s}  {'WR':>5s}  {'PF':>5s}  {'PnL':>10s}  {'Capital':>12s}  {'Rend':>8s}  {'DD':>7s}  {'MaxDD':>7s}")
    print(f"  {'-'*92}")
    for p in sorted_periods:
        ps = period_stats[p]
        wr = ps['w'] / ps['n'] * 100 if ps['n'] > 0 else 0
        pf = ps['gp'] / (ps['gl'] + 0.01)
        rend = (ps['cap'] - CAPITAL) / CAPITAL * 100
        p_dd = dd_per_period.get(p, 0)
        pnl_sign = '+' if ps['pnl'] >= 0 else ''
        print(f"  {p:>10s}  {ps['n']:>6d}  {ps['w']:>5d}  {wr:>4.0f}%  {pf:>4.1f}  ${ps['pnl']:>+9,.0f}  ${ps['cap']:>11,.0f}  {rend:>+7.1f}%  {p_dd:>+6.2f}%  {ps['max_dd']:>+6.2f}%")

    tot_n = sum(ps['n'] for ps in period_stats.values())
    tot_w = sum(ps['w'] for ps in period_stats.values())
    tot_gp = sum(ps['gp'] for ps in period_stats.values())
    tot_gl = sum(ps['gl'] for ps in period_stats.values())
    pos_periods = sum(1 for ps in period_stats.values() if ps['pnl'] > 0)
    neg_periods = len(sorted_periods) - pos_periods

    print(f"  {'-'*92}")
    print(f"  Trades: {tot_n:,d}  WR: {tot_w/tot_n*100:.0f}%  PF: {tot_gp/(tot_gl+0.01):.2f}  MaxDD: {max_dd:+.2f}%  Rend: {(cap-CAPITAL)/CAPITAL*100:+.1f}%")
    print(f"  {label}+ {pos_periods}/{len(sorted_periods)}  {label}- {neg_periods}/{len(sorted_periods)}")
    print(f"  ${CAPITAL:,.0f} -> ${cap:,.0f}")

conn.close()
print(f"\n{'='*W}")
