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

st.set_page_config(page_title="VP Swing Paper Trading", layout="wide", page_icon="📊")


def load_state():
    if os.path.exists(LOG_FILE):
        mtime = os.path.getmtime(LOG_FILE)
        with open(LOG_FILE, 'r') as f:
            state = json.load(f)
        state['_mtime'] = datetime.fromtimestamp(mtime).strftime("%H:%M:%S")
        return state
    return {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
            'daily_cache': {}, '_mtime': '—'}


def main():
    state = load_state()
    capital = state['capital']
    trades = state['trades']
    positions = state['open_positions']
    pnl_total = capital - CAPITAL_INITIAL
    cache = {}
    for k, v in state.get('daily_cache', {}).items():
        cache = v
        break

    # ── SIDEBAR ──
    with st.sidebar:
        st.title("⚙️ Config")
        st.metric("Capital initial", "${:,.0f}".format(CAPITAL_INITIAL))
        st.metric("Risque/trade", "1.0%")
        st.divider()
        if st.button("🗑️ Reset paper trades", type="secondary"):
            reset = {
                'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                'ib_levels': {}, 'prev_state_A': None, 'prev_va_ref_A': None,
                'last_trade_A_ts': 0, 'daily_cache': {}, 'last_candle_ts': 0,
            }
            import json
            with open(LOG_FILE, 'w') as f:
                json.dump(reset, f, indent=2)
            st.success("Reset OK — relancez live_paper.py")
            st.rerun()
        st.divider()
        st.caption("Fichier: {}".format(LOG_FILE))
        st.caption("Derniere MAJ: {}".format(state.get('_mtime', '—')))
        st.caption("Positions: {}".format(len(positions)))
        st.caption("Trades: {}".format(len(trades)))
        if cache:
            st.divider()
            st.caption("ATR: {}".format("{:.2f}".format(cache['atr']) if cache.get('atr') else "—"))
            st.caption("Spread RT: {}".format("{:.3f}".format(cache['spread_rt']) if cache.get('spread_rt') else "—"))
            st.caption("Strats: A,C,D,E,F,G,H,I,J,O,P,Q,R,S")

        refresh = st.selectbox("Refresh", [10, 30, 60], index=1)

    # ── HEADER ──
    st.title("📊 VP Swing — Paper Trading")

    # ── KPI ROW ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Capital", "${:,.2f}".format(capital), delta="${:+,.2f}".format(pnl_total))

    if trades:
        df = pd.DataFrame(trades)
        df['pnl_dollar'] = df['pnl_dollar'].astype(float)
        wins = df[df['pnl_dollar'] > 0]
        losses = df[df['pnl_dollar'] < 0]
        wr = len(wins) / len(df) * 100
        gp = wins['pnl_dollar'].sum() if len(wins) > 0 else 0
        gl = abs(losses['pnl_dollar'].sum()) + 0.01
        pf = gp / gl

        c2.metric("Win Rate", "{:.1f}%".format(wr))
        c3.metric("Profit Factor", "{:.2f}".format(pf))
        c4.metric("Trades", str(len(df)))

        # Max consec losses
        max_cl = max((sum(1 for _ in g) for k, g in
                      itertools.groupby(df['pnl_dollar'] < 0) if k), default=0)
        c5.metric("Max pertes consec", str(max_cl))

        # DD — equity = capital_after reel, avec capital initial comme point de depart
        caps = [CAPITAL_INITIAL] + df['capital_after'].astype(float).tolist()
        caps = pd.Series(caps)
        peak = caps.cummax()
        dd_all = (caps - peak) / peak * 100
        max_dd = dd_all.min()
        # Pour l'equity chart, garder cum sur df
        df['cum'] = df['capital_after'].astype(float)
        c6.metric("Max DD", "{:.2f}%".format(max_dd))
    else:
        c2.metric("Win Rate", "—")
        c3.metric("Profit Factor", "—")
        c4.metric("Trades", "0")
        c5.metric("Max pertes consec", "—")
        c6.metric("Max DD", "—")

    st.divider()

    # ── POSITIONS OUVERTES ──
    st.subheader("🔴 Positions ouvertes ({})".format(len(positions)))
    if positions:
        pos_rows = []
        for p in positions:
            unrealized = "—"
            pos_rows.append({
                'Strat': p.get('strat', ''),
                'Dir': p.get('strat_dir', '').upper(),
                'Entree': "{:.2f}".format(p.get('entry', 0)),
                'Stop': "{:.2f}".format(p.get('stop', 0)),
                'Best': "{:.2f}".format(p.get('best', p.get('entry', 0))),
                'Trail': '🟢' if p.get('trail_active') else '⚪',
                'Barres': p.get('bars_held', 0),
                'Lots': "{:.3f}".format(p.get('lots', 0)),
                'ATR trade': "{:.2f}".format(p.get('trade_atr', 0)),
                'Spread entree': "{:.3f}".format(p.get('entry_spread', 0)),
                'Heure': str(p.get('entry_time', ''))[:16],
            })
        st.dataframe(pd.DataFrame(pos_rows), width='stretch', hide_index=True)
    else:
        st.info("Aucune position ouverte")

    if not trades:
        st.divider()
        st.warning("Aucun trade ferme. Lancez live_paper.py et attendez des signaux.")
        time.sleep(refresh)
        st.rerun()
        return

    st.divider()

    # ── EQUITY + DRAWDOWN ──
    df['entry_time'] = pd.to_datetime(df['entry_time'])

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📈 Equity Curve")
        eq_chart = df[['entry_time', 'cum']].set_index('entry_time')
        eq_chart.columns = ['Capital']
        st.line_chart(eq_chart, width='stretch')

    with col_chart2:
        st.subheader("📉 Drawdown")
        df['peak'] = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).cummax().iloc[1:].reset_index(drop=True)
        df['dd_pct'] = (df['cum'] - df['peak']) / df['peak'] * 100
        dd_chart = df[['entry_time', 'dd_pct']].set_index('entry_time')
        dd_chart.columns = ['DD %']
        st.area_chart(dd_chart, width='stretch', color='#ff4b4b')

    st.divider()

    # ── PAR STRATEGIE ──
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.subheader("📋 Performance par strategie")
        strat_rows = []
        for strat in sorted(df['strat'].unique()):
            s = df[df['strat'] == strat]
            n = len(s)
            w = (s['pnl_dollar'] > 0).sum()
            pnl = s['pnl_dollar'].sum()
            gp_s = s[s['pnl_dollar'] > 0]['pnl_dollar'].sum()
            gl_s = abs(s[s['pnl_dollar'] < 0]['pnl_dollar'].sum()) + 0.01
            strat_rows.append({
                'Strat': strat,
                'Trades': n,
                'WR': "{:.0f}%".format(w / n * 100),
                'PF': "{:.2f}".format(gp_s / gl_s),
                'PnL': "${:+,.2f}".format(pnl),
                'Avg': "${:+,.2f}".format(pnl / n),
            })
        st.dataframe(pd.DataFrame(strat_rows), width='stretch', hide_index=True)

    with col_s2:
        st.subheader("💰 PnL par strategie")
        strat_pnl = df.groupby('strat')['pnl_dollar'].sum()
        st.bar_chart(strat_pnl, width='stretch')

    st.divider()

    # ── PAR JOUR / PAR DIRECTION ──
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.subheader("📅 PnL par jour")
        df['date'] = df['entry_time'].dt.date
        daily = df.groupby('date')['pnl_dollar'].sum()
        colors = ['#26a69a' if v > 0 else '#ef5350' for v in daily.values]
        st.bar_chart(daily, width='stretch')

    with col_d2:
        st.subheader("↕️ Par direction")
        dir_rows = []
        for d in ['long', 'short']:
            s = df[df['dir'] == d]
            if len(s) == 0:
                continue
            w = (s['pnl_dollar'] > 0).sum()
            pnl = s['pnl_dollar'].sum()
            dir_rows.append({
                'Direction': d.upper(),
                'Trades': len(s),
                'WR': "{:.0f}%".format(w / len(s) * 100),
                'PnL': "${:+,.2f}".format(pnl),
            })
        st.dataframe(pd.DataFrame(dir_rows), width='stretch', hide_index=True)

        # Exit reasons
        st.subheader("🚪 Raisons de sortie")
        exit_counts = df['exit_reason'].value_counts()
        st.bar_chart(exit_counts, width='stretch')

    st.divider()

    # ── PNL MENSUEL ──
    st.subheader("📆 PnL mensuel")
    df['month'] = df['entry_time'].dt.strftime('%Y-%m')
    monthly = df.groupby('month').agg(
        trades=('pnl_dollar', 'count'),
        pnl=('pnl_dollar', 'sum'),
        wr=('pnl_dollar', lambda x: (x > 0).mean() * 100)
    ).round(1)
    monthly['pnl_fmt'] = monthly['pnl'].apply(lambda x: "${:+,.2f}".format(x))
    monthly['wr_fmt'] = monthly['wr'].apply(lambda x: "{:.0f}%".format(x))

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        st.bar_chart(monthly['pnl'], width='stretch')
    with col_m2:
        display_monthly = monthly[['trades', 'pnl_fmt', 'wr_fmt']].copy()
        display_monthly.columns = ['Trades', 'PnL', 'WR']
        st.dataframe(display_monthly, width='stretch')

    st.divider()

    # ── DISTRIBUTION ──
    st.subheader("📊 Distribution des PnL")
    col_h1, col_h2 = st.columns(2)

    with col_h1:
        # Histogram
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4))
        pnls = df['pnl_dollar'].values
        ax.hist(pnls, bins=30, color=['#26a69a' if x > 0 else '#ef5350' for x in sorted(pnls)],
                edgecolor='white', alpha=0.8)
        ax.axvline(0, color='white', linestyle='--', alpha=0.5)
        ax.set_xlabel('PnL ($)')
        ax.set_ylabel('Frequence')
        ax.set_facecolor('#0e1117')
        fig.patch.set_facecolor('#0e1117')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        st.pyplot(fig)

    with col_h2:
        st.caption("Statistiques")
        stats = {
            'Moyenne': "${:+,.2f}".format(pnls.mean()),
            'Mediane': "${:+,.2f}".format(np.median(pnls)),
            'Ecart-type': "${:,.2f}".format(pnls.std()),
            'Best trade': "${:+,.2f}".format(pnls.max()),
            'Worst trade': "${:+,.2f}".format(pnls.min()),
            'Avg win': "${:+,.2f}".format(pnls[pnls > 0].mean()) if len(pnls[pnls > 0]) > 0 else "—",
            'Avg loss': "${:+,.2f}".format(pnls[pnls < 0].mean()) if len(pnls[pnls < 0]) > 0 else "—",
            'Win/Loss ratio': "{:.2f}".format(
                abs(pnls[pnls > 0].mean() / pnls[pnls < 0].mean())
                if len(pnls[pnls > 0]) > 0 and len(pnls[pnls < 0]) > 0 else 0),
        }
        st.dataframe(pd.DataFrame(stats.items(), columns=['Metric', 'Value']),
                     width='stretch', hide_index=True)

    st.divider()

    # ── DERNIERS TRADES ──
    st.subheader("🕐 Derniers trades")
    n_show = st.slider("Trades a afficher", 5, min(100, len(df)), 20)

    show = df.tail(n_show).iloc[::-1].copy()
    show['entry_time'] = show['entry_time'].dt.strftime('%m-%d %H:%M')
    show['PnL'] = show['pnl_dollar'].apply(lambda x: "${:+,.2f}".format(x))
    show['Entry'] = show['entry'].apply(lambda x: "{:.2f}".format(x))
    show['Exit'] = show['exit'].apply(lambda x: "{:.2f}".format(x))

    display_cols = ['entry_time', 'strat', 'dir', 'Entry', 'Exit', 'PnL',
                    'exit_reason', 'bars_held']
    display_df = show[display_cols].copy()
    display_df.columns = ['Heure', 'Strat', 'Dir', 'Entree', 'Sortie', 'PnL',
                          'Raison', 'Barres']

    def highlight_pnl(row):
        pnl_val = float(row['PnL'].replace('$', '').replace(',', '').replace('+', ''))
        color = 'color: #26a69a' if pnl_val > 0 else 'color: #ef5350' if pnl_val < 0 else ''
        return [color] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_pnl, axis=1),
        width='stretch', hide_index=True, height=min(n_show * 35 + 40, 700)
    )

    # ── AUTO REFRESH ──
    time.sleep(refresh)
    st.rerun()


if __name__ == '__main__':
    main()
