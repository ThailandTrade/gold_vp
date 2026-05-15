"""
Compare backtest vs live MT5 trades for today -- multi-instrument multi-TF.
Usage: python compare_today.py [ftmo|5ers|pepperstone] [--tf 15m]
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, importlib; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn
from strats import make_magic, decode_magic
from strat_exits import STRAT_EXITS, DEFAULT_EXIT
from backtest_engine import load_data_recent, collect_trades, OPEN_STRATS
from datetime import datetime, timezone, timedelta
from prettytable import PrettyTable
from config_helpers import iter_sym_tf

parser = argparse.ArgumentParser()
parser.add_argument('account', choices=['ftmo','5ers','pepperstone','exness','exness_standard'])
parser.add_argument('--tf', default=None, help='Filtre: un seul TF (sinon tous LIVE_TIMEFRAMES)')
parser.add_argument('--lookback-days', type=int, default=14,
                    help='Fenetre lookback pour catcher les trades fermes today entres avant (default 14)')
args = parser.parse_args()

# TF duration en minutes (pour aligner entry_time BT sur close de bougie = live fill time)
TF_DELTA_MIN = {'5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440}

def fmt_price(v):
    """Decimales adaptatives selon magnitude (FX 5, indices 2, etc.) -- aligne sur priceDecimals JS."""
    if v is None: return '-'
    a = abs(v)
    if a >= 1000: d = 2
    elif a >= 100: d = 3
    elif a >= 10: d = 4
    else: d = 5
    return f"{v:.{d}f}"

import os, json
cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER

UNITS = list(iter_sym_tf(cfg))
if args.tf:
    UNITS = [u for u in UNITS if u[1] == args.tf]
SYMBOLS = sorted({sym for sym, _, _ in UNITS})

with open(os.path.join(os.path.dirname(__file__), 'broker_offsets.json')) as f:
    _offsets = json.load(f)
BROKER_OFFSET = timedelta(hours=_offsets[args.account])


def _magic(symbol, strat, tf):
    return make_magic(args.account, symbol, strat, tf)

# magic -> (sym, tf, strat)
MAGIC_REVERSE = {}
for sym, tf, icfg in UNITS:
    for sn in icfg['portfolio']:
        MAGIC_REVERSE[_magic(sym, sn, tf)] = (sym, tf, sn)

# Date = derniere bougie en DB. Choisir un (sym, tf) reference.
_ref_sym = SYMBOLS[0] if SYMBOLS else 'XAUUSD'
_ref_tf = UNITS[0][1] if UNITS else '15m'
import re as _re
_ref_table = f"candles_mt5_{_re.sub(r'[^a-z0-9]+', '_', _ref_sym.lower()).strip('_')}_{_ref_tf}"
_conn_tmp = get_conn(); _conn_tmp.autocommit = True
_cur = _conn_tmp.cursor()
_cur.execute(f"SELECT MAX(ts) FROM {_ref_table}")
_max_ts = _cur.fetchone()[0]
_cur.close(); _conn_tmp.close()
today = datetime.fromtimestamp(_max_ts / 1000, tz=timezone.utc).date() if _max_ts else datetime.now(timezone.utc).date()
conn = get_conn(); conn.autocommit = True

print(f"\n  COMPARE BT vs LIVE -- {BROKER} -- {today} -- {len(UNITS)} units (sym,tf)")

# Live trades indexes par (sym, tf)
live_trades = {}  # (sym, tf) -> [trades]
live_open = {}    # (sym, tf) -> [positions]
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        from datetime import timedelta
        # Fenetre large pour catcher tous les deals dont exit_utc.date() == today
        # malgre BROKER_OFFSET et trades multi-jour
        from_date = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) - timedelta(days=2)
        to_date = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) + timedelta(days=2)

        # Closed deals today (filtre post-hoc par exit_utc.date() == today)
        deals = mt5.history_deals_get(from_date, to_date) or []
        pos_deals = {}
        for d in deals:
            if d.entry == 0 and d.type <= 1:
                pos_deals.setdefault(d.position_id, {'in': None, 'out': None, 'pnl': 0})
                pos_deals[d.position_id]['in'] = d
            elif d.entry == 1 and d.type <= 1:
                pos_deals.setdefault(d.position_id, {'in': None, 'out': None, 'pnl': 0})
                pos_deals[d.position_id]['out'] = d
                pos_deals[d.position_id]['pnl'] += d.profit

        for pid, td in pos_deals.items():
            if not td['in'] or not td['out']: continue
            din = td['in']; dout = td['out']
            # MT5 time est broker (UTC+offset) -- on convertit immediatement en UTC pur
            entry_broker = datetime.fromtimestamp(din.time, tz=timezone.utc)
            entry_utc = entry_broker - BROKER_OFFSET
            exit_broker = datetime.fromtimestamp(dout.time, tz=timezone.utc)
            exit_utc = exit_broker - BROKER_OFFSET
            # Filtre: trade FERME aujourd'hui (exit, pas entry)
            if exit_utc.date() != today: continue
            decoded = MAGIC_REVERSE.get(din.magic)
            if not decoded: continue
            sym, tf, sn = decoded
            d_dir = 'long' if din.type == 0 else 'short'
            live_trades.setdefault((sym, tf), []).append({
                'strat': sn, 'tf': tf, 'dir': d_dir,
                'entry': din.price, 'exit': dout.price,
                'pnl': td['pnl'],
                'entry_time': entry_utc,  # UTC pur
                'exit_time': exit_utc,
            })

        # Open positions
        for sym in SYMBOLS:
            positions = mt5.positions_get(symbol=sym) or []
            for p in positions:
                decoded = MAGIC_REVERSE.get(p.magic)
                if not decoded: continue
                s, tf, sn = decoded
                if s != sym: continue
                d_dir = 'long' if p.type == 0 else 'short'
                pos_broker = datetime.fromtimestamp(p.time, tz=timezone.utc)
                pos_utc = pos_broker - BROKER_OFFSET
                live_open.setdefault((sym, tf), []).append({
                    'strat': sn, 'tf': tf, 'dir': d_dir,
                    'entry': p.price_open, 'stop': p.sl, 'tp': p.tp,
                    'pnl': p.profit, 'lots': p.volume,
                    'time': pos_utc,  # UTC pur
                })

        mt5.shutdown()
    else:
        print("  MT5 non disponible — comparaison BT uniquement")
except ImportError:
    print("  MetaTrader5 non installe — comparaison BT uniquement")

# Per (sym, tf)
for sym, tf, icfg in UNITS:
    portfolio = icfg['portfolio']
    if not portfolio: continue
    sym_exits = STRAT_EXITS.get((args.account, sym, tf), {})

    candles, daily_atr, global_atr, trading_days = load_data_recent(conn, sym, n=5000, tf=tf)
    from backtest_engine import prev_trading_day
    pd_ = prev_trading_day(today, trading_days)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr

    entry_min_date = today - timedelta(days=args.lookback_days)
    raw_trades = collect_trades(candles, daily_atr, global_atr, trading_days,
                                portfolio, sym_exits, entry_min_date=entry_min_date, tf=tf)

    tf_delta = timedelta(minutes=TF_DELTA_MIN.get(tf, 60))
    bt_closed_today = []
    bt_open_today = []
    N = len(candles)
    for tup in raw_trades:
        ci, xi, di, pnl_oz, sl_atr, atr_t, mo, sn = tup[:8]
        d_dir = 'long' if di == 1 else 'short'
        entry = float(candles.iloc[ci]['close'])
        ex = entry + pnl_oz if di == 1 else entry - pnl_oz
        risk_1r = sl_atr * atr_t
        # Shift entry/exit time pour aligner sur close de bougie (= live fill time)
        entry_close = candles.iloc[ci]['ts_dt'] + tf_delta
        xi_safe = min(xi, N - 1)
        exit_close = candles.iloc[xi_safe]['ts_dt'] + tf_delta
        # Detect "ran out of data": xi atteint la derniere bougie ET pas le cap timeout 288
        # => trade pas vraiment ferme dans la simu, equivalent a une open position
        ran_out = (xi == N - 1) and (xi - ci < 288)
        t = {
            'strat': sn, 'tf': tf, 'dir': d_dir, 'entry': entry,
            'exit': ex if not ran_out else None,
            'pnl_pts': pnl_oz if not ran_out else None,
            'pnl_r': (pnl_oz / risk_1r) if (risk_1r > 0 and not ran_out) else None,
            'risk_1r': risk_1r, 'bars': xi - ci,
            'entry_time': str(entry_close),
            'exit_time': str(exit_close) if not ran_out else None,
            'skipped': None,
            'ran_out': ran_out,
        }
        # Split par etat aujourd'hui
        if ran_out:
            if entry_close.date() <= today:
                bt_open_today.append(t)
        elif exit_close.date() == today:
            bt_closed_today.append(t)
        elif entry_close.date() <= today and exit_close.date() > today:
            bt_open_today.append(t)
        # else: ferme avant today ou pas encore entre -- ignore

    bt_trades = bt_closed_today + bt_open_today
    lv = live_trades.get((sym, tf), [])
    lo = live_open.get((sym, tf), [])

    bt_active = bt_trades
    bt_skip = []

    if not bt_active and not bt_skip and not lv and not lo: continue

    print(f"\n  {sym} [{tf}] -- ATR={fmt_price(atr)} -- {len(portfolio)} strats")
    print(f"  BT: {len(bt_active)} trades ({len(bt_skip)} skipped) | Live: {len(lv)} closed + {len(lo)} open")

    # Match exact: (strat, dir, entry date + hour) -- evite faux match position-par-position
    def _date_hour(t):
        if hasattr(t, 'strftime'): return t.strftime('%Y-%m-%d %H')
        s = str(t)
        return s[:13]  # '2026-05-12 06'
    bt_buckets = {}
    for t in bt_trades:
        k = (t['strat'], t['dir'], _date_hour(t['entry_time']))
        bt_buckets.setdefault(k, []).append(t)
    lv_buckets = {}
    for t in lv:
        k = (t['strat'], t['dir'], _date_hour(t['entry_time']))
        lv_buckets.setdefault(k, []).append(t)
    lo_buckets = {}
    for p in lo:
        k = (p['strat'], p['dir'], _date_hour(p['time']))
        lo_buckets.setdefault(k, []).append(p)
    # Cle de tri: (strat, date_hour, dir)
    all_keys = sorted(set(bt_buckets) | set(lv_buckets) | set(lo_buckets),
                      key=lambda k: (k[0], k[2], k[1]))

    tbl = PrettyTable()
    tbl.field_names = ['Sym', 'TF', 'Strat', 'Exit', 'BT Dir', 'BT Entry', 'BT Exit', 'BT R', 'BT In', 'BT Out',
                       'LV Dir', 'LV Entry', 'LV Exit', 'LV R', 'LV In', 'LV Out',
                       'LV-BT', 'Verdict']
    tbl.align = 'r'
    tbl.align['Sym'] = 'l'
    tbl.align['TF'] = 'l'
    tbl.align['Strat'] = 'l'
    tbl.align['Verdict'] = 'l'

    bt_total_pts = 0; lv_total_pts = 0
    table_rows = []

    for key in all_keys:
        sn, _dir, _dh = key
        bts = bt_buckets.get(key, [])
        lvs = lv_buckets.get(key, [])
        los = lo_buckets.get(key, [])
        n_pairs = max(len(bts), len(lvs), len(los), 1) if (bts or lvs or los) else 0
        exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
        exit_type = exit_cfg[0]
        for idx in range(n_pairs):
            bt = bts[idx] if idx < len(bts) else None
            lv_t = lvs[idx] if idx < len(lvs) else None
            lo_t = los[idx] if idx < len(los) else None

            # Strat label: ajout suffix #idx si plusieurs trades dans le meme bucket
            sn_label = f"{sn}#{idx+1}" if n_pairs > 1 else sn

            # BT columns (MM-DD HH:MM pour distinguer jours avec lookback)
            if bt and bt['skipped']:
                bt_dir = 'SKIP'; bt_entry = fmt_price(bt['entry']); bt_exit = '-'; bt_pts = '-'
                bt_in = bt['entry_time'][5:16]; bt_out = '-'
            elif bt:
                bt_dir = bt['dir']; bt_entry = fmt_price(bt['entry'])
                # ran_out -> trade simu pas vraiment ferme, on cache l'exit
                bt_exit = fmt_price(bt['exit']) if bt.get('exit') is not None else 'OPEN'
                bt_pts = f"{bt['pnl_r']:+.2f}R" if bt.get('pnl_r') is not None else '...'
                if bt.get('pnl_r') is not None:
                    bt_total_pts += bt['pnl_r']
                bt_in = bt['entry_time'][5:16]
                bt_out = bt['exit_time'][5:16] if bt.get('exit_time') else '...'
            else:
                bt_dir = '-'; bt_entry = '-'; bt_exit = '-'; bt_pts = '-'; bt_in = '-'; bt_out = '-'

            lv_sort_key = '99-99 99:99'
            if lv_t:
                lv_dir = lv_t['dir']; lv_entry = fmt_price(lv_t['entry']); lv_exit = fmt_price(lv_t['exit'])
                lv_pnl_pts = (lv_t['exit'] - lv_t['entry']) if lv_t['dir'] == 'long' else (lv_t['entry'] - lv_t['exit'])
                risk_1r = bt['risk_1r'] if bt and not bt['skipped'] else 3.0 * atr
                lv_pnl_r = lv_pnl_pts / risk_1r if risk_1r > 0 else 0
                lv_pts = f"{lv_pnl_r:+.2f}R"
                lv_total_pts += lv_pnl_r
                # entry_time/exit_time deja en UTC (converti a la lecture MT5)
                lv_in = lv_t['entry_time'].strftime('%m-%d %H:%M') if hasattr(lv_t['entry_time'], 'strftime') else str(lv_t['entry_time'])[5:16]
                lv_out = lv_t['exit_time'].strftime('%m-%d %H:%M') if hasattr(lv_t['exit_time'], 'strftime') else str(lv_t['exit_time'])[5:16]
                lv_sort_key = lv_in
            elif lo_t:
                lv_dir = lo_t['dir']; lv_entry = fmt_price(lo_t['entry']); lv_exit = 'OPEN'
                lv_pts = '...'
                lv_in = lo_t['time'].strftime('%m-%d %H:%M') if hasattr(lo_t['time'], 'strftime') else str(lo_t['time'])[5:16]
                lv_out = '...'
                lv_sort_key = lv_in
            else:
                lv_dir = '-'; lv_entry = '-'; lv_exit = '-'; lv_pts = '-'; lv_in = '-'; lv_out = '-'

            lv_bt_diff = '-'
            if bt and not bt['skipped'] and lv_t and bt.get('pnl_r') is not None:
                lv_pnl = (lv_t['exit'] - lv_t['entry']) if lv_t['dir'] == 'long' else (lv_t['entry'] - lv_t['exit'])
                risk_1r_d = bt['risk_1r'] if bt['risk_1r'] > 0 else 1
                lv_bt_diff = f"{(lv_pnl / risk_1r_d) - bt['pnl_r']:+.2f}R"

            if bt and not bt['skipped'] and (lv_t or lo_t):
                lv_d = lv_t['dir'] if lv_t else lo_t['dir']
                lv_e = lv_t['entry'] if lv_t else lo_t['entry']
                if bt['dir'] != lv_d:
                    verdict = 'DIR MISMATCH!'
                else:
                    entry_diff = abs(bt['entry'] - lv_e)
                    if entry_diff < 0.5: verdict = ''
                    elif entry_diff < 2.0: verdict = ''
                    else: verdict = f'!! ENTRY DIFF {fmt_price(entry_diff)}'
            elif bt and bt['skipped'] and (lv_t or lo_t):
                verdict = '!! BT=SKIP LV=PRIS'
            elif bt and not bt['skipped'] and not lv_t and not lo_t:
                verdict = '!! BT ONLY'
            elif not bt and (lv_t or lo_t):
                verdict = '!! LV ONLY'
            elif bt and bt['skipped'] and not lv_t and not lo_t:
                verdict = ''
            else:
                verdict = '?'

            table_rows.append((lv_sort_key, [sym, tf, sn_label, exit_type, bt_dir, bt_entry, bt_exit, bt_pts, bt_in, bt_out,
                         lv_dir, lv_entry, lv_exit, lv_pts, lv_in, lv_out,
                         lv_bt_diff, verdict]))

    # Tri par heure d'entree live
    for _, row in sorted(table_rows, key=lambda x: x[0]):
        tbl.add_row(row)

    print(tbl)
    print(f"  TOTAL:  BT {bt_total_pts:+.2f}R  |  LV {lv_total_pts:+.2f}R")

conn.close()
