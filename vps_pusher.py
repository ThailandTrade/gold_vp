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

def get_today_trades():
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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

push_count = 0
history_sent = False

try:
    while True:
        try:
            positions = get_positions()
            account = get_account()
            today_trades = get_today_trades()
            candles = {}
            for sym in INSTRUMENTS:
                candles[sym] = get_last_candle(sym)

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
            }

            payload = {'state': state}
            # Envoyer l'histo au premier push, puis toutes les 5 min
            if not history_sent or push_count % 300 == 0:
                payload['history'] = history
                history = get_all_history()  # refresh
                history_sent = True

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
