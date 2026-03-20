"""
Dashboard VP Swing — streamlit run dashboard.py
Portfolio: AA+D+E+F+H+NY6+NY16+NY17+O
"""
import streamlit as st
import json, os, time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import itertools
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LOG_FILE = "paper_trades.json"
CAPITAL_INITIAL = 1000.0

STRATS = {
    'AA':'Pin Bar London','D':'GAP Tokyo→London','E':'KZ London fade',
    'F':'2BAR Tokyo rev','H':'TOKEND 3b','O':'BigCandle Tokyo',
    'NY6':'GAP London→NY','NY16':'LONEND 3b→NY','NY17':'LONEND 0.5ATR→NY',
}

st.set_page_config(page_title="VP Swing Dashboard", layout="wide")

def load_state():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f: return json.load(f)
    return {'capital':CAPITAL_INITIAL,'trades':[],'open_positions':[]}

def get_price():
    try:
        from phase1_poc_calculator import get_conn
        c=get_conn(); c.autocommit=True; cur=c.cursor()
        cur.execute("SELECT bid,ask FROM market_ticks_xauusd ORDER BY ts DESC LIMIT 1")
        r=cur.fetchone(); cur.close(); c.close()
        if r: return float(r[0]),float(r[1])
    except: pass
    return None,None

state = load_state()
capital = state['capital']
trades = state['trades']
positions = state['open_positions']
bid, ask = get_price()
now = datetime.now(timezone.utc)
h = now.hour
sess = "Tokyo" if 0<=h<6 else "London" if 8<=h<14 else "New York" if 14<=h<21 else "Off"
pnl = capital - CAPITAL_INITIAL

# ── TITRE ──
st.title("VP Swing — Paper Trading")
st.caption(f"{sess} · {now.strftime('%H:%M')} UTC · XAUUSD {'${:,.2f}'.format(bid) if bid else '—'} · 9 strats · SL=1.0 ACT=0.5 TRAIL=0.75 T12")

# ── METRIQUES ──
n_trades = len(trades)
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Capital", f"${capital:,.2f}", f"${pnl:+,.2f}")

if n_trades > 0:
    df = pd.DataFrame(trades)
    df['pnl_dollar'] = df['pnl_dollar'].astype(float)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['cum'] = df['capital_after'].astype(float)
    df['entry'] = df['entry'].astype(float)
    df['exit'] = df['exit'].astype(float)
    df['pnl_oz'] = df['pnl_oz'].astype(float)
    df['date'] = df['entry_time'].dt.date
    df['duration'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60

    wins = df[df['pnl_dollar'] > 0]
    losses = df[df['pnl_dollar'] <= 0]
    gp = wins['pnl_dollar'].sum() if len(wins) else 0
    gl = abs(losses['pnl_dollar'].sum()) + 0.01
    caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
    max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()

    today_df = df[df['date'] == now.date()]
    today_pnl = today_df['pnl_dollar'].sum() if len(today_df) else 0

    c2.metric("Trades", n_trades, f"{len(today_df)} aujourd'hui")
    c3.metric("Win Rate", f"{len(wins)/n_trades*100:.0f}%", f"{len(wins)}W {len(losses)}L")
    c4.metric("Profit Factor", f"{gp/gl:.2f}")
    c5.metric("Max DD", f"{max_dd:.1f}%")
    c6.metric("PnL du jour", f"${today_pnl:+,.2f}")
else:
    c2.metric("Trades", 0)
    c3.metric("Win Rate", "—")
    c4.metric("Profit Factor", "—")
    c5.metric("Max DD", "—")
    c6.metric("PnL du jour", "—")

st.divider()

# ── POSITIONS OUVERTES ──
st.subheader(f"Positions ouvertes ({len(positions)})")

if positions:
    pos_rows = []
    total_unr = 0
    for p in positions:
        e = p.get('entry',0); s = p.get('stop',0); best = p.get('best',e)
        d = p.get('strat_dir',''); sn = p.get('strat','')
        oz = p.get('pos_oz',0); bars = p.get('bars_held',0)
        trail = p.get('trail_active',False); lots = p.get('lots',0)
        et = str(p.get('entry_time',''))[:16]

        prix = "—"; pnl_str = "—"; pnl_oz_str = "—"
        if bid:
            px = bid if d=='long' else ask
            pnl_oz = (px-e) if d=='long' else (e-px)
            pnl_d = pnl_oz * oz; total_unr += pnl_d
            prix = f"{px:.2f}"
            pnl_str = f"${pnl_d:+,.2f}"
            pnl_oz_str = f"{pnl_oz:+.2f}"

        pos_rows.append({
            'Strat': sn,
            'Nom': STRATS.get(sn,''),
            'Dir': d.upper(),
            'Entree': f"{e:.2f}",
            'Prix': prix,
            'Stop': f"{s:.2f}",
            'Best': f"{best:.2f}",
            'PnL $': pnl_str,
            'PnL oz': pnl_oz_str,
            'Trail': 'ON' if trail else '—',
            'Bars': f"{bars}/12",
            'Lots': f"{lots:.3f}",
            'Ouvert': et,
        })

    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)

    if bid and total_unr != 0:
        st.metric("PnL latent total", f"${total_unr:+,.2f}")
