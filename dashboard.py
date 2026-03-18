"""
Dashboard Streamlit Pro — Paper Trading VP Swing
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

st.set_page_config(page_title="VP Swing Dashboard", layout="wide", page_icon="📊")

# ── CSS ──
st.markdown("""<style>
    .block-container{padding-top:1rem;}
    [data-testid="stMetricValue"]{font-size:1.3rem;}
    [data-testid="stMetricDelta"]{font-size:0.9rem;}
</style>""", unsafe_allow_html=True)

def load_state():
    if os.path.exists(LOG_FILE):
        mtime = os.path.getmtime(LOG_FILE)
        with open(LOG_FILE, 'r') as f: state = json.load(f)
        state['_mtime'] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        return state
    return {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
            'daily_cache': {}, '_mtime': '—'}

def build_df(trades):
    if not trades: return None
    df = pd.DataFrame(trades)
    df['pnl_dollar'] = df['pnl_dollar'].astype(float)
    df['entry'] = df['entry'].astype(float)
    df['exit'] = df['exit'].astype(float)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['cum'] = df['capital_after'].astype(float)
    df['date'] = df['entry_time'].dt.date
    df['month'] = df['entry_time'].dt.strftime('%Y-%m')
    df['hour'] = df['entry_time'].dt.hour
    df['dow'] = df['entry_time'].dt.dayofweek
    df['duration_min'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60
    df['pnl_atr'] = df['pnl_oz'] / df['exit'].apply(lambda x: 1)  # approx
    # DD
    caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
    peak = caps.cummax()
    dd = (caps - peak) / peak * 100
    df['dd_pct'] = dd.iloc[1:].values
    df['peak'] = peak.iloc[1:].values
    return df

def kpi_bar(df, capital):
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    pnl = capital - CAPITAL_INITIAL
    c1.metric("Capital", f"${capital:,.2f}", delta=f"${pnl:+,.2f}")
    if df is not None and len(df) > 0:
        wins = df[df['pnl_dollar'] > 0]; losses = df[df['pnl_dollar'] < 0]
        wr = len(wins)/len(df)*100
        gp = wins['pnl_dollar'].sum() if len(wins) else 0
        gl = abs(losses['pnl_dollar'].sum()) + 0.01
        max_cl = max((sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar'] < 0) if k), default=0)
        caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
        max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
        c2.metric("Win Rate", f"{wr:.1f}%")
        c3.metric("Profit Factor", f"{gp/gl:.2f}")
        c4.metric("Trades", str(len(df)))
        c5.metric("Avg Trade", f"${df['pnl_dollar'].mean():+,.2f}")
        c6.metric("Best", f"${df['pnl_dollar'].max():+,.2f}")
        c7.metric("Worst", f"${df['pnl_dollar'].min():+,.2f}")
        c8.metric("Max DD", f"{max_dd:.2f}%")

def tab_overview(df, positions):
    st.subheader("Positions ouvertes" + (f" ({len(positions)})" if positions else ""))
    if positions:
        rows = []
        for p in positions:
            rows.append({
                'Strat': p.get('strat',''),
                'Nom': STRAT_NAMES.get(p.get('strat',''),''),
                'Dir': p.get('strat_dir','').upper(),
                'Entree': f"{p.get('entry',0):.2f}",
                'Stop': f"{p.get('stop',0):.2f}",
                'Best': f"{p.get('best',p.get('entry',0)):.2f}",
                'Trail': '🟢 ON' if p.get('trail_active') else '⚪ off',
                'Barres': p.get('bars_held',0),
                'Lots': f"{p.get('lots',0):.3f}",
                'Heure': str(p.get('entry_time',''))[:16],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune position ouverte")

    if df is None or len(df) == 0:
        st.warning("Aucun trade ferme.")
        return

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Equity Curve")
        eq = df[['entry_time','cum']].set_index('entry_time')
        eq.columns = ['Capital']
        st.line_chart(eq, use_container_width=True)
    with col2:
        st.subheader("Drawdown")
        dd = df[['entry_time','dd_pct']].set_index('entry_time')
        dd.columns = ['DD %']
        st.area_chart(dd, use_container_width=True, color='#ff4b4b')

def tab_strategies(df):
    if df is None or len(df) == 0: st.warning("Pas de trades"); return

    st.subheader("Performance par strategie")
    rows = []
    for strat in sorted(df['strat'].unique()):
        s = df[df['strat']==strat]; n = len(s)
        w = (s['pnl_dollar']>0).sum(); pnl = s['pnl_dollar'].sum()
        gp = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gl = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        rows.append({
            'Strat': strat,
            'Nom': STRAT_NAMES.get(strat, '?'),
            'Trades': n,
            'WR': f"{w/n*100:.0f}%",
            'PF': f"{gp/gl:.2f}",
            'PnL': f"${pnl:+,.2f}",
            'Avg': f"${pnl/n:+,.2f}",
            'Best': f"${s['pnl_dollar'].max():+,.2f}",
            'Worst': f"${s['pnl_dollar'].min():+,.2f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("PnL par strategie")
        chart_data = df.groupby('strat')['pnl_dollar'].sum().sort_values(ascending=True)
        st.bar_chart(chart_data, use_container_width=True, horizontal=True)
    with col2:
        st.subheader("Nombre de trades")
        chart_data2 = df.groupby('strat')['pnl_dollar'].count().sort_values(ascending=True)
        st.bar_chart(chart_data2, use_container_width=True, horizontal=True)

    st.divider()
    st.subheader("Equity par strategie")
    strat_select = st.multiselect("Strategies", sorted(df['strat'].unique()),
                                   default=sorted(df['strat'].unique())[:5])
    if strat_select:
        eq_strats = pd.DataFrame()
        for sn in strat_select:
            s = df[df['strat']==sn].copy()
            s['cum_strat'] = s['pnl_dollar'].cumsum()
            eq_strats[sn] = s.set_index('entry_time')['cum_strat']
        eq_strats = eq_strats.fillna(method='ffill').fillna(0)
        st.line_chart(eq_strats, use_container_width=True)

def tab_calendar(df):
    if df is None or len(df) == 0: st.warning("Pas de trades"); return

    st.subheader("PnL mensuel")
    monthly = df.groupby('month').agg(
        trades=('pnl_dollar','count'),
        pnl=('pnl_dollar','sum'),
        wr=('pnl_dollar', lambda x: (x>0).mean()*100),
        avg=('pnl_dollar','mean'),
        best=('pnl_dollar','max'),
        worst=('pnl_dollar','min'),
    ).round(2)
    col1, col2 = st.columns([2,1])
    with col1:
        st.bar_chart(monthly['pnl'], use_container_width=True)
    with col2:
        display = monthly.copy()
        display['pnl'] = display['pnl'].apply(lambda x: f"${x:+,.2f}")
        display['avg'] = display['avg'].apply(lambda x: f"${x:+,.2f}")
        display['wr'] = display['wr'].apply(lambda x: f"{x:.0f}%")
        display.columns = ['Trades','PnL','WR','Avg','Best','Worst']
        st.dataframe(display, use_container_width=True)

    st.divider()
    st.subheader("PnL journalier")
    daily = df.groupby('date').agg(
        trades=('pnl_dollar','count'),
        pnl=('pnl_dollar','sum'),
    )
    st.bar_chart(daily['pnl'], use_container_width=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Par jour de la semaine")
        dow_names = {0:'Lundi',1:'Mardi',2:'Mercredi',3:'Jeudi',4:'Vendredi'}
        dow_rows = []
        for dow in range(5):
            s = df[df['dow']==dow]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            dow_rows.append({
                'Jour': dow_names[dow],
                'Trades': len(s),
                'WR': f"{w/len(s)*100:.0f}%",
                'PF': f"{gp/gl:.2f}",
                'PnL': f"${s['pnl_dollar'].sum():+,.2f}",
            })
        st.dataframe(pd.DataFrame(dow_rows), use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Par heure d'entree (UTC)")
        hour_rows = []
        for h in sorted(df['hour'].unique()):
            s = df[df['hour']==h]
            if len(s) < 3: continue
            w = (s['pnl_dollar']>0).sum()
            gp = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            hour_rows.append({
                'Heure': f"{h:02d}h",
                'Trades': len(s),
                'WR': f"{w/len(s)*100:.0f}%",
                'PF': f"{gp/gl:.2f}",
                'PnL': f"${s['pnl_dollar'].sum():+,.2f}",
            })
        st.dataframe(pd.DataFrame(hour_rows), use_container_width=True, hide_index=True)

def tab_analysis(df):
    if df is None or len(df) == 0: st.warning("Pas de trades"); return

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Long vs Short")
        for d in ['long','short']:
            s = df[df['dir']==d]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.metric(f"{d.upper()} ({len(s)} trades)",
                      f"PF {gp/gl:.2f} | WR {w/len(s)*100:.0f}%",
                      delta=f"${s['pnl_dollar'].sum():+,.2f}")

    with col2:
        st.subheader("Raisons de sortie")
        exit_rows = []
        for reason in df['exit_reason'].unique():
            s = df[df['exit_reason']==reason]
            w = (s['pnl_dollar']>0).sum()
            gp = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            exit_rows.append({
                'Raison': reason,
                'Trades': len(s),
                'WR': f"{w/len(s)*100:.0f}%",
                'PF': f"{gp/gl:.2f}",
                'PnL': f"${s['pnl_dollar'].sum():+,.2f}",
            })
        st.dataframe(pd.DataFrame(exit_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Distribution des PnL")
    col1, col2 = st.columns(2)
    with col1:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4))
        pnls = df['pnl_dollar'].values
        pos = pnls[pnls > 0]; neg = pnls[pnls <= 0]
        bins = np.linspace(pnls.min(), pnls.max(), 31)
        if len(neg): ax.hist(neg, bins=bins, color='#ef5350', edgecolor='white', alpha=0.8, label='Loss')
        if len(pos): ax.hist(pos, bins=bins, color='#26a69a', edgecolor='white', alpha=0.8, label='Win')
        ax.axvline(0, color='white', linestyle='--', alpha=0.5)
        ax.legend(); ax.set_xlabel('PnL ($)'); ax.set_ylabel('Frequence')
        ax.set_facecolor('#0e1117'); fig.patch.set_facecolor('#0e1117')
        ax.tick_params(colors='white'); ax.xaxis.label.set_color('white'); ax.yaxis.label.set_color('white')
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.legend(facecolor='#0e1117', labelcolor='white')
        st.pyplot(fig)
        plt.close(fig)

    with col2:
        stats = {
            'Moyenne': f"${pnls.mean():+,.2f}",
            'Mediane': f"${np.median(pnls):+,.2f}",
            'Ecart-type': f"${pnls.std():,.2f}",
            'Skewness': f"{pd.Series(pnls).skew():+.2f}",
            'Best trade': f"${pnls.max():+,.2f}",
            'Worst trade': f"${pnls.min():+,.2f}",
            'Avg win': f"${pnls[pnls>0].mean():+,.2f}" if len(pnls[pnls>0]) else "—",
            'Avg loss': f"${pnls[pnls<0].mean():+,.2f}" if len(pnls[pnls<0]) else "—",
            'Win/Loss ratio': f"{abs(pnls[pnls>0].mean()/pnls[pnls<0].mean()):.2f}" if len(pnls[pnls>0])>0 and len(pnls[pnls<0])>0 else "—",
            'Expectancy': f"${pnls.mean():+,.2f}",
        }
        st.dataframe(pd.DataFrame(stats.items(), columns=['Metrique','Valeur']),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Streaks")
    col1, col2 = st.columns(2)
    losses_seq = [t < 0 for t in df['pnl_dollar']]
    max_loss_streak = max((sum(1 for _ in g) for k, g in itertools.groupby(losses_seq) if k), default=0)
    max_win_streak = max((sum(1 for _ in g) for k, g in itertools.groupby(losses_seq) if not k), default=0)
    daily_pnl = df.groupby('date')['pnl_dollar'].sum()
    max_neg_days = max((sum(1 for _ in g) for k, g in itertools.groupby(daily_pnl < 0) if k), default=0)
    max_pos_days = max((sum(1 for _ in g) for k, g in itertools.groupby(daily_pnl > 0) if k), default=0)
    with col1:
        st.metric("Max pertes consecutives", max_loss_streak)
        st.metric("Max gains consecutifs", max_win_streak)
    with col2:
        st.metric("Max jours negatifs", max_neg_days)
        st.metric("Max jours positifs", max_pos_days)

def tab_trades(df):
    if df is None or len(df) == 0: st.warning("Pas de trades"); return

    col1, col2 = st.columns([1,3])
    with col1:
        total = len(df)
        if total <= 5:
            n_show = total
        else:
            n_show = st.slider("Nombre", 5, min(500, total), min(50, total))
        strat_filter = st.multiselect("Filtrer strats", sorted(df['strat'].unique()))
        dir_filter = st.radio("Direction", ['Tous','Long','Short'], horizontal=True)
        result_filter = st.radio("Resultat", ['Tous','Gagnants','Perdants'], horizontal=True)

    filtered = df.copy()
    if strat_filter: filtered = filtered[filtered['strat'].isin(strat_filter)]
    if dir_filter == 'Long': filtered = filtered[filtered['dir']=='long']
    elif dir_filter == 'Short': filtered = filtered[filtered['dir']=='short']
    if result_filter == 'Gagnants': filtered = filtered[filtered['pnl_dollar']>0]
    elif result_filter == 'Perdants': filtered = filtered[filtered['pnl_dollar']<0]

    with col2:
        if len(filtered) == 0:
            st.warning("Aucun trade avec ces filtres")
            return

        show = filtered.tail(n_show).iloc[::-1].copy()
        show['Heure'] = show['entry_time'].dt.strftime('%m-%d %H:%M')
        show['Nom'] = show['strat'].map(STRAT_NAMES)
        show['Dir'] = show['dir'].str.upper()
        show['Entree'] = show['entry'].apply(lambda x: f"{x:.2f}")
        show['Sortie'] = show['exit'].apply(lambda x: f"{x:.2f}")
        show['PnL'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
        show['Barres'] = show['bars_held']
        show['Raison'] = show['exit_reason']
        show['Duree'] = show['duration_min'].apply(lambda x: f"{x:.0f}min")

        display_cols = ['Heure','strat','Nom','Dir','Entree','Sortie','PnL','Raison','Barres','Duree']
        display_df = show[display_cols].copy()
        display_df.columns = ['Heure','Strat','Nom','Dir','Entree','Sortie','PnL','Raison','Barres','Duree']

        def color_pnl(row):
            try:
                val = float(row['PnL'].replace('$','').replace(',','').replace('+',''))
                c = 'color: #26a69a' if val > 0 else 'color: #ef5350' if val < 0 else ''
            except: c = ''
            return [c]*len(row)

        st.dataframe(display_df.style.apply(color_pnl, axis=1),
                     use_container_width=True, hide_index=True,
                     height=min(n_show*35+40, 800))

        # Stats du filtre
        st.caption(f"Filtre: {len(filtered)} trades | WR {(filtered['pnl_dollar']>0).mean()*100:.0f}% | "
                   f"PnL ${filtered['pnl_dollar'].sum():+,.2f} | "
                   f"Avg ${filtered['pnl_dollar'].mean():+,.2f}")

def tab_sessions(df):
    if df is None or len(df) == 0: st.warning("Pas de trades"); return

    st.subheader("Performance par session")
    def get_session(hour):
        if 0 <= hour < 6: return 'Tokyo'
        elif 8 <= hour < 15: return 'London'
        elif 14 <= hour < 22: return 'New York'
        else: return 'Autre'

    df_sess = df.copy()
    df_sess['session'] = df_sess['hour'].apply(get_session)

    rows = []
    for sess in ['Tokyo','London','New York']:
        s = df_sess[df_sess['session']==sess]
        if len(s) == 0: continue
        w = (s['pnl_dollar']>0).sum()
        gp = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gl = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        rows.append({
            'Session': sess,
            'Trades': len(s),
            'WR': f"{w/len(s)*100:.0f}%",
            'PF': f"{gp/gl:.2f}",
            'PnL': f"${s['pnl_dollar'].sum():+,.2f}",
            'Avg': f"${s['pnl_dollar'].mean():+,.2f}",
            'Strats': ', '.join(sorted(s['strat'].unique())),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("PnL cumule par session")
    eq_sess = pd.DataFrame()
    for sess in ['Tokyo','London','New York']:
        s = df_sess[df_sess['session']==sess].copy()
        if len(s) == 0: continue
        s['cum_sess'] = s['pnl_dollar'].cumsum()
        eq_sess[sess] = s.set_index('entry_time')['cum_sess']
    eq_sess = eq_sess.fillna(method='ffill').fillna(0)
    st.line_chart(eq_sess, use_container_width=True)

# ── MAIN ──
def main():
    state = load_state()
    capital = state['capital']
    trades = state['trades']
    positions = state['open_positions']
    df = build_df(trades)

    # Sidebar
    with st.sidebar:
        st.title("VP Swing")
        st.caption(f"MAJ: {state.get('_mtime','—')}")
        cache = {}
        for k, v in state.get('daily_cache', {}).items(): cache = v; break
        if cache:
            st.metric("ATR", f"{cache['atr']:.2f}" if cache.get('atr') else "—")
            st.metric("Spread RT", f"{cache['spread_rt']:.3f}" if cache.get('spread_rt') else "—")
        st.metric("Capital", f"${capital:,.2f}")
        st.metric("Positions", len(positions))
        st.metric("Trades fermes", len(trades))
        st.divider()
        refresh = st.selectbox("Auto-refresh (sec)", [0, 10, 30, 60], index=0)
        if st.button("Reset", type="secondary"):
            reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                     'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
            with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
            st.success("Reset OK"); st.rerun()

    # KPI bar
    kpi_bar(df, capital)
    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Vue d'ensemble", "Strategies", "Calendrier", "Analyse", "Trades", "Sessions"
    ])

    with tab1: tab_overview(df, positions)
    with tab2: tab_strategies(df)
    with tab3: tab_calendar(df)
    with tab4: tab_analysis(df)
    with tab5: tab_trades(df)
    with tab6: tab_sessions(df)

    # Auto refresh
    if refresh > 0:
        time.sleep(refresh)
        st.rerun()

if __name__ == '__main__':
    main()
