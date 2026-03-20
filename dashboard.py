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
st.markdown("""<style>
div[data-testid="stMetricValue"] > div {font-size: 1.4rem;}
div[data-testid="stMetricDelta"] > div {font-size: 0.85rem;}
section[data-testid="stSidebar"] {width: 260px !important;}
.block-container {padding-top: 1rem; padding-bottom: 0rem;}
</style>""", unsafe_allow_html=True)

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

state = load_state()
capital = state['capital']
trades = state['trades']
positions = state['open_positions']
bid, ask = get_price()
now_utc = datetime.now(timezone.utc)
h = now_utc.hour
sess = "Tokyo" if 0<=h<6 else "London" if 8<=h<14 else "New York" if 14<=h<21 else "Off"

# ══════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### VP Swing")
    st.markdown(f"**{sess}** · {now_utc.strftime('%H:%M')} UTC")
    if bid: st.markdown(f"**XAUUSD** ${bid:,.2f}")
    cache = {}
    for k, v in state.get('daily_cache', {}).items(): cache = v; break
    if cache.get('atr'): st.markdown(f"**ATR** {cache['atr']:.2f}")
    st.divider()
    st.caption("10 strats · Trailing pessimiste")
    st.caption(f"SL 1.5 · ACT 0.3 · TRAIL 0.3 · T12")
    st.caption(f"Strats: {', '.join(sorted(STRATS.keys()))}")

# ══════════════════════════════════════════════════
# HEADER: 6 METRIQUES
# ══════════════════════════════════════════════════
pnl = capital - CAPITAL_INITIAL
pnl_pct = pnl / CAPITAL_INITIAL * 100

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Capital", f"${capital:,.2f}", delta=f"${pnl:+,.2f} ({pnl_pct:+.1f}%)")

n_trades = len(trades)
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
    pf = gp / gl
    wr = len(wins) / n_trades * 100
    caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
    max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
    dd_now = (capital - caps.cummax().iloc[-1]) / caps.cummax().iloc[-1] * 100

    today_df = df[df['date'] == now_utc.date()]
    today_pnl = today_df['pnl_dollar'].sum() if len(today_df) else 0
    today_n = len(today_df)

    c2.metric("Trades", n_trades, delta=f"{today_n} aujourd'hui")
    c3.metric("Win Rate", f"{wr:.0f}%", delta=f"{len(wins)}W / {len(losses)}L")
    c4.metric("Profit Factor", f"{pf:.2f}")
    c5.metric("Drawdown", f"{dd_now:.1f}%", delta=f"max {max_dd:.1f}%", delta_color="off")
    c6.metric("Aujourd'hui", f"${today_pnl:+,.2f}", delta=f"{today_n} trades")
else:
    c2.metric("Trades", "0")
    c3.metric("Win Rate", "—")
    c4.metric("Profit Factor", "—")
    c5.metric("Drawdown", "—")
    c6.metric("Aujourd'hui", "—")

st.divider()

# ══════════════════════════════════════════════════
# POSITIONS OUVERTES
# ══════════════════════════════════════════════════
if positions:
    st.markdown(f"### {len(positions)} position(s) ouverte(s)")
    pos_rows = []
    total_unr = 0
    for p in positions:
        entry = p.get('entry',0); stop = p.get('stop',0); best = p.get('best',entry)
        d = p.get('strat_dir',''); strat = p.get('strat','')
        oz = p.get('pos_oz',0); bars = p.get('bars_held',0)
        atr = p.get('trade_atr',1); trail = p.get('trail_active',False)
        lots = p.get('lots',0); spread = p.get('entry_spread',0)
        entry_time = str(p.get('entry_time',''))[:19]

        px = "—"; pnl_str = "—"; pnl_oz_str = "—"
        if bid:
            exit_p = bid if d == 'long' else ask
            pnl_oz = (exit_p - entry) if d == 'long' else (entry - exit_p)
            pnl_d = pnl_oz * oz; total_unr += pnl_d
            px = f"{exit_p:.2f}"
            pnl_str = f"${pnl_d:+,.2f}"
            pnl_oz_str = f"{pnl_oz:+.2f}"

        pos_rows.append({
            'Strat': strat,
            'Nom': STRATS.get(strat, ''),
            'Dir': d.upper(),
            'Entree': f"{entry:.2f}",
            'Prix actuel': px,
            'Stop': f"{stop:.2f}",
            'Best': f"{best:.2f}",
            'PnL $': pnl_str,
            'PnL oz': pnl_oz_str,
            'Trail': 'ON' if trail else '—',
            'Bars': f"{bars}/12",
            'Lots': f"{lots:.3f}",
            'Spread': f"{spread:.3f}",
            'Ouverture': entry_time,
        })

    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True,
                 height=len(pos_rows)*38+40)
    if bid:
        color = "green" if total_unr >= 0 else "red"
        st.markdown(f"PnL latent total: :{color}[**${total_unr:+,.2f}**]")
    st.divider()

