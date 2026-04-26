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
parser.add_argument('--spread', action='store_true', help='Modelise le spread (-0.1R par trade, legacy)')
parser.add_argument('--cost-r', type=float, default=0.0, help='Penalite R par trade (ex: 0.05 pour modeliser spread+slippage)')
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = getattr(cfg, 'ALL_INSTRUMENTS', cfg.INSTRUMENTS)

CRYPTO_BASES = ('BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOT', 'AVAX',
                'LINK', 'MATIC', 'DOGE', 'LTC', 'BCH', 'TRX', 'ATOM', 'SHIB',
                'NEAR', 'UNI', 'XLM', 'APT', 'ARB', 'OP', 'INJ', 'SUI')


def is_crypto(sym):
    return sym.upper().startswith(CRYPTO_BASES)


def crosses_weekend(entry_ts, exit_ts):
    from datetime import timedelta as _td
    d = entry_ts.date(); end = exit_ts.date()
    while d <= end:
        if d.weekday() >= 5:
            return True
        d += _td(days=1)
    return False

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
# Cost effective: --cost-r prioritaire si >0, sinon --spread (0.1R legacy), sinon 0
COST_R = args.cost_r if args.cost_r > 0 else (0.1 if args.spread else 0.0)
cost_tag = f' — COST -{COST_R}R/trade' if COST_R > 0 else ''
print(f"  BACKTEST {BROKER} — ${CAPITAL:,.0f} — {'hebdo' if args.weekly else 'mensuel'}{cost_tag}")
print(f"{'='*W}")

conn = get_conn()

all_sym_trades = []
candles_by_sym = {}

