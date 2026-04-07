"""
MQTT Publisher — tourne sur chaque VPS, publie l'etat MT5 toutes les secondes.
Process SEPARE de live_mt5.py (ne touche a rien).

Usage:
  python mqtt_publisher.py 5ers
  python mqtt_publisher.py ftmo

Publie sur topics:
  vpswing/<account>/state    → positions, balance, pnl, ATR, candle
  vpswing/<account>/trade    → quand un trade s'ouvre/ferme (event)
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse, json, time, importlib, os
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import MetaTrader5 as mt5
import paho.mqtt.client as mqtt

# ── CONFIG ──
parser = argparse.ArgumentParser()
parser.add_argument('account', choices=['icm', 'ftmo', '5ers'])
args = parser.parse_args()

cfg = importlib.import_module(f'config_{args.account}')
BROKER = cfg.BROKER
INSTRUMENTS = cfg.INSTRUMENTS

MQTT_HOST = os.getenv('MQTT_HOST', 'broker.hivemq.com')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USER = os.getenv('MQTT_USER', '')
MQTT_PASS = os.getenv('MQTT_PASS', '')
TOPIC_BASE = f"vpswing/{args.account}"
INTERVAL = 1  # secondes

# ── MT5 ──
def mt5_init():
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    info = mt5.terminal_info()
    print(f"MT5: {info.company} {info.name}")

def get_positions():
    """Positions ouvertes avec details."""
    positions = []
    for sym in INSTRUMENTS:
        for p in (mt5.positions_get(symbol=sym) or []):
            positions.append({
                'ticket': p.ticket,
                'symbol': p.symbol,
                'dir': 'long' if p.type == 0 else 'short',
                'volume': p.volume,
                'entry': p.price_open,
                'sl': p.sl,
                'tp': p.tp,
                'pnl': round(p.profit, 2),
                'swap': round(p.swap, 2),
                'magic': p.magic,
                'comment': p.comment,
                'time_open': datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
            })
    return positions

def get_account():
    """Balance, equity, margin."""
    info = mt5.account_info()
    if not info: return {}
    return {
        'balance': round(info.balance, 2),
        'equity': round(info.equity, 2),
        'margin': round(info.margin, 2),
        'free_margin': round(info.margin_free, 2),
        'margin_level': round(info.margin_level, 2) if info.margin_level else 0,
        'profit': round(info.profit, 2),
    }

def _deals_to_trades(deals):
    """Convertit une liste de deals MT5 en trades (in+out groupes)."""
    pos = {}
    for d in deals:
        if d.type > 1: continue  # skip balance, credit, etc
        pid = d.position_id
        if d.entry == 0:  # ENTRY_IN
            pos.setdefault(pid, {})['in'] = d
        elif d.entry == 1:  # ENTRY_OUT
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
    """Trades fermes aujourd'hui."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today.replace(hour=23, minute=59, second=59)
    deals = mt5.history_deals_get(today, tomorrow) or []
    return _deals_to_trades(deals)

def get_all_history():
    """Tout l'historique disponible sur MT5."""
    from_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    to_date = datetime.now(timezone.utc)
    deals = mt5.history_deals_get(from_date, to_date) or []
    return _deals_to_trades(deals)

def get_last_candle(symbol):
    """Derniere bougie fermee."""
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

# ── MQTT ──
def mqtt_connect():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    print(f"MQTT: {MQTT_HOST}:{MQTT_PORT} topic={TOPIC_BASE}")
    return client

# ── MAIN ──
mt5_init()
mq = mqtt_connect()

print(f"Publisher {BROKER} — interval {INTERVAL}s")
print(f"Instruments: {list(INSTRUMENTS.keys())}")

# Publish full history at startup
print("Publishing full history...", end='', flush=True)
history = get_all_history()
# Split en chunks si trop gros (MQTT max ~256KB par message)
CHUNK = 100
for i in range(0, max(len(history), 1), CHUNK):
    chunk = history[i:i+CHUNK]
    mq.publish(f"{TOPIC_BASE}/history", json.dumps({
        'chunk': i // CHUNK,
        'total': len(history),
        'trades': chunk,
    }), qos=1)
print(f" {len(history)} trades published in {max(1, (len(history)-1)//CHUNK+1)} chunks")

prev_positions = set()  # pour detecter trades ouverts/fermes

try:
    while True:
        try:
            # Collecter etat
            positions = get_positions()
            account = get_account()
            today_trades = get_today_trades()

            # Candle pour chaque instrument
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

            # Publish state
            mq.publish(f"{TOPIC_BASE}/state", json.dumps(state), qos=0)

            # Detecter events (trade ouvert/ferme)
            cur_tickets = set(p['ticket'] for p in positions)
            opened = cur_tickets - prev_positions
            closed = prev_positions - cur_tickets
            if opened or closed:
                event = {
                    'ts': state['ts'],
                    'opened': [p for p in positions if p['ticket'] in opened],
                    'closed': [t for t in today_trades if t.get('ticket') in closed],
                }
                mq.publish(f"{TOPIC_BASE}/trade", json.dumps(event), qos=1)
                for p in event['opened']:
                    print(f"  OPEN {p['symbol']} {p['comment']} {p['dir']} @ {p['entry']}")
                for t in event.get('closed', []):
                    print(f"  CLOSE {t['symbol']} {t['comment']} pnl={t['pnl']}")
            prev_positions = cur_tickets

        except Exception as e:
            print(f"Error: {e}")
            if not mt5.terminal_info():
                print("MT5 reconnect...")
                mt5_init()

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("[STOP]")
finally:
    mq.loop_stop()
    mq.disconnect()
    mt5.shutdown()
