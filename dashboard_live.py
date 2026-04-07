"""
Dashboard Live — Streamlit sur le laptop.
Lit les donnees depuis l'API locale (api_server.py).

Usage:
  streamlit run dashboard_live.py
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests, os
from dotenv import load_dotenv
load_dotenv()

API_URL = os.getenv('DASHBOARD_API', 'http://localhost:8001')
ACCOUNTS = ['5ers', 'ftmo']

# ── PAGE ──
st.set_page_config(page_title="VP Swing Live", layout="wide")
st_autorefresh(interval=2000, key="refresh")  # refresh toutes les 2s, sans clignotement
st.title("VP Swing — Live Dashboard")

# ── FETCH STATE ──
try:
    r = requests.get(f"{API_URL}/state", timeout=3)
    all_states = r.json()
except:
    all_states = {}
    st.error(f"API non disponible ({API_URL})")

# ── ACCOUNTS ──
cols = st.columns(len(ACCOUNTS))

for i, account in enumerate(ACCOUNTS):
    with cols[i]:
        data = all_states.get(account, {})
        state = data.get('state', {})
        hist = data.get('history', [])
        last_push = data.get('last_push', '')

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
                st.text(f"{pnl_color} {p['symbol']} {p.get('comment','')} {p['dir'].upper()} "
                       f"@ {p['entry']:.2f} → {p.get('current', 0):.2f} SL={p['sl']:.2f} "
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
                st.text(f"{pnl_color} {time_close} {t['symbol']} {t.get('comment','')} "
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

# Auto-refresh gere par st_autorefresh (pas de sleep/rerun)
