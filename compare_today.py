"""
Compare backtest vs live MT5 trades for today — multi-instrument.
Usage: python compare_today.py [icm|ftmo|5ers]
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, importlib; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn
from strats import make_magic
from strat_exits import STRAT_EXITS, DEFAULT_EXIT
from backtest_engine import load_data_recent, collect_trades, OPEN_STRATS
from datetime import datetime, timezone, timedelta
from prettytable import PrettyTable

parser = argparse.ArgumentParser()
parser.add_argument('account', nargs='?', default='5ers', choices=['icm','ftmo','5ers'])
parser.add_argument('--tf', default='5m', help='Timeframe: 5m or 15m')
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = cfg.INSTRUMENTS

# OPEN_STRATS importe depuis backtest_engine (source unique)

def _magic(symbol, strat):
    return make_magic(args.account, symbol, strat)

MAGIC_REVERSE = {}
for sym, icfg in INSTRUMENTS.items():
    for sn in icfg['portfolio']:
        MAGIC_REVERSE[_magic(sym, sn)] = (sym, sn)

# Date = derniere bougie en DB (pas l'horloge systeme — regle UTC candles)
_conn_tmp = get_conn(); _conn_tmp.autocommit = True
_cur = _conn_tmp.cursor()
_cur.execute(f"SELECT MAX(ts) FROM candles_mt5_xauusd_{args.tf}")
_max_ts = _cur.fetchone()[0]
_cur.close(); _conn_tmp.close()
today = datetime.fromtimestamp(_max_ts / 1000, tz=timezone.utc).date() if _max_ts else datetime.now(timezone.utc).date()
conn = get_conn(); conn.autocommit = True

print(f"\n  COMPARE BT vs LIVE — {BROKER} — {today}")

# ── Load MT5 live trades ──
live_trades = {}  # sym -> [trades]
live_open = {}    # sym -> [positions]
try:
    import MetaTrader5 as mt5
    if mt5.initialize():
        from datetime import timedelta
        from_date = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        to_date = from_date + timedelta(days=1)

        # Closed deals today
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
            # din.time est en heure broker (UTC+3) — convertir en UTC pour filtrer
            entry_broker = datetime.fromtimestamp(din.time, tz=timezone.utc)
            entry_utc = entry_broker - timedelta(hours=3)
            if entry_utc.date() != today: continue
            sym_sn = MAGIC_REVERSE.get(din.magic)
            if not sym_sn: continue
            sym, sn = sym_sn
            d_dir = 'long' if din.type == 0 else 'short'
            live_trades.setdefault(sym, []).append({
                'strat': sn, 'dir': d_dir,
                'entry': din.price, 'exit': dout.price,
                'pnl': td['pnl'],
                'entry_time': entry_broker,  # stocker heure broker, l'affichage soustrait 3h
                'exit_time': datetime.fromtimestamp(dout.time, tz=timezone.utc),
            })

        # Open positions
        for sym in INSTRUMENTS:
            positions = mt5.positions_get(symbol=sym) or []
            for p in positions:
                sym_sn = MAGIC_REVERSE.get(p.magic)
                if not sym_sn: continue
                s, sn = sym_sn
                if s != sym: continue
                d_dir = 'long' if p.type == 0 else 'short'
                live_open.setdefault(sym, []).append({
                    'strat': sn, 'dir': d_dir,
                    'entry': p.price_open, 'stop': p.sl, 'tp': p.tp,
                    'pnl': p.profit, 'lots': p.volume,
                    'time': datetime.fromtimestamp(p.time, tz=timezone.utc),
                })

        mt5.shutdown()
    else:
        print("  MT5 non disponible — comparaison BT uniquement")
except ImportError:
    print("  MetaTrader5 non installe — comparaison BT uniquement")

# ── Per instrument ──
for sym, icfg in INSTRUMENTS.items():
    portfolio = icfg['portfolio']
    if not portfolio: continue
    sym_exits = STRAT_EXITS.get((args.account, sym), {})

    # Load recent data (5000 bars = convergence garantie indicateurs, ~20x plus rapide que full)
    candles, daily_atr, global_atr, trading_days = load_data_recent(conn, sym, n=5000, tf=args.tf)
    from backtest_engine import prev_trading_day
    pd_ = prev_trading_day(today, trading_days)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr

    # Collect trades via backtest_engine (meme code que bt_portfolio)
    raw_trades = collect_trades(candles, daily_atr, global_atr, trading_days,
                                portfolio, sym_exits, date_filter=today)

    # Convertir en format compare_today
    bt_trades = []
    for ci, xi, di, pnl_oz, sl_atr, atr_t, mo, sn in raw_trades:
        d_dir = 'long' if di == 1 else 'short'
        entry = float(candles.iloc[ci]['close'])
        ex = entry + pnl_oz if di == 1 else entry - pnl_oz
        risk_1r = sl_atr * atr_t  # 1R = distance du stop en points
        bt_trades.append({
            'strat': sn, 'dir': d_dir, 'entry': entry, 'exit': ex,
            'pnl_pts': pnl_oz, 'pnl_r': pnl_oz / risk_1r if risk_1r > 0 else 0,
            'risk_1r': risk_1r, 'bars': xi - ci,
            'entry_time': str(candles.iloc[ci]['ts_dt']),
            'exit_time': str(candles.iloc[min(xi, len(candles)-1)]['ts_dt']),
            'skipped': None,
        })

    # Live data for this symbol
    lv = live_trades.get(sym, [])
    lo = live_open.get(sym, [])

    bt_active = bt_trades  # tous les trades (conflict filter deja applique dans collect_trades)
    bt_skip = []

    if not bt_active and not bt_skip and not lv and not lo: continue

    print(f"\n  {sym} — ATR={atr:.2f} — {len(portfolio)} strats")
    print(f"  BT: {len(bt_active)} trades ({len(bt_skip)} skipped) | Live: {len(lv)} closed + {len(lo)} open")

    # Build maps
    bt_map = {}
    for t in bt_trades: bt_map.setdefault(t['strat'], []).append(t)
    lv_map = {}
    for t in lv: lv_map.setdefault(t['strat'], []).append(t)
    lo_map = {}
    for p in lo: lo_map.setdefault(p['strat'], []).append(p)
    all_sn = sorted(set(list(bt_map.keys()) + list(lv_map.keys()) + list(lo_map.keys())))

    # Build table
    tbl = PrettyTable()
    tbl.field_names = ['Sym', 'Strat', 'Exit', 'BT Dir', 'BT Entry', 'BT Exit', 'BT R', 'BT In', 'BT Out',
                       'LV Dir', 'LV Entry', 'LV Exit', 'LV R', 'LV In', 'LV Out',
                       'LV-BT', 'Verdict']
    tbl.align = 'r'
    tbl.align['Sym'] = 'l'
    tbl.align['Strat'] = 'l'
    tbl.align['Verdict'] = 'l'

    bt_total_pts = 0; lv_total_pts = 0
    table_rows = []

    for sn in all_sn:
        bts = bt_map.get(sn, [])
        lvs = lv_map.get(sn, [])
        los = lo_map.get(sn, [])
        bt = bts[0] if bts else None
        lv_t = lvs[0] if lvs else None
        lo_t = los[0] if los else None

        exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
        exit_type = exit_cfg[0]

        # BT columns
        if bt and bt['skipped']:
            bt_dir = 'SKIP'; bt_entry = f"{bt['entry']:.2f}"; bt_exit = '-'; bt_pts = '-'
            bt_in = bt['entry_time'][11:16]; bt_out = '-'
        elif bt:
            bt_dir = bt['dir']; bt_entry = f"{bt['entry']:.2f}"; bt_exit = f"{bt['exit']:.2f}"
            bt_pts = f"{bt['pnl_r']:+.2f}R"
            bt_total_pts += bt['pnl_r']
            bt_in = bt['entry_time'][11:16]; bt_out = bt['exit_time'][11:16]
        else:
            bt_dir = '-'; bt_entry = '-'; bt_exit = '-'; bt_pts = '-'; bt_in = '-'; bt_out = '-'

        # LV columns + pts (heures MT5 -3h pour aligner sur UTC candles)
        lv_sort_key = '99:99'  # trades sans live en dernier
        if lv_t:
            lv_dir = lv_t['dir']; lv_entry = f"{lv_t['entry']:.2f}"; lv_exit = f"{lv_t['exit']:.2f}"
            lv_pnl_pts = (lv_t['exit'] - lv_t['entry']) if lv_t['dir'] == 'long' else (lv_t['entry'] - lv_t['exit'])
            # R = pnl / risk_1r (utilise le risk_1r du BT si dispo, sinon ATR*3 par defaut)
            risk_1r = bt['risk_1r'] if bt and not bt['skipped'] else 3.0 * atr
            lv_pnl_r = lv_pnl_pts / risk_1r if risk_1r > 0 else 0
            lv_pts = f"{lv_pnl_r:+.2f}R"
            lv_total_pts += lv_pnl_r
            lv_entry_utc = lv_t['entry_time'] - timedelta(hours=3) if hasattr(lv_t['entry_time'], 'strftime') else lv_t['entry_time']
            lv_exit_utc = lv_t['exit_time'] - timedelta(hours=3) if hasattr(lv_t['exit_time'], 'strftime') else lv_t['exit_time']
            lv_in = lv_entry_utc.strftime('%H:%M') if hasattr(lv_entry_utc, 'strftime') else str(lv_entry_utc)[11:16]
            lv_out = lv_exit_utc.strftime('%H:%M') if hasattr(lv_exit_utc, 'strftime') else str(lv_exit_utc)[11:16]
            lv_sort_key = lv_in
        elif lo_t:
            lv_dir = lo_t['dir']; lv_entry = f"{lo_t['entry']:.2f}"; lv_exit = 'OPEN'
            lv_pts = '...'
            lv_entry_utc = lo_t['time'] - timedelta(hours=3) if hasattr(lo_t['time'], 'strftime') else lo_t['time']
            lv_in = lv_entry_utc.strftime('%H:%M') if hasattr(lv_entry_utc, 'strftime') else str(lv_entry_utc)[11:16]
            lv_out = '...'
            lv_sort_key = lv_in
        else:
            lv_dir = '-'; lv_entry = '-'; lv_exit = '-'; lv_pts = '-'; lv_in = '-'; lv_out = '-'

        # Delta R: LV R - BT R
        lv_bt_diff = '-'
        if bt and not bt['skipped'] and lv_t:
            lv_pnl = (lv_t['exit'] - lv_t['entry']) if lv_t['dir'] == 'long' else (lv_t['entry'] - lv_t['exit'])
            risk_1r_d = bt['risk_1r'] if bt['risk_1r'] > 0 else 1
            lv_bt_diff = f"{(lv_pnl / risk_1r_d) - bt['pnl_r']:+.2f}R"

        # Verdict
        if bt and not bt['skipped'] and (lv_t or lo_t):
            lv_d = lv_t['dir'] if lv_t else lo_t['dir']
            lv_e = lv_t['entry'] if lv_t else lo_t['entry']
            if bt['dir'] != lv_d:
                verdict = 'DIR MISMATCH!'
            else:
                entry_diff = abs(bt['entry'] - lv_e)
                if entry_diff < 0.5: verdict = ''
                elif entry_diff < 2.0: verdict = ''
                else: verdict = f'!! ENTRY DIFF {entry_diff:.1f}'
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

        table_rows.append((lv_sort_key, [sym, sn, exit_type, bt_dir, bt_entry, bt_exit, bt_pts, bt_in, bt_out,
                     lv_dir, lv_entry, lv_exit, lv_pts, lv_in, lv_out,
                     lv_bt_diff, verdict]))

    # Tri par heure d'entree live
    for _, row in sorted(table_rows, key=lambda x: x[0]):
        tbl.add_row(row)

    print(tbl)
    print(f"  TOTAL:  BT {bt_total_pts:+.2f}R  |  LV {lv_total_pts:+.2f}R")

conn.close()
