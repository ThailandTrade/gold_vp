"""
VPS Pusher — tourne sur chaque VPS, pousse l'etat MT5 chaque seconde vers l'API.
Process SEPARE de live_mt5.py.

Usage:
  python vps_pusher.py ftmo
  python vps_pusher.py 5ers
  python vps_pusher.py ftmo --url https://custom-domain.com
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, json, time, importlib, os
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import MetaTrader5 as mt5
import requests

# ── CONFIG ──
parser = argparse.ArgumentParser()
parser.add_argument('account', choices=['icm', 'ftmo', '5ers'])
parser.add_argument('--url', default='https://unprolongable-nonexternalized-elizabet.ngrok-free.dev')
parser.add_argument('--interval', type=float, default=1.0)
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = cfg.INSTRUMENTS
API_URL = f"{args.url.rstrip('/')}/push/{args.account}"
INTERVAL = args.interval

# ── MT5 ──
def mt5_init():
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    info = mt5.terminal_info()
    print(f"MT5: {info.company} {info.name}")

def get_positions():
    positions = []
    for sym in INSTRUMENTS:
        for p in (mt5.positions_get(symbol=sym) or []):
            positions.append({
                'ticket': p.ticket,
                'symbol': p.symbol,
                'dir': 'long' if p.type == 0 else 'short',
                'volume': p.volume,
                'entry': round(p.price_open, 2),
                'current': round(p.price_current, 2),
                'sl': round(p.sl, 2),
                'tp': round(p.tp, 2),
                'pnl': round(p.profit, 2),
                'swap': round(p.swap, 2),
                'comment': p.comment,
                'time_open': datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
            })
    return positions

def get_account():
    info = mt5.account_info()
    if not info: return {}
    return {
        'balance': round(info.balance, 2),
        'equity': round(info.equity, 2),
        'margin': round(info.margin, 2),
        'free_margin': round(info.margin_free, 2),
        'profit': round(info.profit, 2),
    }

def _deals_to_trades(deals):
    pos = {}
    for d in deals:
        if d.type > 1: continue
        pid = d.position_id
        if d.entry == 0:
            pos.setdefault(pid, {})['in'] = d
        elif d.entry == 1:
            pos.setdefault(pid, {})['out'] = d
    trades = []
    for pid, td in pos.items():
        if not td.get('in') or not td.get('out'): continue
        din = td['in']; dout = td['out']
        trades.append({
            'ticket': din.order,
            'symbol': din.symbol,
            'dir': 'long' if din.type == 0 else 'short',
            'entry': round(din.price, 2),
            'exit': round(dout.price, 2),
            'volume': din.volume,
            'pnl': round(dout.profit, 2),
            'comment': din.comment,
            'time_open': datetime.fromtimestamp(din.time, tz=timezone.utc).isoformat(),
            'time_close': datetime.fromtimestamp(dout.time, tz=timezone.utc).isoformat(),
        })
    return trades

def _get_candle_date():
    """Date de la derniere bougie en DB (pas l'horloge systeme)."""
    conn = _get_conn()
    cur = conn.cursor()
    import re
    sym0 = list(INSTRUMENTS.keys())[0]
    table = f"candles_mt5_{re.sub(r'[^a-z0-9]+', '_', sym0.lower()).strip('_')}_5m"
    cur.execute(f"SELECT MAX(ts) FROM {table}")
    max_ts = cur.fetchone()[0]
    cur.close(); conn.close()
    if max_ts:
        return datetime.fromtimestamp(max_ts / 1000, tz=timezone.utc).date()
    return datetime.now(timezone.utc).date()

def get_today_trades():
    today_dt = _get_candle_date()
    today = datetime(today_dt.year, today_dt.month, today_dt.day, tzinfo=timezone.utc)
    tomorrow = today.replace(hour=23, minute=59, second=59)
    deals = mt5.history_deals_get(today, tomorrow) or []
    return _deals_to_trades(deals)

def get_all_history():
    from_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    to_date = datetime.now(timezone.utc)
    deals = mt5.history_deals_get(from_date, to_date) or []
    return _deals_to_trades(deals)

def get_last_candle(symbol):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 1, 1)
    if rates is None or len(rates) == 0: return {}
    r = rates[0]
    return {
        'time': datetime.fromtimestamp(r[0], tz=timezone.utc).isoformat(),
        'open': round(float(r[1]), 2),
        'high': round(float(r[2]), 2),
        'low': round(float(r[3]), 2),
        'close': round(float(r[4]), 2),
        'volume': int(r[5]),
    }

# ── MAIN ──
mt5_init()

print(f"Pusher {BROKER} → {API_URL}")
print(f"Instruments: {list(INSTRUMENTS.keys())}")
print(f"Interval: {INTERVAL}s")

# Push full history au demarrage
print("Fetching full history...", end='', flush=True)
history = get_all_history()
print(f" {len(history)} trades")

