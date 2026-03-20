"""
Dashboard VP Swing — streamlit run dashboard.py
"""
import streamlit as st
import json, os, time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import itertools

LOG_FILE = "paper_trades.json"
CAPITAL_INITIAL = 1000.0

STRATS = {
    'AC':'Absorption Tokyo','D':'GAP Tokyo→London','E':'KZ London fade',
    'F':'2BAR Tokyo rev','G':'NY 1st candle','H':'TOKEND 3b',
    'I':'FADE NY 1h','O':'BigCandle Tokyo','P':'ORB NY 30min','V':'CandleRatio Tokyo'
}

st.set_page_config(page_title="VP Swing", layout="wide")

def load_state():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f: return json.load(f)
    return {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': []}

def get_price():
    try:
        from phase1_poc_calculator import get_conn
        c = get_conn(); c.autocommit = True
        cur = c.cursor()
        cur.execute("SELECT bid, ask FROM market_ticks_xauusd ORDER BY ts DESC LIMIT 1")
        r = cur.fetchone(); cur.close(); c.close()
        if r: return float(r[0]), float(r[1])
    except: pass
    return None, None

def session_now():
    h = datetime.now(timezone.utc).hour
    if 0 <= h < 6: return "Tokyo"
    elif 8 <= h < 14: return "London"
    elif 14 <= h < 21: return "New York"
    return "Off"

state = load_state()
capital = state['capital']
trades = state['trades']
positions = state['open_positions']
bid, ask = get_price()
pnl_total = capital - CAPITAL_INITIAL
now_utc = datetime.now(timezone.utc)

# ════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(f"# ${capital:,.2f}")
    pnl_pct = pnl_total / CAPITAL_INITIAL * 100
    pnl_color = "green" if pnl_total >= 0 else "red"
    st.markdown(f":{pnl_color}[**{'+' if pnl_total>=0 else ''}{pnl_total:,.2f}** ({pnl_pct:+.1f}%)]")
with col_b:
    st.markdown(f"**{session_now()}** · {now_utc.strftime('%H:%M')} UTC")
    if bid:
        st.markdown(f"XAUUSD **{bid:,.2f}** · sp {ask-bid:.3f}")
    cache = {}
    for k, v in state.get('daily_cache', {}).items(): cache = v; break
    if cache.get('atr'):
        st.markdown(f"ATR {cache['atr']:.2f}")

# KPIs
if trades:
    df_all = pd.DataFrame(trades)
    df_all['pnl_dollar'] = df_all['pnl_dollar'].astype(float)
    df_all['cum'] = df_all['capital_after'].astype(float)
    df_all['entry_time'] = pd.to_datetime(df_all['entry_time'])
    df_all['exit_time'] = pd.to_datetime(df_all['exit_time'])

    wins = df_all[df_all['pnl_dollar'] > 0]
    gp = wins['pnl_dollar'].sum() if len(wins) else 0
    gl = abs(df_all[df_all['pnl_dollar'] < 0]['pnl_dollar'].sum()) + 0.01
    caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df_all['cum']]).reset_index(drop=True)
    max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Trades", len(df_all))
    k2.metric("Win Rate", f"{len(wins)/len(df_all)*100:.0f}%")
    k3.metric("Profit Factor", f"{gp/gl:.2f}")
    k4.metric("Max DD", f"{max_dd:.1f}%")
    # Today
    today_df = df_all[df_all['entry_time'].dt.date == now_utc.date()]
    today_pnl = today_df['pnl_dollar'].sum() if len(today_df) else 0
    k5.metric(f"Aujourd'hui ({len(today_df)})", f"${today_pnl:+,.2f}")

st.divider()

# ════════════════════════════════════════════════════
# POSITIONS OUVERTES
# ════════════════════════════════════════════════════
st.markdown(f"### Positions ouvertes ({len(positions)})")

if positions:
    total_unr = 0
    for p in positions:
        entry = p.get('entry', 0)
        stop = p.get('stop', 0)
        best = p.get('best', entry)
        d = p.get('strat_dir', '')
        strat = p.get('strat', '')
        oz = p.get('pos_oz', 0)
        lots = p.get('lots', 0)
        bars = p.get('bars_held', 0)
        atr = p.get('trade_atr', 1)
        trail = p.get('trail_active', False)
        spread = p.get('entry_spread', 0)
        entry_time = str(p.get('entry_time', ''))[:19]

        # PnL
        if bid:
            px = bid if d == 'long' else ask
            pnl_oz = (px - entry) if d == 'long' else (entry - px)
            pnl_d = pnl_oz * oz
            total_unr += pnl_d
        else:
            px = 0; pnl_oz = 0; pnl_d = 0

        # Distances
        dist_stop = abs(entry - stop)
        dist_best = abs(best - entry)
        dist_px = abs(px - entry) if px else 0

        icon = "🟢" if pnl_d >= 0 else "🔴"
        trail_icon = "🔒" if trail else "—"

        c1, c2, c3, c4 = st.columns([1.5, 2, 2, 1])
        with c1:
            st.markdown(f"#### {icon} {strat}")
            st.caption(f"{STRATS.get(strat, '')} · **{d.upper()}**")
        with c2:
            st.markdown(f"**Entree** {entry:.2f} → **Prix** {px:.2f}" if px else f"**Entree** {entry:.2f}")
            st.caption(f"Stop **{stop:.2f}** (dist {dist_stop:.2f}) · Best **{best:.2f}** (dist {dist_best:.2f})")
        with c3:
            st.markdown(f"**PnL ${pnl_d:+,.2f}** ({pnl_oz:+.2f} oz)")
            st.caption(f"Trail {trail_icon} · Spread {spread:.3f} · {lots:.3f} lots")
        with c4:
            st.markdown(f"**{bars}** / 12 bars")
            st.caption(entry_time)

    if bid:
        color = "green" if total_unr >= 0 else "red"
        st.markdown(f":{color}[**PnL latent total: ${total_unr:+,.2f}**]")
