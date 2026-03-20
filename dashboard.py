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

    # Sidebar
    with st.sidebar:
        st.title("VP Swing")
        st.caption(f"MAJ: {state.get('_mtime','—')}")
        st.caption("10 strats | TRp SL=1.5 ACT=0.3 TRAIL=0.3 T12")
        cache = {}
        for k, v in state.get('daily_cache', {}).items(): cache = v; break
        if cache:
            st.metric("ATR", f"{cache['atr']:.2f}" if cache.get('atr') else "—")
        if current_price:
            st.metric("Gold", f"${current_price['bid']:.2f}",
                      delta=f"sp={current_price['ask']-current_price['bid']:.3f}")
        st.divider()
        refresh = st.selectbox("Auto-refresh (sec)", [0, 10, 30, 60], index=0)
        if st.button("Reset", type="secondary"):
            reset = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
                     'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
            with open(LOG_FILE, 'w') as f: json.dump(reset, f, indent=2)
            st.success("Reset OK"); st.rerun()

    # KPIs
    cols = st.columns(8)
    cols[0].metric("Capital", f"${capital:,.2f}", delta=f"${pnl_total:+,.2f}")
    cols[1].metric("Positions", len(positions))

    df = None
    if trades:
        df = pd.DataFrame(trades)
        df['pnl_dollar'] = df['pnl_dollar'].astype(float)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df['cum'] = df['capital_after'].astype(float)
        wins = df[df['pnl_dollar'] > 0]
        gp = wins['pnl_dollar'].sum() if len(wins) else 0
        gl = abs(df[df['pnl_dollar'] < 0]['pnl_dollar'].sum()) + 0.01
        caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
        max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
        max_cl = max((sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar'] < 0) if k), default=0)
        cols[2].metric("Trades", len(df))
        cols[3].metric("Win Rate", f"{len(wins)/len(df)*100:.0f}%")
        cols[4].metric("Profit Factor", f"{gp/gl:.2f}")
        cols[5].metric("Avg Trade", f"${df['pnl_dollar'].mean():+,.2f}")
        cols[6].metric("Max DD", f"{max_dd:.1f}%")
        cols[7].metric("Streak L", max_cl)

    st.divider()

    # Positions ouvertes
    st.subheader(f"Positions ouvertes ({len(positions)})")
    if positions:
        total_unrealized = 0
        rows = []
        for p in positions:
            entry = p.get('entry', 0); stop = p.get('stop', 0)
            best = p.get('best', entry); d = p.get('strat_dir', '')
            pos_oz = p.get('pos_oz', 0)
            if current_price:
                exit_price = current_price['bid'] if d == 'long' else current_price['ask']
                pnl_oz = (exit_price - entry) if d == 'long' else (entry - exit_price)
                pnl_dollar = pnl_oz * pos_oz; total_unrealized += pnl_dollar
                pnl_str = f"${pnl_dollar:+,.2f}"; price_str = f"{exit_price:.2f}"
            else:
                pnl_str = "—"; price_str = "—"
            rows.append({
                'Strat': p.get('strat',''), 'Nom': STRAT_NAMES.get(p.get('strat',''),''),
                'Dir': d.upper(), 'Entree': f"{entry:.2f}", 'Prix': price_str,
                'Stop': f"{stop:.2f}", 'Best': f"{best:.2f}", 'PnL': pnl_str,
                'Trail': '🟢' if p.get('trail_active') else '⚪',
                'Bars': p.get('bars_held',0), 'Lots': f"{p.get('lots',0):.3f}",
                'Heure': str(p.get('entry_time',''))[:16],
            })
        if current_price:
            st.caption(f"PnL latent: **${total_unrealized:+,.2f}**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune position ouverte")

    if df is None or len(df) == 0:
        st.divider()
        st.warning("Aucun trade ferme.")
        if refresh > 0: time.sleep(refresh); st.rerun()
        return

    st.divider()

    # Equity + DD
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Equity")
        st.line_chart(df[['entry_time','cum']].set_index('entry_time').rename(columns={'cum':'Capital'}), use_container_width=True)
    with col2:
        st.subheader("Drawdown")
        peak = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).cummax().iloc[1:].reset_index(drop=True)
        dd = (df['cum'].reset_index(drop=True) - peak) / peak * 100
        st.area_chart(pd.DataFrame({'DD %': dd.values}, index=df['entry_time'].values), use_container_width=True, color='#ff4b4b')

    st.divider()

    # Par strat + PnL chart
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Par strategie")
        srows = []
        for sn in sorted(df['strat'].unique()):
            s = df[df['strat']==sn]; n = len(s)
            w = (s['pnl_dollar']>0).sum(); pnl = s['pnl_dollar'].sum()
            gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            srows.append({'Strat':sn, 'Nom':STRAT_NAMES.get(sn,''), 'n':n,
                          'WR':f"{w/n*100:.0f}%", 'PF':f"{gps/gls:.2f}",
                          'PnL':f"${pnl:+,.2f}", 'Avg':f"${pnl/n:+,.2f}"})
        st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)
    with col2:
        st.subheader("PnL par strat")
        st.bar_chart(df.groupby('strat')['pnl_dollar'].sum().sort_values(), use_container_width=True, horizontal=True)

    st.divider()

    # Long/Short + Jour semaine + PnL journalier
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Long vs Short")
        for d in ['long','short']:
            s = df[df['dir']==d]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.metric(f"{d.upper()} ({len(s)})", f"PF {gp_d/gl_d:.2f} | WR {w/len(s)*100:.0f}%",
                      delta=f"${s['pnl_dollar'].sum():+,.2f}")
    with col2:
        st.subheader("Par jour")
        dow_names = {0:'Lun',1:'Mar',2:'Mer',3:'Jeu',4:'Ven'}
        df['dow'] = df['entry_time'].dt.dayofweek
        drows = []
        for dow in range(5):
            s = df[df['dow']==dow]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            drows.append({'Jour':dow_names[dow],'n':len(s),'WR':f"{w/len(s)*100:.0f}%",
                          'PF':f"{gp_d/gl_d:.2f}",'PnL':f"${s['pnl_dollar'].sum():+,.2f}"})
        st.dataframe(pd.DataFrame(drows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("PnL journalier")
    df['date'] = df['entry_time'].dt.date
    st.bar_chart(df.groupby('date')['pnl_dollar'].sum(), use_container_width=True)

    st.divider()

    # Distribution
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Distribution PnL")
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 4))
        pnls = df['pnl_dollar'].values
        pos_p = pnls[pnls > 0]; neg_p = pnls[pnls <= 0]
        bins = np.linspace(pnls.min(), pnls.max(), 31)
        if len(neg_p): ax.hist(neg_p, bins=bins, color='#ef5350', edgecolor='white', alpha=0.8, label='Loss')
        if len(pos_p): ax.hist(pos_p, bins=bins, color='#26a69a', edgecolor='white', alpha=0.8, label='Win')
        ax.axvline(0, color='white', linestyle='--', alpha=0.5)
        ax.set_xlabel('PnL ($)'); ax.set_ylabel('Freq')
        ax.set_facecolor('#0e1117'); fig.patch.set_facecolor('#0e1117')
        ax.tick_params(colors='white'); ax.xaxis.label.set_color('white'); ax.yaxis.label.set_color('white')
        for spine in ax.spines.values(): spine.set_color('#333')
        ax.legend(facecolor='#0e1117', labelcolor='white')
        st.pyplot(fig); plt.close(fig)
    with col2:
        st.subheader("Stats")
        stats = {
            'Avg win': f"${pnls[pnls>0].mean():+,.2f}" if len(pnls[pnls>0]) else "—",
            'Avg loss': f"${pnls[pnls<0].mean():+,.2f}" if len(pnls[pnls<0]) else "—",
            'Best': f"${pnls.max():+,.2f}", 'Worst': f"${pnls.min():+,.2f}",
            'Ecart-type': f"${pnls.std():,.2f}",
        }
        st.dataframe(pd.DataFrame(stats.items(), columns=['','']), use_container_width=True, hide_index=True)
        st.subheader("Sorties")
        for reason in df['exit_reason'].unique():
            s = df[df['exit_reason']==reason]
            st.caption(f"**{reason}**: {len(s)} ({len(s)/len(df)*100:.0f}%)")

    st.divider()

    # Trades
    st.subheader(f"Trades ({len(df)})")
    df['duration'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60
    show = df.iloc[::-1].copy()
    show['Heure'] = show['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
    show['Nom'] = show['strat'].map(STRAT_NAMES)
    show['Dir'] = show['dir'].str.upper()
    show['Entree'] = show['entry'].apply(lambda x: f"{float(x):.2f}")
    show['Sortie'] = show['exit'].apply(lambda x: f"{float(x):.2f}")
    show['PnL $'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
    show['PnL oz'] = show['pnl_oz'].apply(lambda x: f"{float(x):+.3f}")
    show['Duree'] = show['duration'].apply(lambda x: f"{x:.0f}m")
    show['Raison'] = show['exit_reason']
    show['Capital'] = show['capital_after'].apply(lambda x: f"${float(x):,.2f}")

    cols_show = ['Heure','strat','Nom','Dir','Entree','Sortie','PnL $','PnL oz','Raison','bars_held','Duree','Capital']
    display_df = show[cols_show].copy()
    display_df.columns = ['Heure','Strat','Nom','Dir','In','Out','PnL $','PnL oz','Raison','Bars','Duree','Capital']

    def color_row(row):
        try:
            val = float(row['PnL $'].replace('$','').replace(',','').replace('+',''))
            c = 'color: #26a69a' if val > 0 else 'color: #ef5350' if val < 0 else ''
        except: c = ''
        return [c]*len(row)

    st.dataframe(display_df.style.apply(color_row, axis=1),
                 use_container_width=True, hide_index=True,
                 height=min(len(display_df)*38+40, 800))

    if refresh > 0:
        time.sleep(refresh)
        st.rerun()

if __name__ == '__main__':
    main()
