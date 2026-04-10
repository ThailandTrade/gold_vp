"""
Audit: compare trades from bt_portfolio (pkl) vs compare_today (real-time detect_all + sim_exit).
Verifie que les deux chemins de code produisent les memes resultats.

Usage:
  python audit_bt_vs_compare.py 5ers                    # audit toutes les dates
  python audit_bt_vs_compare.py ftmo --date 2026-04-01  # un jour specifique
  python audit_bt_vs_compare.py 5ers --last 5           # 5 derniers jours
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, importlib, re, pickle
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from datetime import datetime, timezone, date
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import detect_all, compute_indicators, sim_exit_custom
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
               'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

parser = argparse.ArgumentParser()
parser.add_argument('account', choices=['icm','ftmo','5ers'])
parser.add_argument('--symbol', default='XAUUSD')
parser.add_argument('--date', default=None, help='YYYY-MM-DD specific date')
parser.add_argument('--last', type=int, default=5, help='Last N trading days')
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
sym = args.symbol.upper()
INSTRUMENTS = getattr(cfg, 'ALL_INSTRUMENTS', cfg.INSTRUMENTS)
if sym not in INSTRUMENTS:
    print(f"ERROR: {sym} not in config"); sys.exit(1)
portfolio = INSTRUMENTS[sym]['portfolio']
risk_pct = INSTRUMENTS[sym]['risk_pct']
sym_exits = STRAT_EXITS.get((args.account, sym), {})

# ── Load pkl trades ──
sym_san = re.sub(r"[^a-z0-9]+", "_", sym.lower()).strip("_")
pkl_file = f'data/{args.account}/{sym_san}/optim_data.pkl'
with open(pkl_file, 'rb') as f:
    pkl_data = pickle.load(f)
strat_arrays = pkl_data['strat_arrays']

# ── Load candles + ATR from DB ──
conn = get_conn()
candles = load_candles_5m(conn, symbol=sym.lower())
daily_atr, global_atr = compute_atr(conn, symbol=sym.lower())
trading_days = get_trading_days(conn, symbol=sym.lower())
conn.close()

candles = compute_indicators(candles)

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day:
            return trading_days[di-1] if di > 0 else None
    return None

# ── Determine dates to audit ──
if args.date:
    audit_dates = [date.fromisoformat(args.date)]
else:
    audit_dates = trading_days[-args.last:]

print(f"\n  AUDIT bt_portfolio vs compare_today — {args.account} {sym}")
print(f"  pkl: {pkl_file} ({len(strat_arrays)} strats)")
print(f"  Dates: {audit_dates[0]} -> {audit_dates[-1]} ({len(audit_dates)} jours)")
print()

# ── Build pkl trades by date ──
pkl_by_date = {}  # date -> [(strat, di, entry, exit, pnl, ei, xi)]
for sn in portfolio:
    if sn not in strat_arrays: continue
    for t in strat_arrays[sn]:
        ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = t
        if ei >= len(candles): continue
        d = candles.iloc[ei]['date']
        pkl_by_date.setdefault(d, []).append({
            'strat': sn, 'di': di, 'ei': ei, 'xi': xi,
            'entry': float(candles.iloc[ei]['close']),
            'pnl_oz': pnl_oz, 'sl_atr': sl_atr, 'atr_pkl': atr,
        })

# ── Run compare_today logic for each date ──
total_match = 0; total_mismatch = 0; total_missing = 0; total_extra = 0

for audit_day in audit_dates:
    # ATR for this day (prev trading day)
    pd_ = prev_day(audit_day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr

    # prev_day_data
    prev_day_data = None; prev2_day_data = None
    if pd_:
        yc = candles[candles['date'] == pd_]
        if len(yc) > 0:
            prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                             'high': float(yc['high'].max()), 'low': float(yc['low'].min()),
                             'range': float(yc['high'].max() - yc['low'].min())}
        pd2 = prev_day(pd_)
        if pd2:
            yc2 = candles[candles['date'] == pd2]
            if len(yc2) > 0:
                prev2_day_data = {'open': float(yc2.iloc[0]['open']), 'close': float(yc2.iloc[-1]['close']),
                                  'high': float(yc2['high'].max()), 'low': float(yc2['low'].min()),
                                  'range': float(yc2['high'].max() - yc2['low'].min())}

    # Detect signals for this day
    trig = {}; day_signals = []
    day_candles = candles[candles['date'] == audit_day]
    if len(day_candles) == 0: continue

    for ci in day_candles.index:
        row = candles.iloc[ci]
        ct = row['ts_dt']; hour = ct.hour + ct.minute / 60.0
        ds = pd.Timestamp(audit_day.year, audit_day.month, audit_day.day, 0, 0, tz='UTC')
        te = pd.Timestamp(audit_day.year, audit_day.month, audit_day.day, 6, 0, tz='UTC')
        ls = pd.Timestamp(audit_day.year, audit_day.month, audit_day.day, 8, 0, tz='UTC')
        ns = pd.Timestamp(audit_day.year, audit_day.month, audit_day.day, 14, 30, tz='UTC')
        tv = candles[(candles['ts_dt'] >= ds) & (candles['ts_dt'] <= ct)]
        tok = tv[tv['ts_dt'] < te]; lon = tv[(tv['ts_dt'] >= ls) & (tv['ts_dt'] < ns)]

        def add(sn, d_dir, e):
            if sn in portfolio:
                day_signals.append((ci, sn, d_dir, e))
        detect_all(candles, ci, row, ct, audit_day, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

    # Simulate exits with conflict filter
    day_signals.sort(key=lambda x: (x[0], x[1]))
    compare_trades = []
    active_pos = []
    for ci, sn, d_dir, entry in day_signals:
        is_open = sn in OPEN_STRATS
        exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
        etype = exit_cfg[0]; p1 = exit_cfg[1]; p2 = exit_cfg[2]
        p3 = exit_cfg[3] if len(exit_cfg) > 3 else 0
        b, ex = sim_exit_custom(candles, ci, entry, d_dir, atr, etype, p1, p2, p3, check_entry_candle=is_open)
        xi = ci + b
        di = 1 if d_dir == 'long' else -1
        # Conflict filter
        active_pos = [(axi, ad) for axi, ad in active_pos if axi >= ci]
        if any(ad != di for _, ad in active_pos):
            continue  # skipped by conflict
        active_pos.append((xi, di))
        pnl = (ex - entry) if d_dir == 'long' else (entry - ex)
        compare_trades.append({
            'strat': sn, 'di': di, 'ei': ci, 'xi': xi,
            'entry': entry, 'exit': ex, 'pnl': pnl, 'atr_compare': atr,
        })

    # ── Compare pkl vs compare for this day ──
    pkl_trades = pkl_by_date.get(audit_day, [])
    pkl_map = {}
    for t in pkl_trades:
        pkl_map.setdefault(t['strat'], []).append(t)
    cmp_map = {}
    for t in compare_trades:
        cmp_map.setdefault(t['strat'], []).append(t)

    day_issues = []
    all_strats = sorted(set(list(pkl_map.keys()) + list(cmp_map.keys())))
    for sn in all_strats:
        pt_list = pkl_map.get(sn, [])
        ct_list = cmp_map.get(sn, [])

        if not pt_list and ct_list:
            for ct in ct_list:
                day_issues.append(f"  EXTRA compare: {sn} di={ct['di']} ei={ct['ei']} entry={ct['entry']:.2f}")
                total_extra += 1
        elif pt_list and not ct_list:
            for pt in pt_list:
                day_issues.append(f"  MISSING compare: {sn} di={pt['di']} ei={pt['ei']} entry={pt['entry']:.2f}")
                total_missing += 1
        else:
            # Match by ei (bar index)
            for pt in pt_list:
                matched = [ct for ct in ct_list if ct['ei'] == pt['ei']]
                if not matched:
                    # Try closest ei
                    matched = [ct for ct in ct_list if abs(ct['ei'] - pt['ei']) <= 2]
                if not matched:
                    day_issues.append(f"  MISSING compare: {sn} di={pt['di']} ei={pt['ei']} entry={pt['entry']:.2f}")
                    total_missing += 1
                    continue
                ct = matched[0]
                # Compare
                issues = []
                if pt['di'] != ct['di']:
                    issues.append(f"DIR pkl={pt['di']} cmp={ct['di']}")
                entry_diff = abs(pt['entry'] - ct['entry'])
                if entry_diff > 0.01:
                    issues.append(f"ENTRY pkl={pt['entry']:.2f} cmp={ct['entry']:.2f} diff={entry_diff:.2f}")
                atr_diff = abs(pt['atr_pkl'] - ct['atr_compare'])
                if atr_diff > 0.01:
                    issues.append(f"ATR pkl={pt['atr_pkl']:.4f} cmp={ct['atr_compare']:.4f}")
                pnl_diff = abs(pt['pnl_oz'] - ct['pnl'])
                if pnl_diff > 0.1:
                    issues.append(f"PNL pkl={pt['pnl_oz']:.2f} cmp={ct['pnl']:.2f} diff={pnl_diff:.2f}")

                if issues:
                    day_issues.append(f"  MISMATCH {sn}: {' | '.join(issues)}")
                    total_mismatch += 1
                else:
                    total_match += 1

    if day_issues:
        print(f"  {audit_day} — {len(pkl_trades)} pkl / {len(compare_trades)} compare — {len(day_issues)} ISSUES:")
        for iss in day_issues:
            print(iss)
    else:
        print(f"  {audit_day} — {len(pkl_trades)} pkl / {len(compare_trades)} compare — OK ✓")

# ── Summary ──
print(f"\n  {'='*60}")
print(f"  MATCH: {total_match} | MISMATCH: {total_mismatch} | MISSING: {total_missing} | EXTRA: {total_extra}")
total = total_match + total_mismatch + total_missing + total_extra
if total > 0:
    print(f"  Taux de match: {total_match/total*100:.1f}%")
if total_mismatch + total_missing + total_extra == 0:
    print(f"  ✓ AUDIT OK — les deux chemins de code sont coherents")
else:
    print(f"  ✗ DIVERGENCES DETECTEES — a investiguer")
print(f"  {'='*60}")