for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    risk = args.risk / 100 if args.risk else icfg['risk_pct']
    if not portfolio:
        print(f"\n  {sym}: portfolio vide"); continue

    sym_exits = STRAT_EXITS.get((args.account, sym), {})

    print(f"\n  Loading {sym}...", end='', flush=True)
    candles, daily_atr, global_atr, trading_days = load_data(conn, sym, tf=args.tf)
    print(f" {len(candles)} bars, {len(trading_days)} days", flush=True)
    candles_by_sym[sym] = candles

    trades = collect_trades(candles, daily_atr, global_atr, trading_days, portfolio, sym_exits)
    r = eval_portfolio(trades, risk, CAPITAL, spread=(COST_R > 0), cost_r=COST_R)
    if not r:
        print(f"  {sym}: 0 trades"); continue

    print(f"  {'-'*W}")
    print(f"  {sym} — {len(portfolio)} strats @ {risk*100:.2f}%")
    print(f"  Trades: {r['n']:,d}  PF: {r['pf']:.2f}  WR: {r['wr']:.0f}%  DD: {r['mdd']:+.1f}%  Rend: {r['ret']:+,.0f}%  M+: {r['pm']}/{r['tm']}")

    durations_h = []
    multi_day = 0
    weekend_cross = 0
    sym_is_crypto = is_crypto(sym)
    for ci, xi, *_ in trades:
        xi_safe = min(xi, len(candles) - 1)
        ets = candles.iloc[ci]['ts_dt']
        xts = candles.iloc[xi_safe]['ts_dt']
        dur_h = (xts - ets).total_seconds() / 3600
        durations_h.append(dur_h)
        if dur_h >= 24: multi_day += 1
        if not sym_is_crypto and crosses_weekend(ets, xts):
            weekend_cross += 1
    avg_dur = sum(durations_h) / len(durations_h) if durations_h else 0
    md_pct = multi_day / len(trades) * 100 if trades else 0
    line = f"  Duree avg: {avg_dur:.1f}h  Multi-day (>=24h): {multi_day} ({md_pct:.1f}%)"
    if not sym_is_crypto:
        wk_pct = weekend_cross / len(trades) * 100 if trades else 0
        line += f"  Weekend cross: {weekend_cross} ({wk_pct:.1f}%)"
    print(line)

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
if len(all_sym_trades) >= 1:
    print(f"\n{'='*W}")
    print(f"  AGREGE — {len(all_sym_trades)} instruments — ${CAPITAL:,.0f}")
    print(f"{'='*W}")

    # Convertit ei/xi (indices DataFrame par sym) en timestamps reels.
    # Indispensable: chaque sym a son propre DataFrame avec longueur differente,
    # donc trier sur les indices melange la chronologie globale.
    from datetime import timedelta
    filtered = []
    for st in all_sym_trades:
        sym = st['sym']
        cd = candles_by_sym[sym]
        n_bars = len(cd)
        for t in st['accepted']:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, sn = t
            xi_safe = min(xi, n_bars - 1)
            entry_ts = cd.iloc[ei]['ts_dt']
            exit_ts = cd.iloc[xi_safe]['ts_dt']
            filtered.append((entry_ts, exit_ts, di, pnl_oz, sl_atr, atr, sn, st['risk'], sym))

    events = [(t[0], 0, idx) for idx, t in enumerate(filtered)] + \
             [(t[1], 1, idx) for idx, t in enumerate(filtered)]
    events.sort()

    cap = CAPITAL; peak = cap; max_dd = 0
    entry_caps = {}; period_stats = {}; dd_per_period = {}

    for ts, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            entry_ts, exit_ts, di, pnl_oz, sl_atr, atr, sn, risk, sym = filtered[idx]
            if COST_R > 0:
                pnl_oz -= COST_R * sl_atr * atr
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak * 100
            if dd < max_dd: max_dd = dd

            # Period bucket base sur exit_ts: ps['cap'] est ainsi cap au dernier
            # exit du calendaire, coherent avec PnL agrege du calendaire.
            if args.weekly:
                period = (exit_ts - timedelta(days=exit_ts.weekday())).strftime('%Y-%m-%d')
            else:
                period = exit_ts.strftime('%Y-%m')

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

    from prettytable import PrettyTable
    tbl = PrettyTable()
    tbl.field_names = [label, 'Trades', 'Wins', 'WR', 'PF', 'PnL', 'Rend P', 'Capital', 'Rend', 'DD', 'MaxDD']
    tbl.align = 'r'
    tbl.align[label] = 'l'
    prev_cap = CAPITAL
    for p in sorted_periods:
        ps = period_stats[p]
        wr = ps['w'] / ps['n'] * 100 if ps['n'] > 0 else 0
        pf = ps['gp'] / (ps['gl'] + 0.01)
        rend = (ps['cap'] - CAPITAL) / CAPITAL * 100
        rend_period = (ps['cap'] - prev_cap) / prev_cap * 100 if prev_cap > 0 else 0
        prev_cap = ps['cap']
        p_dd = dd_per_period.get(p, 0)
        tbl.add_row([p, f"{ps['n']:,d}", ps['w'], f"{wr:.0f}%", f"{pf:.2f}",
                     f"${ps['pnl']:+,.0f}", f"{rend_period:+.2f}%",
                     f"${ps['cap']:,.0f}", f"{rend:+.1f}%",
                     f"{p_dd:+.2f}%", f"{ps['max_dd']:+.2f}%"])
    print()
    print(tbl)

    tot_n = sum(ps['n'] for ps in period_stats.values())
    tot_w = sum(ps['w'] for ps in period_stats.values())
    tot_gp = sum(ps['gp'] for ps in period_stats.values())
    tot_gl = sum(ps['gl'] for ps in period_stats.values())
    pos_periods = sum(1 for ps in period_stats.values() if ps['pnl'] > 0)
    neg_periods = len(sorted_periods) - pos_periods

    total_durations_h = []
    total_multi_day = 0
    weekend_cross_total = 0
    non_crypto_n = 0
    for entry_ts, exit_ts, di, pnl_oz, sl_atr, atr, sn, risk, sym in filtered:
        dh = (exit_ts - entry_ts).total_seconds() / 3600
        total_durations_h.append(dh)
        if dh >= 24: total_multi_day += 1
        if not is_crypto(sym):
            non_crypto_n += 1
            if crosses_weekend(entry_ts, exit_ts):
                weekend_cross_total += 1
    avg_dur_total = sum(total_durations_h) / len(total_durations_h) if total_durations_h else 0
    md_pct_total = total_multi_day / len(filtered) * 100 if filtered else 0
    wk_pct_total = weekend_cross_total / non_crypto_n * 100 if non_crypto_n else 0

    print(f"\n  TOTAL: Trades {tot_n:,d}  WR {tot_w/tot_n*100:.0f}%  PF {tot_gp/(tot_gl+0.01):.2f}  MaxDD {max_dd:+.2f}%  Rend {(cap-CAPITAL)/CAPITAL*100:+.1f}%")
    print(f"  Duree avg: {avg_dur_total:.1f}h  Multi-day (>=24h): {total_multi_day} ({md_pct_total:.1f}%)  Weekend cross (non-crypto): {weekend_cross_total}/{non_crypto_n} ({wk_pct_total:.1f}%)")
    print(f"  {label}+ {pos_periods}/{len(sorted_periods)}  {label}- {neg_periods}/{len(sorted_periods)}")
    print(f"  ${CAPITAL:,.0f} -> ${cap:,.0f}")

conn.close()
print(f"\n{'='*W}")
