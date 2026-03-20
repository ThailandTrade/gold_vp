"""
Dashboard Streamlit — VP Swing Paper Trading
streamlit run dashboard.py
"""
import streamlit as st
import json, os, time
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import itertools

LOG_FILE = "paper_trades.json"
CAPITAL_INITIAL = 1000.0
BACKTEST_PF = 1.82
BACKTEST_WR = 73
BACKTEST_DD = -8.9

STRAT_NAMES = {
    'AC':'Absorption Tokyo','D':'GAP Tokyo→London','E':'KZ London fade',
    'F':'2BAR Tokyo rev','G':'NY 1st candle','H':'TOKEND 3b',
    'I':'FADE NY 1h','O':'BigCandle Tokyo','P':'ORB NY 30min',
    'V':'CandleRatio Tokyo'
}
STRAT_SESSIONS = {
    'AC':'Tokyo','D':'London','E':'London','F':'Tokyo','G':'NY',
    'H':'London','I':'NY','O':'Tokyo','P':'NY','V':'Tokyo'
}

st.set_page_config(page_title="VP Swing", layout="wide", page_icon="📊")
st.markdown("""<style>
    .block-container{padding-top:0.5rem;}
    h1{font-size:1.8rem !important;}
    h2{font-size:1.3rem !important; margin-top:0.5rem !important;}
    h3{font-size:1.1rem !important; margin-top:0.3rem !important;}
</style>""", unsafe_allow_html=True)

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

def get_session():
    now = datetime.now(timezone.utc)
    h = now.hour
    if 0 <= h < 6: return "Tokyo", "🇯🇵"
    elif 6 <= h < 8: return "Gap", "⏳"
    elif 8 <= h < 14: return "London", "🇬🇧"
    elif 14 <= h < 21: return "New York", "🇺🇸"
    else: return "Ferme", "🌙"

