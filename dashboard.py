"""
Dashboard Streamlit — Paper Trading VP Swing
streamlit run dashboard.py
"""
import streamlit as st
import json, os, time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import itertools

LOG_FILE = "paper_trades.json"
CAPITAL_INITIAL = 1000.0

STRAT_NAMES = {
    'A':'IB Tokyo 1h UP','C':'FADE Tokyo→London','D':'GAP Tokyo→London',
    'E':'KZ London fade','F':'2BAR Tokyo rev','G':'NY 1st candle',
    'H':'TOKEND 3b','I':'FADE NY 1h','J':'LON 1st candle',
    'O':'BigCandle Tokyo','P':'ORB NY 30min','Q':'Engulfing London',
    'R':'3soldiers Tokyo','S':'3soldiers rev London','V':'CandleRatio Tokyo',
    'Z':'3days reversal','AA':'CloseExtreme London','AC':'Absorption Tokyo'
}

st.set_page_config(page_title="VP Swing", layout="wide", page_icon="📊")
st.markdown("""<style>
    .block-container{padding-top:1rem;}
    [data-testid="stMetricValue"]{font-size:1.2rem;}
</style>""", unsafe_allow_html=True)

def load_state():
    if os.path.exists(LOG_FILE):
        mtime = os.path.getmtime(LOG_FILE)
        with open(LOG_FILE, 'r') as f: state = json.load(f)
        state['_mtime'] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        return state
    return {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
            'daily_cache': {}, '_mtime': '—'}

def main():
    state = load_state()
    capital = state['capital']
    trades = state['trades']
    positions = state['open_positions']
    pnl_total = capital - CAPITAL_INITIAL

    # ── SIDEBAR ──
    with st.sidebar:
        st.title("VP Swing")
        st.caption(f"MAJ: {state.get('_mtime','—')}")
        cache = {}
        for k, v in state.get('daily_cache', {}).items(): cache = v; break
        if cache:
            st.metric("ATR", f"{cache['atr']:.2f}" if cache.get('atr') else "—")
        st.divider()
        refresh = st.selectbox("Auto-refresh (sec)", [0, 10, 30, 60], index=0)
        if st.button("Reset", type="secondary"):
            reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                     'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
            with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
            st.success("Reset OK"); st.rerun()

    # ── KPIs ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Capital", f"${capital:,.2f}", delta=f"${pnl_total:+,.2f}")

    if trades:
        df = pd.DataFrame(trades)
        df['pnl_dollar'] = df['pnl_dollar'].astype(float)
        wins = df[df['pnl_dollar'] > 0]
        gp = wins['pnl_dollar'].sum() if len(wins) else 0
        gl = abs(df[df['pnl_dollar'] < 0]['pnl_dollar'].sum()) + 0.01
        caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['capital_after'].astype(float)]).reset_index(drop=True)
        max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
        c2.metric("Trades", len(df))
        c3.metric("Win Rate", f"{len(wins)/len(df)*100:.0f}%")
        c4.metric("Profit Factor", f"{gp/gl:.2f}")
        c5.metric("Max DD", f"{max_dd:.1f}%")
    else:
        c2.metric("Trades", "0")
        c3.metric("Win Rate", "—")
        c4.metric("Profit Factor", "—")
        c5.metric("Max DD", "—")

    st.divider()

    # ── POSITIONS OUVERTES ──
    st.subheader(f"Positions ouvertes ({len(positions)})")
    if positions:
        rows = []
        for p in positions:
            entry = p.get('entry', 0)
            stop = p.get('stop', 0)
            best = p.get('best', entry)
            atr = p.get('trade_atr', 1)
            risk_r = abs(best - entry) / abs(entry - stop) if abs(entry - stop) > 0 else 0
            rows.append({
                'Strat': p.get('strat', ''),
                'Nom': STRAT_NAMES.get(p.get('strat', ''), ''),
                'Dir': p.get('strat_dir', '').upper(),
                'Entree': f"{entry:.2f}",
                'Stop': f"{stop:.2f}",
                'Best': f"{best:.2f}",
                'Risk:Reward': f"{risk_r:.1f}R",
                'Trail': '🟢' if p.get('trail_active') else '⚪',
                'Barres': p.get('bars_held', 0),
                'Lots': f"{p.get('lots', 0):.3f}",
                'Spread': f"{p.get('entry_spread', 0):.3f}",
                'Heure entree': str(p.get('entry_time', ''))[:19],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(len(rows)*38+40, 400))
    else:
        st.info("Aucune position ouverte")

    st.divider()

    # ── TRADES FERMES ──
    st.subheader(f"Trades fermes ({len(trades)})")
    if not trades:
        st.warning("Aucun trade ferme. Attendez des signaux.")
    else:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df['duration'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60

        show = df.iloc[::-1].copy()
        show['Heure entree'] = show['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
        show['Heure sortie'] = show['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
        show['Strat'] = show['strat']
        show['Nom'] = show['strat'].map(STRAT_NAMES)
        show['Dir'] = show['dir'].str.upper()
        show['Entree'] = show['entry'].apply(lambda x: f"{x:.2f}")
        show['Sortie'] = show['exit'].apply(lambda x: f"{x:.2f}")
        show['PnL $'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
        show['PnL oz'] = show['pnl_oz'].apply(lambda x: f"{x:+.3f}")
        show['Barres'] = show['bars_held']
        show['Duree'] = show['duration'].apply(lambda x: f"{x:.0f}min")
        show['Raison'] = show['exit_reason']
        show['Capital'] = show['capital_after'].apply(lambda x: f"${float(x):,.2f}")

        display_cols = ['Heure entree', 'Heure sortie', 'Strat', 'Nom', 'Dir',
                        'Entree', 'Sortie', 'PnL $', 'PnL oz', 'Raison', 'Barres', 'Duree', 'Capital']
        display_df = show[display_cols]

        def color_row(row):
            try:
                val = float(row['PnL $'].replace('$','').replace(',','').replace('+',''))
                c = 'color: #26a69a' if val > 0 else 'color: #ef5350' if val < 0 else ''
            except: c = ''
            return [c] * len(row)

        st.dataframe(display_df.style.apply(color_row, axis=1),
                     use_container_width=True, hide_index=True,
                     height=min(len(display_df)*38+40, 800))

    # ── AUTO REFRESH ──
    if refresh > 0:
        time.sleep(refresh)
        st.rerun()

if __name__ == '__main__':
    main()
