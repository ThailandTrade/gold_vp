"""
Dashboard Streamlit — VP Swing Paper Trading
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
    'AC':'Absorption Tokyo','D':'GAP Tokyo→London','E':'KZ London fade',
    'F':'2BAR Tokyo rev','G':'NY 1st candle','H':'TOKEND 3b',
    'I':'FADE NY 1h','O':'BigCandle Tokyo','P':'ORB NY 30min',
    'V':'CandleRatio Tokyo'
}

st.set_page_config(page_title="VP Swing", layout="wide", page_icon="📊")

def load_state():
    if os.path.exists(LOG_FILE):
        mtime = os.path.getmtime(LOG_FILE)
        with open(LOG_FILE, 'r') as f: state = json.load(f)
        state['_mtime'] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        return state
    return {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
            'daily_cache': {}, '_mtime': '—'}

def get_current_price():
    try:
        from phase1_poc_calculator import get_conn
        conn_db = get_conn(); conn_db.autocommit = True
        cur = conn_db.cursor()
        cur.execute("SELECT bid, ask FROM market_ticks_xauusd ORDER BY ts DESC LIMIT 1")
        row = cur.fetchone(); cur.close(); conn_db.close()
        if row: return {'bid': float(row[0]), 'ask': float(row[1])}
    except: pass
    return None

def main():
    state = load_state()
    capital = state['capital']
    trades = state['trades']
    positions = state['open_positions']
    pnl_total = capital - CAPITAL_INITIAL
    current_price = get_current_price()

    # ── HEADER ──
    st.title("XAUUSD 5m — Paper Trading")
    st.caption(f"10 strats (AC,D,E,F,G,H,I,O,P,V) | Trailing pessimiste SL=1.5 ACT=0.3 TRAIL=0.3 T12 | MAJ: {state.get('_mtime','—')}")

    # ── RESUME EN HAUT ──
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        st.metric("Capital", f"${capital:,.2f}", delta=f"${pnl_total:+,.2f}")
    with col2:
        if current_price:
            st.metric("XAUUSD", f"${current_price['bid']:,.2f}",
                      delta=f"spread ${current_price['ask']-current_price['bid']:.3f}")
        else:
            st.metric("XAUUSD", "—")
    with col3:
        cache = {}
        for k, v in state.get('daily_cache', {}).items(): cache = v; break
        st.metric("ATR (veille)", f"${cache['atr']:.2f}" if cache.get('atr') else "—")

    st.divider()

    # ── POSITIONS OUVERTES ──
    if positions:
        st.subheader(f"🔴 {len(positions)} position(s) ouverte(s)")
        total_unrealized = 0
        for p in positions:
            entry = p.get('entry', 0); stop = p.get('stop', 0)
            best = p.get('best', entry); d = p.get('strat_dir', '')
            pos_oz = p.get('pos_oz', 0); bars = p.get('bars_held', 0)
            strat = p.get('strat', '')
            trail = "ACTIF" if p.get('trail_active') else "inactif"

            if current_price:
                exit_price = current_price['bid'] if d == 'long' else current_price['ask']
                pnl_oz = (exit_price - entry) if d == 'long' else (entry - exit_price)
                pnl_dollar = pnl_oz * pos_oz
                total_unrealized += pnl_dollar
                color = "🟢" if pnl_dollar > 0 else "🔴"
                st.markdown(f"""
                **{color} {strat}** ({STRAT_NAMES.get(strat,'')}) — **{d.upper()}** depuis {str(p.get('entry_time',''))[:16]}
                - Entree: **${entry:.2f}** | Prix: **${exit_price:.2f}** | Stop: **${stop:.2f}** | Best: **${best:.2f}**
                - PnL: **${pnl_dollar:+,.2f}** ({pnl_oz:+.2f} oz) | Trail: {trail} | Bars: {bars}/12 | {p.get('lots',0):.3f} lots
                """)
            else:
                st.markdown(f"**{strat}** ({STRAT_NAMES.get(strat,'')}) — **{d.upper()}** | Entry: ${entry:.2f} | Stop: ${stop:.2f} | Bars: {bars}")

        if current_price:
            color = "🟢" if total_unrealized > 0 else "🔴"
            st.markdown(f"**{color} PnL latent total: ${total_unrealized:+,.2f}**")
        st.divider()

    # ── PAS DE TRADES FERMES ──
    if not trades:
        st.info("Aucun trade ferme. Le live tourne et attend des signaux.")
        with st.sidebar:
            refresh = st.selectbox("Refresh", [10, 30, 60], index=0)
            if st.button("Reset"):
                reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                         'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
                with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
                st.rerun()
        time.sleep(refresh); st.rerun()
        return

    # ── TRADES FERMES: construire le DataFrame ──
    df = pd.DataFrame(trades)
    df['pnl_dollar'] = df['pnl_dollar'].astype(float)
    df['pnl_oz'] = df['pnl_oz'].astype(float)
    df['entry'] = df['entry'].astype(float)
    df['exit'] = df['exit'].astype(float)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['cum'] = df['capital_after'].astype(float)
    df['date'] = df['entry_time'].dt.date
    df['duration_min'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60

    wins = df[df['pnl_dollar'] > 0]
    losses = df[df['pnl_dollar'] <= 0]
    gp = wins['pnl_dollar'].sum() if len(wins) else 0
    gl = abs(losses['pnl_dollar'].sum()) + 0.01
    caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
    max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()

    # ── PERFORMANCE GLOBALE ──
    st.subheader("Performance")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Trades", len(df))
    c2.metric("Win Rate", f"{len(wins)/len(df)*100:.0f}%")
    c3.metric("Profit Factor", f"{gp/gl:.2f}")
    c4.metric("Avg Win", f"${wins['pnl_dollar'].mean():+,.2f}" if len(wins) else "—")
    c5.metric("Avg Loss", f"${losses['pnl_dollar'].mean():+,.2f}" if len(losses) else "—")
    c6.metric("Max Drawdown", f"{max_dd:.1f}%")

    st.divider()

    # ── EQUITY CURVE ──
    st.subheader("Equity")
    eq_data = pd.DataFrame({
        'Capital': [CAPITAL_INITIAL] + df['cum'].tolist()
    }, index=[df['entry_time'].iloc[0] - pd.Timedelta(hours=1)] + df['entry_time'].tolist())
    st.line_chart(eq_data, use_container_width=True, height=300)

    st.divider()

    # ── DERNIERS TRADES ──
    st.subheader("Derniers trades")
    show = df.iloc[::-1].head(20).copy()
    for _, t in show.iterrows():
        pnl = t['pnl_dollar']
        color = "🟢" if pnl > 0 else "🔴"
        dt = t['entry_time'].strftime('%d/%m %H:%M')
        dur = f"{t['duration_min']:.0f}min"
        st.markdown(
            f"{color} **{t['strat']}** {t['dir'].upper()} | {dt} | "
            f"${t['entry']:.2f} → ${t['exit']:.2f} | "
            f"**${pnl:+,.2f}** | {t['exit_reason']} | {t['bars_held']} bars ({dur})"
        )

    st.divider()

    # ── STATS PAR STRATEGIE ──
    st.subheader("Par strategie")
    srows = []
    for sn in sorted(df['strat'].unique()):
        s = df[df['strat']==sn]; n = len(s)
        w = (s['pnl_dollar']>0).sum(); pnl = s['pnl_dollar'].sum()
        gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        srows.append({
            'Strat': sn, 'Nom': STRAT_NAMES.get(sn,''),
            'Trades': n, 'WR': f"{w/n*100:.0f}%", 'PF': f"{gps/gls:.2f}",
            'PnL': f"${pnl:+,.2f}", 'Avg': f"${pnl/n:+,.2f}",
            'Meilleur': f"${s['pnl_dollar'].max():+,.2f}",
            'Pire': f"${s['pnl_dollar'].min():+,.2f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    st.divider()

    # ── REPARTITION LONG/SHORT ──
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Long vs Short")
        for d in ['long','short']:
            s = df[df['dir']==d]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.metric(f"{d.upper()} ({len(s)} trades)",
                      f"WR {w/len(s)*100:.0f}% | PF {gp_d/gl_d:.2f}",
                      delta=f"${s['pnl_dollar'].sum():+,.2f}")

    with col2:
        st.subheader("Raisons de sortie")
        for reason in df['exit_reason'].unique():
            s = df[df['exit_reason']==reason]
            w = (s['pnl_dollar']>0).sum()
            st.markdown(f"**{reason}**: {len(s)} trades ({w} wins, {len(s)-w} losses)")

    # ── SIDEBAR ──
    with st.sidebar:
        st.divider()
        refresh = st.selectbox("Refresh (sec)", [10, 30, 60], index=0)
        if st.button("Reset paper trades"):
            reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                     'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
            with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
            st.success("Reset OK"); st.rerun()

    time.sleep(refresh)
    st.rerun()

if __name__ == '__main__':
    main()