else:
    st.caption("Aucune position ouverte")

st.divider()

# ════════════════════════════════════════════════════
# EQUITY
# ════════════════════════════════════════════════════
if trades:
    st.markdown("### Equity")
    eq = pd.DataFrame({'Capital': [CAPITAL_INITIAL] + df_all['cum'].tolist()},
        index=[df_all['entry_time'].iloc[0] - pd.Timedelta(minutes=30)] + df_all['entry_time'].tolist())
    st.line_chart(eq, height=280, use_container_width=True)
    st.divider()

# ════════════════════════════════════════════════════
# TRADES FERMES
# ════════════════════════════════════════════════════
st.markdown(f"### Trades fermes ({len(trades)})")

if trades:
    show = df_all.iloc[::-1].copy()
    show['duration'] = (show['exit_time'] - show['entry_time']).dt.total_seconds() / 60
    show['Ouverture'] = show['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
    show['Fermeture'] = show['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
    show['Strat'] = show['strat']
    show['Nom'] = show['strat'].map(STRATS)
    show['Dir'] = show['dir'].str.upper()
    show['Entree'] = show['entry'].apply(lambda x: f"{float(x):.2f}")
    show['Sortie'] = show['exit'].apply(lambda x: f"{float(x):.2f}")
    show['PnL $'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
    show['PnL oz'] = show['pnl_oz'].apply(lambda x: f"{float(x):+.3f}")
    show['Raison'] = show['exit_reason']
    show['Bars'] = show['bars_held']
    show['Duree'] = show['duration'].apply(lambda x: f"{x:.0f}m")
    show['Capital'] = show['capital_after'].apply(lambda x: f"${float(x):,.2f}")

    display_cols = ['Ouverture','Fermeture','Strat','Nom','Dir','Entree','Sortie',
                    'PnL $','PnL oz','Raison','Bars','Duree','Capital']
    display_df = show[display_cols]

    def color_row(row):
        try:
            val = float(row['PnL $'].replace('$','').replace(',','').replace('+',''))
            c = 'color: #26a69a' if val > 0 else 'color: #ef5350' if val < 0 else ''
        except: c = ''
        return [c]*len(row)

    st.dataframe(display_df.style.apply(color_row, axis=1),
                 use_container_width=True, hide_index=True,
                 height=min(len(display_df)*38+40, 600))

    st.divider()

    # ════════════════════════════════════════════════════
    # STATS
    # ════════════════════════════════════════════════════
    st.markdown("### Statistiques")

    # Par strat
    srows = []
    for sn in sorted(df_all['strat'].unique()):
        s = df_all[df_all['strat']==sn]; n = len(s)
        w = (s['pnl_dollar']>0).sum()
        gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        srows.append({
            'Strat': sn, 'Nom': STRATS.get(sn,''),
            'Trades': n, 'Wins': w, 'Losses': n-w,
            'WR': f"{w/n*100:.0f}%", 'PF': f"{gps/gls:.2f}",
            'PnL total': f"${s['pnl_dollar'].sum():+,.2f}",
            'Avg trade': f"${s['pnl_dollar'].mean():+,.2f}",
            'Meilleur': f"${s['pnl_dollar'].max():+,.2f}",
            'Pire': f"${s['pnl_dollar'].min():+,.2f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### Long vs Short")
        for d_name in ['long','short']:
            s = df_all[df_all['dir']==d_name]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.markdown(f"**{d_name.upper()}** · {len(s)} trades · WR {w/len(s)*100:.0f}% · PF {gp_d/gl_d:.2f} · ${s['pnl_dollar'].sum():+,.2f}")

    with col2:
        st.markdown("##### Sorties")
        for reason in df_all['exit_reason'].unique():
            s = df_all[df_all['exit_reason']==reason]
            w = (s['pnl_dollar']>0).sum()
            st.markdown(f"**{reason}** · {len(s)} trades · {w}W {len(s)-w}L")

    with col3:
        st.markdown("##### Streaks")
        loss_s = max((sum(1 for _ in g) for k, g in itertools.groupby(df_all['pnl_dollar']<0) if k), default=0)
        win_s = max((sum(1 for _ in g) for k, g in itertools.groupby(df_all['pnl_dollar']>0) if k), default=0)
        st.markdown(f"Max wins consecutifs: **{win_s}**")
        st.markdown(f"Max pertes consecutives: **{loss_s}**")
        if len(wins):
            st.markdown(f"Avg win: **${wins['pnl_dollar'].mean():+,.2f}**")
        losses_df = df_all[df_all['pnl_dollar']<0]
        if len(losses_df):
            st.markdown(f"Avg loss: **${losses_df['pnl_dollar'].mean():+,.2f}**")

    st.divider()

    # PnL par strat
    st.markdown("##### PnL par strategie")
    st.bar_chart(df_all.groupby('strat')['pnl_dollar'].sum().sort_values(),
                 use_container_width=True, horizontal=True, height=250)

    # PnL journalier
    st.markdown("##### PnL journalier")
    df_all['date'] = df_all['entry_time'].dt.date
    st.bar_chart(df_all.groupby('date')['pnl_dollar'].sum(), use_container_width=True, height=200)

else:
    st.caption("Aucun trade ferme. En attente de signaux.")

# Refresh
time.sleep(10)
st.rerun()
