"""
Backtest complet crypto — multi-instrument AVEC FRAIS HYPERLIQUID.
Derive de bt_portfolio.py, dedie crypto uniquement (zero impact 5ers/ftmo/icm).

Frais Hyperliquid standard (pas de discount):
  - Entry: Taker market 0.045%
  - Exit : Maker limit (SL/TP) 0.015%
  - Round-trip: 0.060% du notional par trade

Usage:
  python bt_portfolio_crypto.py                    # tous instruments
  python bt_portfolio_crypto.py --symbol BTCUSD    # un seul
  python bt_portfolio_crypto.py -c 100000          # avec capital
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd, pickle, importlib, re
from phase1_poc_calculator import get_conn
from crypto_data import load_candles_hl

# Frais Hyperliquid
FEE_TAKER = 0.00045  # 0.045% entry (market order)
FEE_MAKER = 0.00015  # 0.015% exit  (limit SL/TP)

parser = argparse.ArgumentParser(description='Backtest crypto portfolio avec frais HL')
parser.add_argument('-c', '--capital', type=float, default=None)
parser.add_argument('-r', '--risk', type=float, default=None)
parser.add_argument('--symbol', default=None, help='Single instrument (default: all)')
args = parser.parse_args()

cfg = importlib.import_module('config_crypto')
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

# ── Load candles for each symbol once ──
print("Loading candles for fee computation...", flush=True)
conn = get_conn()
SYMBOL_CLOSES = {}  # sym -> np.array of close prices indexed by bar
for sym in INSTRUMENTS.keys():
    candles = load_candles_hl(conn, symbol=sym.lower())
    SYMBOL_CLOSES[sym] = candles['close'].values.astype(np.float64)
    print(f"  {sym}: {len(candles)} candles loaded (15m)")
conn.close()

def eval_combo(strat_arrays, portfolio, risk, sym):
    closes = SYMBOL_CLOSES[sym]
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
    month_detail = {}
    tot_fees = 0.0
    for bar, evt, idx in events:
        if evt == 0: entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = accepted[idx]
            size_usd_risk = entry_caps[idx] * risk  # USD risked
            # size_units = size_usd_risk / (sl_atr * atr)
            # notional_entry = size_units * entry_price
            entry_price = closes[ei]
            exit_price = closes[xi]
            size_units = size_usd_risk / (sl_atr * atr)
            notional_entry = size_units * entry_price
            notional_exit = size_units * exit_price
            fee_entry = FEE_TAKER * notional_entry
            fee_exit = FEE_MAKER * notional_exit
            fee = fee_entry + fee_exit
            pnl_gross = pnl_oz * size_units
            pnl = pnl_gross - fee
            tot_fees += fee
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
            'accepted': accepted, 'tot_fees': tot_fees}

# ── RUN ──
W = 90
print(f"\n{'='*W}")
print(f"  BACKTEST {BROKER} avec frais HL — ${CAPITAL:,.0f}")
print(f"  Taker entry {FEE_TAKER*100:.3f}% | Maker exit {FEE_MAKER*100:.3f}% | Round-trip {(FEE_TAKER+FEE_MAKER)*100:.3f}%")
print(f"{'='*W}")

all_sym_trades = []
for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    risk = args.risk / 100 if args.risk else icfg['risk_pct']
    if not portfolio:
        print(f"\n  {sym}: portfolio vide"); continue

    sym_san = re.sub(r"[^a-z0-9]+", "_", sym.lower()).strip("_")
    pkl_file = f'data/crypto/{sym_san}/optim_data.pkl'
    try:
        with open(pkl_file, 'rb') as f:
            data = pickle.load(f)
        strat_arrays = data['strat_arrays']
    except FileNotFoundError:
        print(f"\n  {sym}: {pkl_file} not found"); continue

    missing = [s for s in portfolio if s not in strat_arrays]
    if missing:
        print(f"\n  {sym}: WARNING strats missing: {missing}")

    r = eval_combo(strat_arrays, portfolio, risk, sym)
    if not r:
        print(f"\n  {sym}: 0 trades"); continue

    print(f"\n{'-'*W}")
    print(f"  {sym} — {len(portfolio)} strats @ {risk*100:.2f}%")
    print(f"{'-'*W}")
    print(f"  Trades: {r['n']:,d} | PF: {r['pf']:.2f} | WR: {r['wr']:.0f}% | DD: {r['mdd']:+.1f}% | Rend: {r['ret']:+,.0f}% | M+: {r['pm']}/{r['tm']}")
    print(f"  Capital: ${r['capital']:,.0f}  |  Fees cumules: ${r['tot_fees']:,.0f}")

    print(f"\n  {'Strat':>22s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'PnL':>10s}")
    for sn in portfolio:
        ss = r['strat_stats'].get(sn, {'n':0,'w':0,'gp':0,'gl':0})
        if ss['n'] > 0:
            pf = ss['gp']/(ss['gl']+0.01)
            wr = ss['w']/ss['n']*100
            pnl = ss['gp'] - ss['gl']
            print(f"  {sn:>22s} {ss['n']:>5d} {wr:>4.0f}% {pf:>5.2f} ${pnl:>+9,.0f}")

    all_sym_trades.append({'sym': sym, 'accepted': r['accepted'], 'risk': risk})

# ── AGGREGATE ──
if len(all_sym_trades) > 1:
    print(f"\n{'='*W}")
    print(f"  AGREGE — {len(all_sym_trades)} instruments — compte unique ${CAPITAL:,.0f}")
    print(f"{'='*W}")

    filtered = []
    for st in all_sym_trades:
        for t in st['accepted']:
            filtered.append((*t, st['risk'], st['sym']))

    events = [(ei, 0, idx) for idx, (ei,*_) in enumerate(filtered)] + \
             [(xi, 1, idx) for idx, (_,xi,*__) in enumerate(filtered)]
    events.sort()

    cap = CAPITAL; peak = cap; max_dd = 0
    entry_caps = {}
    mo_stats = {}
    dd_per_month = {}
    tot_fees_agg = 0.0

    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, sn, risk, sym = filtered[idx]
            closes = SYMBOL_CLOSES[sym]
            size_usd_risk = entry_caps[idx] * risk
            size_units = size_usd_risk / (sl_atr * atr)
            entry_price = closes[ei]
            exit_price = closes[xi]
            notional_entry = size_units * entry_price
            notional_exit = size_units * exit_price
            fee = FEE_TAKER * notional_entry + FEE_MAKER * notional_exit
            pnl = pnl_oz * size_units - fee
            tot_fees_agg += fee
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak * 100
            if dd < max_dd: max_dd = dd

            if mo not in dd_per_month or dd < dd_per_month[mo]:
                dd_per_month[mo] = dd

            ms = mo_stats.setdefault(mo, {'n':0,'w':0,'gp':0,'gl':0,'pnl':0})
            ms['n'] += 1
            if pnl > 0: ms['w'] += 1; ms['gp'] += pnl
            else: ms['gl'] += abs(pnl)
            ms['pnl'] += pnl
            ms['cap'] = cap
            ms['peak'] = peak
            ms['max_dd'] = max_dd

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
    print(f"  Fees totaux: ${tot_fees_agg:,.0f}")

print(f"\n{'='*W}")