def main():
    state = load_state()
    capital = state['capital']
    trades = state['trades']
    positions = state['open_positions']
    pnl_total = capital - CAPITAL_INITIAL
    current_price = get_current_price()
    session_name, session_emoji = get_session()
    now = datetime.now(timezone.utc)

    # ── BARRE DE STATUT ──
    cache = {}
    for k, v in state.get('daily_cache', {}).items(): cache = v; break
    status_parts = [
        f"{session_emoji} **{session_name}**",
        f"UTC {now.strftime('%H:%M')}",
    ]
    if current_price:
        status_parts.append(f"XAUUSD **${current_price['bid']:,.2f}**")
    if cache.get('atr'):
        status_parts.append(f"ATR ${cache['atr']:.2f}")
    status_parts.append(f"MAJ {state.get('_mtime','—')}")
    st.markdown(" | ".join(status_parts))

    # ── CAPITAL + RISQUE ──
    pnl_pct = pnl_total / CAPITAL_INITIAL * 100
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Capital", f"${capital:,.2f}", delta=f"{pnl_pct:+.1f}%")
    col2.metric("Positions", len(positions))

    if trades:
        df = pd.DataFrame(trades)
        df['pnl_dollar'] = df['pnl_dollar'].astype(float)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df['cum'] = df['capital_after'].astype(float)

        caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
        max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
        dd_current = (capital - caps.cummax().iloc[-1]) / caps.cummax().iloc[-1] * 100

        col3.metric("Drawdown actuel", f"{dd_current:.1f}%", delta=f"max {max_dd:.1f}%")

        # Aujourd'hui
        today = now.date()
        today_trades = df[df['entry_time'].dt.date == today]
        today_pnl = today_trades['pnl_dollar'].sum() if len(today_trades) else 0
        today_n = len(today_trades)
        today_w = (today_trades['pnl_dollar'] > 0).sum() if len(today_trades) else 0
        col4.metric(f"Aujourd'hui ({today_n} trades)", f"${today_pnl:+,.2f}",
                    delta=f"{today_w}W {today_n-today_w}L" if today_n else "pas de trade")
    else:
        col3.metric("Drawdown", "—")
        col4.metric("Aujourd'hui", "—")

    st.divider()

    # ── POSITIONS OUVERTES ──
    if positions:
        st.subheader(f"🔴 Positions ouvertes")
        for p in positions:
            entry = p.get('entry', 0); stop = p.get('stop', 0)
            best = p.get('best', entry); d = p.get('strat_dir', '')
            pos_oz = p.get('pos_oz', 0); bars = p.get('bars_held', 0)
            strat = p.get('strat', ''); atr = p.get('trade_atr', 1)
            trail = p.get('trail_active', False)

            # Calcul distances en ATR
            risk_atr = abs(entry - stop) / atr if atr else 0
            best_atr = abs(best - entry) / atr if atr else 0

            # Progress bar
            bars_pct = min(bars / 12, 1.0)

            if current_price:
                exit_price = current_price['bid'] if d == 'long' else current_price['ask']
                pnl_oz = (exit_price - entry) if d == 'long' else (entry - exit_price)
                pnl_dollar = pnl_oz * pos_oz
                pnl_atr = pnl_oz / atr if atr else 0
                color = "🟢" if pnl_dollar > 0 else "🔴"

                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"### {color} {strat} — {STRAT_NAMES.get(strat,'')} ({d.upper()})")
                    st.markdown(f"Entree **${entry:.2f}** → Prix **${exit_price:.2f}** | "
                                f"PnL **${pnl_dollar:+,.2f}** ({pnl_atr:+.1f} ATR)")
                with c2:
                    st.markdown(f"Stop **${stop:.2f}** ({risk_atr:.1f} ATR) | "
                                f"Best **${best:.2f}** ({best_atr:+.1f} ATR)")
                    st.markdown(f"Trail {'🟢 ACTIF' if trail else '⚪ inactif'} | "
                                f"{p.get('lots',0):.3f} lots | {str(p.get('entry_time',''))[:16]}")
                with c3:
                    st.progress(bars_pct, text=f"Bar {bars}/12")
            else:
                st.markdown(f"**{strat}** {d.upper()} | Entry ${entry:.2f} | Stop ${stop:.2f} | Bar {bars}/12")

        st.divider()

    # ── PAS DE TRADES ──
    if not trades:
        st.info("En attente du premier trade. Le live tourne et surveille les signaux.")

        # Strats attendues par session
        st.subheader("Strats attendues")
        for sess in ['Tokyo', 'London', 'NY']:
            strats = [f"**{s}** ({STRAT_NAMES[s]})" for s, se in STRAT_SESSIONS.items() if se == sess]
            active = "👉 " if session_name == sess else ""
            st.markdown(f"{active}**{sess}**: {', '.join(strats)}")

        with st.sidebar:
            if st.button("Reset"):
                reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                         'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
                with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
                st.rerun()
        time.sleep(10); st.rerun()
        return

    # ── EQUITY ──
    st.subheader("Equity")
    eq_data = pd.DataFrame({
        'Capital': [CAPITAL_INITIAL] + df['cum'].tolist()
    }, index=[df['entry_time'].iloc[0] - pd.Timedelta(hours=1)] + df['entry_time'].tolist())
    st.line_chart(eq_data, use_container_width=True, height=250)

    st.divider()

    # ── STATS LIVE vs BACKTEST ──
    wins = df[df['pnl_dollar'] > 0]; losses = df[df['pnl_dollar'] <= 0]
    gp = wins['pnl_dollar'].sum() if len(wins) else 0
    gl = abs(losses['pnl_dollar'].sum()) + 0.01
    live_pf = gp / gl
    live_wr = len(wins) / len(df) * 100

    st.subheader("Live vs Backtest")
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def metric_vs(col, label, live_val, bt_val, fmt=".2f", suffix=""):
        delta = live_val - bt_val
        col.metric(label, f"{live_val:{fmt}}{suffix}",
                   delta=f"{delta:+{fmt}} vs BT",
                   delta_color="normal" if delta >= 0 else "inverse")

    metric_vs(c1, "Profit Factor", live_pf, BACKTEST_PF)
    metric_vs(c2, "Win Rate", live_wr, BACKTEST_WR, ".0f", "%")
    metric_vs(c3, "Max DD", max_dd, BACKTEST_DD, ".1f", "%")
    c4.metric("Trades", len(df))
    c5.metric("Avg Win", f"${wins['pnl_dollar'].mean():+,.2f}" if len(wins) else "—")
    c6.metric("Avg Loss", f"${losses['pnl_dollar'].mean():+,.2f}" if len(losses) else "—")

    # Streaks
    loss_streaks = [sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar'] < 0) if k]
    win_streaks = [sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar'] > 0) if k]
    # Current streak
    current_streak = 0
    for p in df['pnl_dollar'].iloc[::-1]:
        if p > 0 and current_streak >= 0: current_streak += 1
        elif p <= 0 and current_streak <= 0: current_streak -= 1
        else: break
    streak_text = f"🟢 {current_streak} wins" if current_streak > 0 else f"🔴 {abs(current_streak)} losses" if current_streak < 0 else "—"
    st.caption(f"Streak actuelle: {streak_text} | "
               f"Max win streak: {max(win_streaks) if win_streaks else 0} | "
               f"Max loss streak: {max(loss_streaks) if loss_streaks else 0}")

    st.divider()

    # ── DERNIERS TRADES ──
    st.subheader("Derniers trades")
    show = df.iloc[::-1].head(30)
    for _, t in show.iterrows():
        pnl = t['pnl_dollar']
        color = "🟢" if pnl > 0 else "🔴"
        dt = t['entry_time'].strftime('%d/%m %H:%M')
        dur = (t['exit_time'] - t['entry_time']).total_seconds() / 60
        st.markdown(
            f"{color} **{t['strat']}** {t['dir'].upper()} | {dt} | "
            f"${t['entry']:.2f} → ${t['exit']:.2f} | "
            f"**${pnl:+,.2f}** | {t['exit_reason']} ({t['bars_held']} bars, {dur:.0f}min)")

    st.divider()

    # ── PAR STRATEGIE ──
    st.subheader("Performance par strategie")
    srows = []
    for sn in sorted(df['strat'].unique()):
        s = df[df['strat']==sn]; n = len(s)
        w = (s['pnl_dollar']>0).sum(); pnl = s['pnl_dollar'].sum()
        gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        srows.append({
            'Strat': sn, 'Nom': STRAT_NAMES.get(sn,''), 'Session': STRAT_SESSIONS.get(sn,''),
            'Trades': n, 'WR': f"{w/n*100:.0f}%", 'PF': f"{gps/gls:.2f}",
            'PnL': f"${pnl:+,.2f}", 'Avg': f"${pnl/n:+,.2f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    # PnL par strat bar chart
    st.bar_chart(df.groupby('strat')['pnl_dollar'].sum().sort_values(),
                 use_container_width=True, horizontal=True, height=250)

    st.divider()

    # ── PAR JOUR ──
    st.subheader("PnL journalier")
    daily = df.groupby('date').agg(
        trades=('pnl_dollar','count'),
        pnl=('pnl_dollar','sum'),
        wr=('pnl_dollar', lambda x: f"{(x>0).mean()*100:.0f}%")
    )
    st.bar_chart(daily['pnl'], use_container_width=True, height=200)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Long vs Short")
        for d_name in ['long','short']:
            s = df[df['dir']==d_name]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.metric(f"{d_name.upper()} ({len(s)})",
                      f"WR {w/len(s)*100:.0f}% | PF {gp_d/gl_d:.2f}",
                      delta=f"${s['pnl_dollar'].sum():+,.2f}")
    with col2:
        st.subheader("Par jour de la semaine")
        dow_names = {0:'Lun',1:'Mar',2:'Mer',3:'Jeu',4:'Ven'}
        df['dow'] = df['entry_time'].dt.dayofweek
        for dow in range(5):
            s = df[df['dow']==dow]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            st.caption(f"**{dow_names[dow]}**: {len(s)} trades, WR {w/len(s)*100:.0f}%, PnL ${s['pnl_dollar'].sum():+,.2f}")

    # ── SIDEBAR ──
    with st.sidebar:
        st.divider()
        if st.button("Reset paper trades"):
            reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                     'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
            with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
            st.success("Reset OK"); st.rerun()

    time.sleep(10)
    st.rerun()

if __name__ == '__main__':
    main()
