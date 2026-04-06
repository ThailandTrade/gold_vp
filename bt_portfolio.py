"""
Backtest complet — multi-instrument — TEMPS REEL depuis DB.
Pas de pkl: detecte les signaux et simule les exits en temps reel,
exactement comme compare_today.py et live_mt5.py.

Usage:
  python bt_portfolio.py 5ers                    → tous instruments
  python bt_portfolio.py 5ers --symbol XAUUSD    → un seul instrument
  python bt_portfolio.py icm -c 100000           → avec capital
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, re, importlib
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import detect_all, compute_indicators, sim_exit_custom
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
               'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

parser = argparse.ArgumentParser(description='Backtest portfolio (temps reel)')
parser.add_argument('account', nargs='?', default='icm', choices=['icm','ftmo','5ers'])
parser.add_argument('-c', '--capital', type=float, default=None)
parser.add_argument('-r', '--risk', type=float, default=None)
parser.add_argument('--symbol', default=None, help='Single instrument (default: all)')
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


def collect_trades(candles, daily_atr, global_atr, trading_days, portfolio, sym_exits):
    """Detecte tous les signaux + simule les exits en temps reel. Meme code que compare_today/live."""

    def prev_day(day):
        for di, d in enumerate(trading_days):
            if d >= day:
                return trading_days[di-1] if di > 0 else None
        return None

    # Signaux bruts
    signals = []  # (ci, sn, d_dir, entry)
    prev_d = None; trig = {}; day_atr = None
    prev_day_data = None; prev2_day_data = None

    for ci in range(200, len(candles)):
        row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
        hour = ct.hour + ct.minute / 60.0
        if today != prev_d:
            if prev_d:
                yc = candles[candles['date'] == prev_d]
                if len(yc) > 0:
                    prev2_day_data = prev_day_data
                    prev_day_data = {
                        'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                        'high': float(yc['high'].max()), 'low': float(yc['low'].min()),
                        'range': float(yc['high'].max() - yc['low'].min()),
                        'body': float(yc.iloc[-1]['close'] - yc.iloc[0]['open']),
                    }
            prev_d = today; trig = {}
            pd_ = prev_day(today)
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
            if sn in portfolio:
                signals.append((ci, sn, d_dir, e, atr, today))
        detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig, prev2_day_data)

    # Simulate exits + conflict filter
    signals.sort(key=lambda x: (x[0], x[1]))
    trades = []  # (ei, xi, di, pnl_oz, sl_atr, atr, mo, sn)
    active_pos = []

    for ci, sn, d_dir, entry, atr, today in signals:
        is_open = sn in OPEN_STRATS
        exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
        etype = exit_cfg[0]; p1 = exit_cfg[1]; p2 = exit_cfg[2]
        p3 = exit_cfg[3] if len(exit_cfg) > 3 else 0
        b, ex = sim_exit_custom(candles, ci, entry, d_dir, atr, etype, p1, p2, p3, check_entry_candle=is_open)
        xi = ci + b
        di = 1 if d_dir == 'long' else -1
        pnl_oz = (ex - entry) if d_dir == 'long' else (entry - ex)
        mo = f"{today.year}-{str(today.month).zfill(2)}"

        # Conflict filter (identique a eval_combo)
        active_pos = [(axi, ad) for axi, ad in active_pos if axi >= ci]
        if any(ad != di for _, ad in active_pos):
            continue
        active_pos.append((xi, di))
        trades.append((ci, xi, di, pnl_oz, p1, atr, mo, sn))

    return trades


def eval_trades(trades, risk):
    """Evalue un portefeuille de trades (event-based, identique a l'ancien eval_combo)."""
    if not trades: return None
    n = len(trades)
    events = [(ei, 0, idx) for idx, (ei, *_) in enumerate(trades)] + \
             [(xi, 1, idx) for idx, (_, xi, *__) in enumerate(trades)]
    events.sort()
    cap = CAPITAL; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0
    months = {}; entry_caps = {}; strat_stats = {}
    month_detail = {}
    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = trades[idx]
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak
            if dd < max_dd: max_dd = dd
            if pnl > 0: gp += pnl; wins += 1
            else: gl += abs(pnl)
            months[mo] = months.get(mo, 0.0) + pnl
            md = month_detail.setdefault(mo, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
            md['n'] += 1
            if pnl > 0: md['w'] += 1; md['gp'] += pnl
            else: md['gl'] += abs(pnl)
            month_detail[mo]['cap'] = cap
            month_detail[mo]['peak'] = peak
            month_detail[mo]['dd'] = max_dd
            ss = strat_stats.setdefault(_sn, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
            ss['n'] += 1
            if pnl > 0: ss['w'] += 1; ss['gp'] += pnl
            else: ss['gl'] += abs(pnl)
    pm = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'mdd': max_dd * 100,
            'ret': (cap - CAPITAL) / CAPITAL * 100, 'capital': cap, 'pm': pm, 'tm': len(months),
            'months': months, 'strat_stats': strat_stats, 'month_detail': month_detail,
            'accepted': trades}


# ── RUN ──
W = 90
print(f"\n{'='*W}")
print(f"  BACKTEST {BROKER} — ${CAPITAL:,.0f} (temps reel, pas de pkl)")
print(f"{'='*W}")

conn = get_conn()
all_sym_trades = []

for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    risk = args.risk / 100 if args.risk else icfg['risk_pct']
    if not portfolio:
        print(f"\n  {sym}: portfolio vide"); continue

    sym_exits = STRAT_EXITS.get((args.account, sym), {})
    missing_exits = [s for s in portfolio if s not in sym_exits]
    if missing_exits:
        print(f"\n  {sym}: WARNING strats sans exit config: {missing_exits}")

    # Load data from DB
    print(f"\n  Loading {sym}...", end='', flush=True)
    candles = load_candles_5m(conn, symbol=sym.lower())
    daily_atr, global_atr = compute_atr(conn, symbol=sym.lower())
    trading_days = get_trading_days(conn, symbol=sym.lower())
    candles = compute_indicators(candles)
    print(f" {len(candles)} bars, {len(trading_days)} days", flush=True)

    # Collect trades
    trades = collect_trades(candles, daily_atr, global_atr, trading_days, portfolio, sym_exits)
    r = eval_trades(trades, risk)
    if not r:
        print(f"  {sym}: 0 trades"); continue

    print(f"{'-'*W}")
    print(f"  {sym} — {len(portfolio)} strats @ {risk*100:.2f}%")
    print(f"{'-'*W}")
    print(f"  Trades: {r['n']:,d} | PF: {r['pf']:.2f} | WR: {r['wr']:.0f}% | DD: {r['mdd']:+.1f}% | Rend: {r['ret']:+,.0f}% | M+: {r['pm']}/{r['tm']}")
    print(f"  Capital: ${r['capital']:,.0f}")

    # Per strat
    print(f"\n  {'Strat':>22s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'PnL':>10s}")
    for sn in portfolio:
        ss = r['strat_stats'].get(sn, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
        if ss['n'] > 0:
            pf = ss['gp'] / (ss['gl'] + 0.01)
            wr = ss['w'] / ss['n'] * 100
            pnl = ss['gp'] - ss['gl']
            print(f"  {sn:>22s} {ss['n']:>5d} {wr:>4.0f}% {pf:>5.2f} ${pnl:>+9,.0f}")

    # Per month
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
    entry_caps = {}
    mo_stats = {}
    dd_per_month = {}

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