# ══════════════════════════════════════════════════
# EQUITY + DRAWDOWN
# ══════════════════════════════════════════════════
if n_trades > 0:
    col_eq, col_dd = st.columns(2)
    with col_eq:
        st.markdown("### Equity")
        eq = pd.DataFrame({'$': [CAPITAL_INITIAL] + df['cum'].tolist()},
            index=[df['entry_time'].iloc[0] - pd.Timedelta(minutes=30)] + df['entry_time'].tolist())
        st.line_chart(eq, height=250, use_container_width=True)
    with col_dd:
        st.markdown("### Drawdown")
        peak = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).cummax().iloc[1:].reset_index(drop=True)
        dd_series = (df['cum'].reset_index(drop=True) - peak) / peak * 100
        dd_df = pd.DataFrame({'%': dd_series.values}, index=df['entry_time'].values)
        st.area_chart(dd_df, height=250, use_container_width=True, color='#ff4b4b')

    st.divider()

# ══════════════════════════════════════════════════
# TRADES FERMES
# ══════════════════════════════════════════════════
if n_trades > 0:
    st.markdown(f"### Trades fermes ({n_trades})")

    show = df.iloc[::-1].copy()
    show['Ouverture'] = show['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
    show['Fermeture'] = show['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
    show['Nom'] = show['strat'].map(STRATS)
    show['Dir'] = show['dir'].str.upper()
    show['In'] = show['entry'].apply(lambda x: f"{x:.2f}")
    show['Out'] = show['exit'].apply(lambda x: f"{x:.2f}")
    show['PnL $'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
    show['PnL oz'] = show['pnl_oz'].apply(lambda x: f"{x:+.3f}")
    show['Raison'] = show['exit_reason']
    show['Bars'] = show['bars_held']
    show['Duree'] = show['duration'].apply(lambda x: f"{x:.0f}m")
    show['Cap'] = show['capital_after'].apply(lambda x: f"${float(x):,.2f}")

    table_cols = ['Ouverture','Fermeture','strat','Nom','Dir','In','Out',
                  'PnL $','PnL oz','Raison','Bars','Duree','Cap']
    table = show[table_cols].copy()
    table.columns = ['Ouverture','Fermeture','Strat','Nom','Dir','In','Out',
                     'PnL $','PnL oz','Raison','Bars','Duree','Capital']

    def color_pnl(row):
        try:
            v = float(row['PnL $'].replace('$','').replace(',','').replace('+',''))
            c = 'color:#26a69a' if v>0 else 'color:#ef5350' if v<0 else ''
        except: c = ''
        return [c]*len(row)

    st.dataframe(table.style.apply(color_pnl, axis=1),
                 use_container_width=True, hide_index=True,
                 height=min(n_trades*38+40, 500))

    st.divider()

    # ══════════════════════════════════════════════════
    # PERFORMANCE PAR STRATEGIE
    # ══════════════════════════════════════════════════
    st.markdown("### Performance par strategie")
    srows = []
    for sn in sorted(df['strat'].unique()):
        s = df[df['strat']==sn]; n = len(s)
        w = (s['pnl_dollar']>0).sum()
        gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        srows.append({
            'Strat': sn, 'Nom': STRATS.get(sn,''),
            'Trades': n, 'Wins': w, 'Losses': n-w,
            'Win Rate': f"{w/n*100:.0f}%",
            'Profit Factor': f"{gps/gls:.2f}",
            'PnL total': f"${s['pnl_dollar'].sum():+,.2f}",
            'PnL moyen': f"${s['pnl_dollar'].mean():+,.2f}",
            'Meilleur': f"${s['pnl_dollar'].max():+,.2f}",
            'Pire': f"${s['pnl_dollar'].min():+,.2f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### PnL par strategie")
        st.bar_chart(df.groupby('strat')['pnl_dollar'].sum().sort_values(),
                     horizontal=True, height=250, use_container_width=True)
    with col2:
        st.markdown("##### PnL journalier")
        st.bar_chart(df.groupby('date')['pnl_dollar'].sum(), height=250, use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════════════
    # DETAILS
    # ══════════════════════════════════════════════════
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### Direction")
        for d_name in ['long','short']:
            s = df[df['dir']==d_name]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.markdown(f"**{d_name.upper()}** · {len(s)} trades · WR {w/len(s)*100:.0f}% · PF {gp_d/gl_d:.2f}")
            st.caption(f"PnL: ${s['pnl_dollar'].sum():+,.2f} · Avg: ${s['pnl_dollar'].mean():+,.2f}")

    with col2:
        st.markdown("##### Sorties")
        for reason in sorted(df['exit_reason'].unique()):
            s = df[df['exit_reason']==reason]; w = (s['pnl_dollar']>0).sum()
            st.markdown(f"**{reason}** · {len(s)} trades ({w}W / {len(s)-w}L)")

    with col3:
        st.markdown("##### Performance")
        loss_s = max((sum(1 for _ in g) for k,g in itertools.groupby(df['pnl_dollar']<0) if k), default=0)
        win_s = max((sum(1 for _ in g) for k,g in itertools.groupby(df['pnl_dollar']>0) if k), default=0)
        st.markdown(f"Max wins consec: **{win_s}**")
        st.markdown(f"Max pertes consec: **{loss_s}**")
        if len(wins): st.markdown(f"Avg win: **${wins['pnl_dollar'].mean():+,.2f}**")
        if len(losses): st.markdown(f"Avg loss: **${losses['pnl_dollar'].mean():+,.2f}**")
        st.markdown(f"Avg duree: **{df['duration'].mean():.0f}m**")
        st.markdown(f"Avg bars: **{df['bars_held'].mean():.1f}**")

else:
    st.info("En attente du premier trade ferme. Le systeme surveille les signaux sur XAUUSD 5 minutes.")

# Refresh
time.sleep(10)
st.rerun()