# BT compare: init
from phase1_poc_calculator import get_conn as _get_conn
from backtest_engine import load_data_recent, collect_trades, prev_trading_day
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

def compute_compare_today():
    """Calcule le compare BT vs LV complet (meme logique que compare_today.py).
    Retourne le tableau final pret a afficher — aucun calcul cote dashboard."""
    today = _get_candle_date()
    today_trades = get_today_trades()
    conn = _get_conn()
    result = {}
    for sym, icfg in INSTRUMENTS.items():
        portfolio = icfg['portfolio']
        if not portfolio: continue
        sym_exits = STRAT_EXITS.get((args.account, sym), {})
        candles, daily_atr, global_atr, trading_days = load_data_recent(conn, sym, n=5000)
        if len(candles) == 0: continue
        pd_ = prev_trading_day(today, trading_days)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        raw = collect_trades(candles, daily_atr, global_atr, trading_days,
                            portfolio, sym_exits, date_filter=today)
        # BT par strat
        bt_by_strat = {}
        for ci, xi, di, pnl_oz, sl_atr, atr_t, mo, sn in raw:
            entry = float(candles.iloc[ci]['close'])
            risk_1r = sl_atr * atr_t
            bt_by_strat[sn] = {
                'dir': 'long' if di == 1 else 'short',
                'entry': round(entry, 2),
                'exit': round(entry + pnl_oz if di == 1 else entry - pnl_oz, 2),
                'pnl_r': round(pnl_oz / risk_1r, 2) if risk_1r > 0 else 0,
                'risk_1r': round(risk_1r, 4),
            }
        # LV par strat
        lv_by_strat = {}
        for t in today_trades:
            if t['symbol'] != sym: continue
            sn = t.get('comment', '')
            if sn in portfolio:
                lv_by_strat[sn] = t
        # Build compare rows (toutes les strats du portfolio)
        rows = []
        for sn in portfolio:
            bt = bt_by_strat.get(sn)
            lv = lv_by_strat.get(sn)
            row = {'strat': sn, 'bt': None, 'lv': None, 'delta': None}
            if bt:
                row['bt'] = bt
            if lv:
                lv_pnl = (lv['exit'] - lv['entry']) if lv['dir'] == 'long' else (lv['entry'] - lv['exit'])
                risk_1r = bt['risk_1r'] if bt else sl_atr * atr  # fallback
                lv_r = round(lv_pnl / risk_1r, 2) if risk_1r > 0 else 0
                row['lv'] = {
                    'dir': lv['dir'],
                    'entry': lv['entry'],
                    'exit': lv['exit'],
                    'pnl_r': lv_r,
                    'pnl_usd': lv['pnl'],
                }
            if bt and row['lv']:
                row['delta'] = round(row['lv']['pnl_r'] - bt['pnl_r'], 2)
            rows.append(row)
        result[sym] = {'atr': round(atr, 2), 'rows': rows}
    conn.close()
    return result

print("Computing compare today...", end='', flush=True)
bt_compare = compute_compare_today()
print(f" {sum(len(v['rows']) for v in bt_compare.values())} strats")

push_count = 0
history_sent = False
BT_REFRESH = 60  # recalcule BT toutes les 60s (nouvelles bougies)

try:
    while True:
        try:
            positions = get_positions()
            account = get_account()
            today_trades = get_today_trades()
            candles = {}
            for sym in INSTRUMENTS:
                candles[sym] = get_last_candle(sym)

            # Portfolio par instrument (pour afficher toutes les strats dans le dashboard)
            portfolios = {sym: icfg['portfolio'] for sym, icfg in INSTRUMENTS.items()}

            state = {
                'ts': datetime.now(timezone.utc).isoformat(),
                'account': args.account,
                'broker': BROKER,
                'positions': positions,
                'account_info': account,
                'today_trades': today_trades,
                'today_pnl': sum(t['pnl'] for t in today_trades),
                'today_count': len(today_trades),
                'candles': candles,
                'portfolios': portfolios,
            }

            payload = {'state': state, 'bt_compare': bt_compare}
            # Envoyer l'histo au premier push, puis toutes les 5 min
            if not history_sent or push_count % 300 == 0:
                payload['history'] = history
                history = get_all_history()  # refresh
                history_sent = True
            # Refresh BT compare toutes les 60s
            if push_count % BT_REFRESH == 0:
                bt_compare = compute_compare_today()

            r = requests.post(API_URL, json=payload, timeout=5)
            push_count += 1
            if push_count % 60 == 0:  # log toutes les minutes
                print(f"  push #{push_count} | {len(positions)} pos | ${account.get('balance',0):,.0f} | today {len(today_trades)} trades ${sum(t['pnl'] for t in today_trades):+,.0f}")

        except requests.exceptions.RequestException as e:
            print(f"  Push error: {e}")
        except Exception as e:
            print(f"  Error: {e}")
            if not mt5.terminal_info():
                print("  MT5 reconnect...")
                mt5_init()

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("[STOP]")
finally:
    mt5.shutdown()