else:
    st.info("Aucune position ouverte")

st.divider()

# ── EQUITY + DRAWDOWN ──
if n_trades > 1:
    st.subheader("Equity & Drawdown")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_heights=[0.7, 0.3])

    eq_x = [df['entry_time'].iloc[0] - pd.Timedelta(minutes=30)] + df['entry_time'].tolist()
    eq_y = [CAPITAL_INITIAL] + df['cum'].tolist()
    fig.add_trace(go.Scatter(x=eq_x, y=eq_y, fill='tozeroy',
                             fillcolor='rgba(38,166,154,0.15)',
                             line=dict(color='#26a69a', width=2),
                             name='Capital'), row=1, col=1)

    peak = pd.Series(eq_y).cummax()
    dd = ((pd.Series(eq_y) - peak) / peak * 100)
    fig.add_trace(go.Scatter(x=eq_x, y=dd, fill='tozeroy',
                             fillcolor='rgba(239,83,80,0.15)',
                             line=dict(color='#ef5350', width=1.5),
                             name='Drawdown'), row=2, col=1)

    fig.update_layout(
        height=400, showlegend=False, template='plotly_dark',
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    fig.update_yaxes(title_text="$", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

# ── TRADES FERMES ──
if n_trades > 0:
    st.subheader(f"Trades fermes ({n_trades})")

    show = df.iloc[::-1].copy()
    show['Ouverture'] = show['entry_time'].dt.strftime('%d/%m %H:%M')
    show['Fermeture'] = show['exit_time'].dt.strftime('%d/%m %H:%M')
    show['Nom'] = show['strat'].map(STRATS)
    show['Dir'] = show['dir'].str.upper()
    show['In'] = show['entry'].apply(lambda x: f"{x:.2f}")
    show['Out'] = show['exit'].apply(lambda x: f"{x:.2f}")
    show['PnL'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
    show['oz'] = show['pnl_oz'].apply(lambda x: f"{x:+.3f}")
    show['Sortie'] = show['exit_reason']
    show['Bars'] = show['bars_held']
    show['Duree'] = show['duration'].apply(lambda x: f"{x:.0f}m")
    show['Capital'] = show['capital_after'].apply(lambda x: f"${float(x):,.2f}")

    tbl = show[['Ouverture','Fermeture','strat','Nom','Dir','In','Out','PnL','oz','Sortie','Bars','Duree','Capital']].copy()
    tbl.columns = ['Ouverture','Fermeture','Strat','Nom','Dir','In','Out','PnL','PnL oz','Sortie','Bars','Duree','Capital']

    def color_pnl(row):
        try:
            v = float(row['PnL'].replace('$','').replace(',','').replace('+',''))
            c = 'color:#26a69a' if v > 0 else 'color:#ef5350'
        except: c = ''
        return [c] * len(row)

    st.dataframe(tbl.style.apply(color_pnl, axis=1),
                 use_container_width=True, hide_index=True,
                 height=min(n_trades * 38 + 40, 500))

    st.divider()

    # ── PERFORMANCE PAR STRATEGIE ──
    st.subheader("Performance par strategie")

    srows = []
    for sn in sorted(df['strat'].unique()):
        s = df[df['strat']==sn]; n = len(s)
        w = (s['pnl_dollar'] > 0).sum()
        gps = s[s['pnl_dollar'] > 0]['pnl_dollar'].sum()
        gls = abs(s[s['pnl_dollar'] < 0]['pnl_dollar'].sum()) + 0.01
        srows.append({
            'Strat': sn,
            'Nom': STRATS.get(sn, ''),
            'Trades': n,
            'Wins': w,
            'Losses': n - w,
            'Win Rate': f"{w/n*100:.0f}%",
            'PF': f"{gps/gls:.2f}",
            'PnL total': f"${s['pnl_dollar'].sum():+,.2f}",
            'Avg trade': f"${s['pnl_dollar'].mean():+,.2f}",
            'Best': f"${s['pnl_dollar'].max():+,.2f}",
            'Worst': f"${s['pnl_dollar'].min():+,.2f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        pnl_strat = df.groupby('strat')['pnl_dollar'].sum().sort_values()
        colors = ['#26a69a' if v >= 0 else '#ef5350' for v in pnl_strat.values]
        fig2 = go.Figure(go.Bar(
            y=pnl_strat.index, x=pnl_strat.values, orientation='h',
            marker_color=colors,
            text=[f"${v:+,.0f}" for v in pnl_strat.values],
            textposition='outside'))
        fig2.update_layout(title="PnL par strategie", height=280,
                           template='plotly_dark', margin=dict(l=0,r=0,t=30,b=0),
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        daily = df.groupby('date')['pnl_dollar'].sum()
        colors_d = ['#26a69a' if v >= 0 else '#ef5350' for v in daily.values]
        fig3 = go.Figure(go.Bar(x=daily.index, y=daily.values, marker_color=colors_d))
        fig3.update_layout(title="PnL journalier", height=280,
                           template='plotly_dark', margin=dict(l=0,r=0,t=30,b=0),
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # Details
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Direction")
        dir_rows = []
        for d_name in ['long', 'short']:
            s = df[df['dir'] == d_name]
            if len(s) == 0: continue
            w = (s['pnl_dollar'] > 0).sum()
            gd = s[s['pnl_dollar'] > 0]['pnl_dollar'].sum()
            ld = abs(s[s['pnl_dollar'] < 0]['pnl_dollar'].sum()) + 0.01
            dir_rows.append({
                'Dir': d_name.upper(),
                'Trades': len(s),
                'WR': f"{w/len(s)*100:.0f}%",
                'PF': f"{gd/ld:.2f}",
                'PnL': f"${s['pnl_dollar'].sum():+,.2f}",
            })
        st.dataframe(pd.DataFrame(dir_rows), use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Sorties")
        exit_rows = []
        for reason in sorted(df['exit_reason'].unique()):
            s = df[df['exit_reason'] == reason]
            w = (s['pnl_dollar'] > 0).sum()
            exit_rows.append({
                'Raison': reason,
                'Trades': len(s),
                'Wins': w,
                'Losses': len(s) - w,
            })
        st.dataframe(pd.DataFrame(exit_rows), use_container_width=True, hide_index=True)

    with col3:
        st.subheader("Stats")
        ls = max((sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar'] < 0) if k), default=0)
        ws = max((sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar'] > 0) if k), default=0)
        stat_rows = [
            {'Stat': 'Max wins consec', 'Valeur': str(ws)},
            {'Stat': 'Max losses consec', 'Valeur': str(ls)},
            {'Stat': 'Avg win', 'Valeur': f"${wins['pnl_dollar'].mean():+,.2f}" if len(wins) else "—"},
            {'Stat': 'Avg loss', 'Valeur': f"${losses['pnl_dollar'].mean():+,.2f}" if len(losses) else "—"},
            {'Stat': 'Duree moyenne', 'Valeur': f"{df['duration'].mean():.0f} min"},
            {'Stat': 'Bars moyen', 'Valeur': f"{df['bars_held'].mean():.1f}"},
        ]
        st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)

else:
    st.info("En attente du premier trade. 9 strategies surveillent XAUUSD 5 minutes.")

# ── SIDEBAR: STRATEGIES ──
with st.sidebar:
    st.subheader("Strategies")
    for session, strat_list in [("Tokyo", ['F','O']), ("London", ['AA','D','E','H']), ("New York", ['NY6','NY16','NY17'])]:
        st.caption(f"**{session}**")
        for sn in strat_list:
            if n_trades > 0 and sn in df['strat'].values:
                s = df[df['strat']==sn]
                w = (s['pnl_dollar']>0).sum(); n = len(s)
                pnl_s = s['pnl_dollar'].sum()
                gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
                gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
                color = "🟢" if pnl_s >= 0 else "🔴"
                st.markdown(f"{color} **{sn}** — {STRATS[sn]}  \n{n} trades · WR {w/n*100:.0f}% · PF {gps/gls:.2f} · ${pnl_s:+,.2f}")
            else:
                st.markdown(f"⚪ **{sn}** — {STRATS.get(sn,'')}  \n0 trades")
    st.divider()
    cache = {}
    for k, v in state.get('daily_cache', {}).items(): cache = v; break
    if cache.get('atr'):
        st.metric("ATR (veille)", f"{cache['atr']:.2f}")

# Refresh
time.sleep(10)
st.rerun()
