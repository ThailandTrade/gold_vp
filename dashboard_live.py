"""
Dashboard Live — Streamlit sur le laptop.
Recoit les donnees des VPS via MQTT en temps reel.

Usage:
  streamlit run dashboard_live.py
"""
import streamlit as st
import json, os, time, threading
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

import paho.mqtt.client as mqtt

# ── CONFIG ──
MQTT_HOST = os.getenv('MQTT_HOST', 'broker.hivemq.com')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USER = os.getenv('MQTT_USER', '')
MQTT_PASS = os.getenv('MQTT_PASS', '')
ACCOUNTS = ['5ers', 'ftmo']

# ── SHARED STATE (thread-safe via dict global, pas session_state) ──
import threading
_lock = threading.Lock()
_data = {'states': {}, 'events': [], 'history': {}, 'connected': False}


@st.cache_resource
def get_mqtt_client():
    """Lance le subscriber MQTT une seule fois (cache Streamlit)."""
    def on_connect(client, userdata, flags, rc, props=None):
        with _lock:
            _data['connected'] = True
        client.subscribe("vpswing/#")

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload
            if not payload or payload == b'':
                return
            data = json.loads(payload)
            topic = msg.topic
            with _lock:
                if topic.endswith('/state'):
                    account = topic.split('/')[1]
                    _data['states'][account] = data
                elif topic.endswith('/trade'):
                    _data['events'].append(data)
                    if len(_data['events']) > 100:
                        _data['events'] = _data['events'][-100:]
                elif '/history/' in topic:
                    account = topic.split('/')[1]
                    chunk_trades = data.get('trades', [])
                    chunk_id = data.get('chunk', 0)
                    if chunk_id == 0:
                        _data['history'][account] = []
                    _data['history'].setdefault(account, []).extend(chunk_trades)
        except:
            pass

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except:
        client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client


# Start MQTT
get_mqtt_client()

# ── PAGE ──
st.set_page_config(page_title="VP Swing Live", layout="wide")
st.title("VP Swing — Live Dashboard")

with _lock:
    connected = _data['connected']
    states = dict(_data['states'])
    events = list(_data['events'])
    history = dict(_data['history'])

if not connected:
    st.warning("Connexion MQTT en cours...")

# ── ACCOUNTS ──
cols = st.columns(len(ACCOUNTS))

for i, account in enumerate(ACCOUNTS):
    with cols[i]:
        state = states.get(account)
        if not state:
            st.header(f"{account.upper()}")
            st.warning("En attente de donnees...")
            continue

        # Header
        acct = state.get('account_info', {})
        balance = acct.get('balance', 0)
        equity = acct.get('equity', 0)
        today_pnl = state.get('today_pnl', 0)
        today_count = state.get('today_count', 0)
        ts = state.get('ts', '')[:19]

        st.header(f"{account.upper()}")
        st.caption(f"Derniere maj: {ts}")

        # Metriques
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Balance", f"${balance:,.0f}")
        c2.metric("Equity", f"${equity:,.0f}")
        c3.metric("PnL jour", f"${today_pnl:+,.0f}")
        c4.metric("Trades jour", today_count)

        # Positions ouvertes
        positions = state.get('positions', [])
        if positions:
            st.subheader(f"Positions ouvertes ({len(positions)})")
            for p in positions:
                pnl_color = "🟢" if p['pnl'] >= 0 else "🔴"
                st.text(f"{pnl_color} {p['symbol']} {p['comment']} {p['dir'].upper()} "
                       f"@ {p['entry']:.2f} SL={p['sl']:.2f} "
                       f"PnL=${p['pnl']:+.2f} ({p['volume']}lots)")
        else:
            st.info("Aucune position ouverte")

        # Trades du jour
        trades = state.get('today_trades', [])
        if trades:
            st.subheader(f"Trades du jour ({len(trades)})")
            for t in reversed(trades):
                pnl_color = "🟢" if t['pnl'] >= 0 else "🔴"
                time_close = t.get('time_close', '')[:16]
                st.text(f"{pnl_color} {time_close} {t['symbol']} {t['comment']} "
                       f"{t['dir'].upper()} {t['entry']:.2f}→{t['exit']:.2f} "
                       f"PnL=${t['pnl']:+.2f}")

        # Derniere bougie par instrument
        candles = state.get('candles', {})
        if candles:
            st.subheader("Dernieres bougies")
            for sym, c in candles.items():
                if c:
                    rng = c.get('high', 0) - c.get('low', 0)
                    st.text(f"{sym} {c.get('time', '')[:16]} "
                           f"O={c.get('open', 0):.1f} H={c.get('high', 0):.1f} "
                           f"L={c.get('low', 0):.1f} C={c.get('close', 0):.1f} "
                           f"R={rng:.1f}")

        # Historique complet
        hist = history.get(account, [])
        if hist:
            with st.expander(f"Historique complet ({len(hist)} trades)"):
                total_pnl = sum(t.get('pnl', 0) for t in hist)
                wins = sum(1 for t in hist if t.get('pnl', 0) > 0)
                wr = wins / len(hist) * 100 if hist else 0
                st.text(f"Total: {len(hist)} trades | WR: {wr:.0f}% | PnL: ${total_pnl:+,.2f}")
                for t in reversed(hist[-50:]):
                    pnl_color = "🟢" if t.get('pnl', 0) >= 0 else "🔴"
                    st.text(f"{pnl_color} {t.get('time_close', '')[:16]} "
                           f"{t.get('symbol', '')} {t.get('comment', '')} "
                           f"{t.get('dir', '').upper()} "
                           f"{t.get('entry', 0):.2f}→{t.get('exit', 0):.2f} "
                           f"PnL=${t.get('pnl', 0):+.2f}")

# ── EVENTS LOG ──
st.divider()
st.subheader("Events recents")
if events:
    for ev in reversed(events[-20:]):
        ts = ev.get('ts', '')[:19]
        for p in ev.get('opened', []):
            st.text(f"🟢 {ts} {p.get('symbol')} {p.get('comment')} "
                   f"{p.get('dir', '').upper()} @ {p.get('entry', 0):.2f}")
        for t in ev.get('closed', []):
            pnl_color = "🟢" if t.get('pnl', 0) >= 0 else "🔴"
            st.text(f"{pnl_color} {ts} {t.get('symbol')} {t.get('comment')} "
                   f"PnL=${t.get('pnl', 0):+.2f}")
else:
    st.info("Aucun event")

# Auto-refresh 1s
time.sleep(1)
st.rerun()
