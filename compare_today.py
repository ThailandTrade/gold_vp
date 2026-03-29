"""
Compare backtest vs live MT5 trades for today — multi-instrument.
Usage: python compare_today.py [icm|ftmo|5ers]
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, importlib; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn
from strats import detect_all, compute_indicators, sim_exit_custom, make_magic
from strat_exits import STRAT_EXITS, DEFAULT_EXIT
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument('account', nargs='?', default='5ers', choices=['icm','ftmo','5ers'])
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = cfg.INSTRUMENTS

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
               'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

def _magic(symbol, strat):
    return make_magic(args.account, symbol, strat)

MAGIC_REVERSE = {}
for sym, icfg in INSTRUMENTS.items():
    for sn in icfg['portfolio']:
        MAGIC_REVERSE[_magic(sym, sn)] = (sym, sn)

today = datetime.now(timezone.utc).date()
conn = get_conn(); conn.autocommit = True
W = 130

print(f"\n{'='*W}")
print(f"  COMPARE BT vs LIVE — {BROKER} — {today}")
print(f"{'='*W}")

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
            sym_sn = MAGIC_REVERSE.get(din.magic)
            if not sym_sn: continue
            sym, sn = sym_sn
            d_dir = 'long' if din.type == 0 else 'short'
            live_trades.setdefault(sym, []).append({
                'strat': sn, 'dir': d_dir,
                'entry': din.price, 'exit': dout.price,
                'pnl': td['pnl'],
                'entry_time': datetime.fromtimestamp(din.time, tz=timezone.utc),
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

    # Load candles
    import re
    table = f"candles_mt5_{re.sub(r'[^a-z0-9]+', '_', sym.lower()).strip('_')}_5m"
    cur = conn.cursor()
    cur.execute(f"SELECT ts, open, high, low, close FROM {table} ORDER BY ts DESC LIMIT 2000")
    rows = cur.fetchall(); cur.close()
    if not rows: continue
    df = pd.DataFrame(rows, columns=['ts','open','high','low','close']).sort_values('ts').reset_index(drop=True)
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['open','high','low','close']: df[c] = df[c].astype(float)
    df['date'] = df['ts_dt'].dt.date
    df = compute_indicators(df)

    # ATR yesterday
    yc = df[df['date'] < today].copy()
    if len(yc) < 20: continue
    yc['pc'] = yc['close'].shift(1)
    yc['tr'] = np.maximum(yc['high']-yc['low'], np.maximum(abs(yc['high']-yc['pc']), abs(yc['low']-yc['pc'])))
    yc['atr'] = yc['tr'].ewm(span=14, adjust=False).mean()
    atr = float(yc['atr'].iloc[-1])

    # prev_day_data + prev2
    last_day = yc['date'].iloc[-1]
    dc = yc[yc['date'] == last_day]
    prev_day_data = {'open':float(dc.iloc[0]['open']), 'close':float(dc.iloc[-1]['close']),
                     'high':float(dc['high'].max()), 'low':float(dc['low'].min()),
                     'range':float(dc['high'].max()-dc['low'].min())}
    yc2 = yc[yc['date'] < last_day]
    prev2_day_data = None
    if len(yc2) > 0:
        ld2 = yc2['date'].iloc[-1]; dc2 = yc2[yc2['date'] == ld2]
        prev2_day_data = {'open':float(dc2.iloc[0]['open']), 'close':float(dc2.iloc[-1]['close']),
                          'high':float(dc2['high'].max()), 'low':float(dc2['low'].min()),
                          'range':float(dc2['high'].max()-dc2['low'].min())}

    # Backtest signals for today
    trig = {}; bt_signals = []
    for ci in range(len(df)):
        row = df.iloc[ci]; ct = row['ts_dt']; d = ct.date()
        if d != today: continue
        hour = ct.hour + ct.minute / 60.0
        ds = pd.Timestamp(d.year,d.month,d.day,0,0,tz='UTC')
        te = pd.Timestamp(d.year,d.month,d.day,6,0,tz='UTC')
        ls = pd.Timestamp(d.year,d.month,d.day,8,0,tz='UTC')
        ns = pd.Timestamp(d.year,d.month,d.day,14,30,tz='UTC')
        tv = df[(df['ts_dt']>=ds)&(df['ts_dt']<=ct)]
        tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
        def add(sn, d_dir, e):
            if sn in portfolio:
                bt_signals.append((ci, sn, d_dir, e, str(ct)))
        detect_all(df, ci, row, ct, d, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

    # Simulate with conflict filter
    bt_trades = []
    active_pos = []
    for ci, sn, d_dir, entry, ct_str in bt_signals:
        is_open = sn in OPEN_STRATS
        exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
        etype, p1, p2, p3 = exit_cfg[0], exit_cfg[1], exit_cfg[2], exit_cfg[3] if len(exit_cfg) > 3 else 0
        b, ex = sim_exit_custom(df, ci, entry, d_dir, atr, etype, p1, p2, p3, check_entry_candle=is_open)
        xi = ci + b
        di = 1 if d_dir == 'long' else -1
        active_pos = [(axi, ad) for axi, ad in active_pos if axi >= ci]
        skipped = None
        if any(ad != di for _, ad in active_pos):
            skipped = 'conflit'
        pnl = (ex - entry) if d_dir == 'long' else (entry - ex)
        if not skipped:
            active_pos.append((xi, di))
        bt_trades.append({'strat':sn, 'dir':d_dir, 'entry':entry, 'exit':ex,
                          'pnl_oz': pnl if not skipped else 0,
                          'bars':b, 'entry_time':ct_str,
                          'exit_time':str(df.iloc[min(xi,len(df)-1)]['ts_dt']),
                          'skipped': skipped})

    # Live data for this symbol
    lv = live_trades.get(sym, [])
    lo = live_open.get(sym, [])

    bt_active = [t for t in bt_trades if not t['skipped']]
    bt_skip = [t for t in bt_trades if t['skipped']]

    if not bt_active and not lv and not lo: continue

    print(f"\n{'-'*W}")
    print(f"  {sym} — ATR={atr:.2f} — {len(portfolio)} strats")
    print(f"  BT: {len(bt_active)} trades ({len(bt_skip)} skipped) | Live: {len(lv)} closed + {len(lo)} open")
    print(f"{'-'*W}")

    # Build maps
    bt_map = {}
    for t in bt_trades: bt_map.setdefault(t['strat'], []).append(t)
    lv_map = {}
    for t in lv: lv_map.setdefault(t['strat'], []).append(t)
    lo_map = {}
    for p in lo: lo_map.setdefault(p['strat'], []).append(p)
    all_sn = sorted(set(list(bt_map.keys()) + list(lv_map.keys()) + list(lo_map.keys())))

    print(f"  {'Strat':>18s} | {'BT dir':>6s} {'BT entry':>9s} {'BT exit':>9s} {'BT pnl':>8s} {'BT time':>12s} | {'LV dir':>6s} {'LV entry':>9s} {'LV exit':>9s} {'LV pnl':>8s} {'LV time':>12s}")
    print(f"  {'-'*115}")

    for sn in all_sn:
        bts = bt_map.get(sn, [])
        lvs = lv_map.get(sn, [])
        los = lo_map.get(sn, [])
        n = max(len(bts), len(lvs) + len(los))
        for i in range(max(n, 1)):
            bt = bts[i] if i < len(bts) else None
            lv_t = lvs[i] if i < len(lvs) else None
            lo_t = los[i - len(lvs)] if i >= len(lvs) and (i - len(lvs)) < len(los) else None

            # BT column
            if bt and bt['skipped']:
                bt_str = f"{'SKIP':>6s} {bt['entry']:>9.2f} {'---':>9s} {'---':>8s} {bt['entry_time'][11:16]:>5s}       "
            elif bt:
                bt_str = f"{bt['dir']:>6s} {bt['entry']:>9.2f} {bt['exit']:>9.2f} {bt['pnl_oz']:>+8.2f} {bt['entry_time'][11:16]:>5s}->{bt['exit_time'][11:16]:>5s}"
            else:
                bt_str = f"{'---':>6s} {'---':>9s} {'---':>9s} {'---':>8s} {'---':>12s}"

            # LV column
            if lv_t:
                et = lv_t['entry_time'].strftime('%H:%M') if hasattr(lv_t['entry_time'], 'strftime') else str(lv_t['entry_time'])[11:16]
                xt = lv_t['exit_time'].strftime('%H:%M') if hasattr(lv_t['exit_time'], 'strftime') else str(lv_t['exit_time'])[11:16]
                lv_str = f"{lv_t['dir']:>6s} {lv_t['entry']:>9.2f} {lv_t['exit']:>9.2f} {lv_t['pnl']:>+8.2f} {et}->{xt:>5s}"
            elif lo_t:
                et = lo_t['time'].strftime('%H:%M') if hasattr(lo_t['time'], 'strftime') else str(lo_t['time'])[11:16]
                lv_str = f"{lo_t['dir']:>6s} {lo_t['entry']:>9.2f} {'...':>9s} {lo_t['pnl']:>+8.2f} {et}->  ..."
            else:
                lv_str = f"{'---':>6s} {'---':>9s} {'---':>9s} {'---':>8s} {'---':>12s}"

            label = sn if i == 0 else ''
            print(f"  {label:>18s} | {bt_str} | {lv_str}")

    # Totals
    bt_pnl = sum(t['pnl_oz'] for t in bt_trades if not t['skipped'])
    lv_pnl = sum(t['pnl'] for t in lv)
    lo_pnl = sum(p['pnl'] for p in lo)
    print(f"  {'-'*105}")
    print(f"  {'TOTAL':>18s} | {'':>6s} {'':>9s} {'':>9s} {bt_pnl:>+8.2f} {'':>12s} | {'':>6s} {'':>9s} {lv_pnl+lo_pnl:>+8.2f} {'':>8s}")

conn.close()
print(f"\n{'='*W}")
