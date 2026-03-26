"""
Dashboard VP Swing — streamlit run dashboard.py
Multi-compte + Paper/Live selector.
"""
import streamlit as st
import json, os
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import itertools
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from strats import STRAT_NAMES as STRATS, STRAT_SESSION
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

st.set_page_config(page_title="VP Swing", layout="wide")

# ── SIDEBAR: ACCOUNT + MODE ──
ACCOUNTS = {
    'icm': {'module': 'config_icm', 'label': 'ICMarkets'},
    'ftmo': {'module': 'config_ftmo', 'label': 'FTMO'},
    '5ers': {'module': 'config_5ers', 'label': '5ers'},
}
with st.sidebar:
    account = st.selectbox("Compte", list(ACCOUNTS.keys()),
                           format_func=lambda x: ACCOUNTS[x]['label'],
                           key='account_selector')
    mode = st.radio("Mode", ["Paper", "Live MT5"], key='mode_selector')

import importlib
cfg = importlib.import_module(ACCOUNTS[account]['module'])
PORTFOLIO = cfg.PORTFOLIO
RISK_PCT = cfg.RISK_PCT
BROKER = cfg.BROKER

# ── MAGIC NUMBERS (same as live_mt5.py) ──
import hashlib
MAGIC_BASES = {'icm': 240000, 'ftmo': 250000, '5ers': 260000}
MAGIC_BASE = MAGIC_BASES.get(account, 240000)
def _strat_magic(name):
    return MAGIC_BASE + int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % 9999
MAGIC_MAP = {sn: _strat_magic(sn) for sn in set(list(STRAT_EXITS.keys()) + list(PORTFOLIO))}
MAGIC_REVERSE = {v: k for k, v in MAGIC_MAP.items()}
ALL_OUR_MAGICS = set(MAGIC_MAP.values())

# ── DATA LOADING ──

def load_paper():
    """Load paper trading state from JSON."""
    f = f"data/{account}/paper.json"
    if os.path.exists(f):
        with open(f) as fh: state = json.load(fh)
    else:
        state = {'capital': 1000, 'capital_initial': 1000, 'trades': [], 'open_positions': []}
    capital = state['capital']
    cap_init = state.get('capital_initial', 1000.0)
    trades = state['trades']
    positions = state['open_positions']
    # Get price from DB
    bid, ask = None, None
    try:
        from phase1_poc_calculator import get_conn
        c = get_conn(); c.autocommit = True; cur = c.cursor()
        cur.execute("SELECT bid,ask FROM market_ticks_xauusd ORDER BY ts DESC LIMIT 1")
        r = cur.fetchone(); cur.close(); c.close()
        if r: bid, ask = float(r[0]), float(r[1])
    except: pass
    return capital, cap_init, trades, positions, bid, ask

def load_mt5_live():
    """Load live data directly from MT5."""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return 0, 0, [], [], None, None
        info = mt5.account_info()
        capital = info.balance if info else 0
        cap_init = capital  # no initial tracking for live, use current balance

        # Tick
        tick = mt5.symbol_info_tick('XAUUSD')
        bid = tick.bid if tick else None
        ask = tick.ask if tick else None

        # Open positions (ours)
        mt5_positions = mt5.positions_get(symbol='XAUUSD') or []
        positions = []
        for p in mt5_positions:
            sn = MAGIC_REVERSE.get(p.magic, 'LEGACY')
            if p.magic not in ALL_OUR_MAGICS and sn == 'LEGACY':
                # Check comment for strat name
                if p.comment and p.comment in STRATS:
                    sn = p.comment
            d = 'long' if p.type == 0 else 'short'
            positions.append({
                'strat': sn, 'strat_dir': d,
                'entry': p.price_open, 'stop': p.sl,
                'target': p.tp if p.tp > 0 else None,
                'pos_oz': p.volume * 100,  # 1 lot = 100 oz
                'lots': p.volume,
                'bars_held': 0,
                'trail_active': False,
                'best': p.price_open,
                'entry_time': datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
                '_pnl_live': p.profit,
                '_ticket': p.ticket,
            })

        # History deals (closed trades)
        from_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(timezone.utc)
        deals = mt5.history_deals_get(from_date, to_date) or []

        # Group deals by position ID to reconstruct trades
        pos_deals = {}
        for d in deals:
            if d.symbol != 'XAUUSD': continue
            if d.entry == 0 and d.type <= 1:  # DEAL_ENTRY_IN
                pos_deals.setdefault(d.position_id, {'in': None, 'out': None, 'pnl': 0, 'commission': 0, 'swap': 0})
                pos_deals[d.position_id]['in'] = d
            elif d.entry == 1 and d.type <= 1:  # DEAL_ENTRY_OUT
                pos_deals.setdefault(d.position_id, {'in': None, 'out': None, 'pnl': 0, 'commission': 0, 'swap': 0})
                pos_deals[d.position_id]['out'] = d
                pos_deals[d.position_id]['pnl'] += d.profit
                pos_deals[d.position_id]['commission'] += d.commission
                pos_deals[d.position_id]['swap'] += d.swap

        trades = []
        for pid, td in pos_deals.items():
            if not td['in'] or not td['out']: continue
            din = td['in']; dout = td['out']
            sn = MAGIC_REVERSE.get(din.magic, 'LEGACY')
            if din.magic not in ALL_OUR_MAGICS and sn == 'LEGACY':
                if din.comment and din.comment in STRATS:
                    sn = din.comment
            direction = 'long' if din.type == 0 else 'short'
            pnl_total = td['pnl'] + td['commission'] + td['swap']
            trades.append({
                'strat': sn, 'dir': direction,
                'entry': din.price, 'exit': dout.price,
                'pnl_dollar': pnl_total,
                'pnl_oz': (dout.price - din.price) if direction == 'long' else (din.price - dout.price),
                'entry_time': datetime.fromtimestamp(din.time, tz=timezone.utc).isoformat(),
                'exit_time': datetime.fromtimestamp(dout.time, tz=timezone.utc).isoformat(),
                'exit_reason': 'mt5',
                'bars_held': 0,
                'capital_after': 0,  # can't reconstruct easily
                'lots': din.volume,
            })

        # Sort by entry time and compute running capital
        trades.sort(key=lambda t: t['entry_time'])
        # We don't have true running capital from MT5, estimate from current balance
        running = capital - sum(t['pnl_dollar'] for t in trades)
        for t in trades:
            running += t['pnl_dollar']
            t['capital_after'] = running

        cap_init = capital - sum(t['pnl_dollar'] for t in trades)

        mt5.shutdown()
        return capital, cap_init, trades, positions, bid, ask
    except Exception as e:
        st.error(f"MT5 error: {e}")
        return 0, 0, [], [], None, None

# ── LOAD DATA ──
if mode == "Live MT5":
    capital, CAPITAL_INITIAL, trades, positions, bid, ask = load_mt5_live()
else:
    capital, CAPITAL_INITIAL, trades, positions, bid, ask = load_paper()

now = datetime.now(timezone.utc)
h = now.hour
sess = "Tokyo" if 0<=h<6 else "London" if 8<=h<14 else "New York" if 14<=h<21 else "Off"
pnl = capital - CAPITAL_INITIAL

# ── TITRE ──
mode_label = "Live" if mode == "Live MT5" else "Paper"
st.title(f"VP Swing {BROKER} — {mode_label}")
st.caption(f"{sess} · {now.strftime('%H:%M')} UTC · XAUUSD {'${:,.2f}'.format(bid) if bid else '—'} · {len(PORTFOLIO)} strats · {RISK_PCT*100:.1f}% risk")

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
        e = p.get('entry',0); s = p.get('stop',0)
        d = p.get('strat_dir',''); sn = p.get('strat','')
        lots = p.get('lots',0)
        et = str(p.get('entry_time',''))[:16]
        target = p.get('target')
        exit_cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
        exit_type = exit_cfg[0] if sn != 'LEGACY' else '?'

        # PnL
        if mode == "Live MT5" and '_pnl_live' in p:
            pnl_d = p['_pnl_live']; total_unr += pnl_d
            prix = f"{bid:.2f}" if bid else "—"
            pnl_str = f"${pnl_d:+,.2f}"
            pnl_oz_val = 0
        elif bid:
            oz = p.get('pos_oz', lots * 100)
            px = bid if d=='long' else ask
            pnl_oz_val = (px-e) if d=='long' else (e-px)
            pnl_d = pnl_oz_val * oz; total_unr += pnl_d
            prix = f"{px:.2f}"
            pnl_str = f"${pnl_d:+,.2f}"
        else:
            prix = "—"; pnl_str = "—"; pnl_d = 0; pnl_oz_val = 0

        pos_rows.append({
            'Strat': sn, 'Type': exit_type, 'Dir': d.upper(),
            'Entree': f"{e:.2f}", 'Prix': prix,
            'Stop': f"{s:.2f}" if s else "—",
            'Target': f"{target:.2f}" if target else "—",
            'PnL $': pnl_str,
            '_pnl_val': pnl_d,
            'Lots': f"{lots:.3f}" if lots else "—",
            'Ouvert': et,
        })

    pos_df = pd.DataFrame(pos_rows)
    pnl_vals = pos_df['_pnl_val'].values
    display_df = pos_df.drop(columns=['_pnl_val'])
    def color_pos_pnl(row):
        idx = row.name
        v = pnl_vals[idx] if idx < len(pnl_vals) else 0
        c = 'color:#26a69a' if v > 0 else 'color:#ef5350' if v < 0 else ''
        return [c if col in ('PnL $',) else '' for col in row.index]
    st.dataframe(display_df.style.apply(color_pos_pnl, axis=1),
                 use_container_width=True, hide_index=True)

    if total_unr != 0:
        c = '#26a69a' if total_unr >= 0 else '#ef5350'
        st.markdown(f'**PnL latent total** <span style="color:{c};font-size:1.4em">${total_unr:+,.2f}</span>', unsafe_allow_html=True)
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

    fig.update_layout(height=400, showlegend=False, template='plotly_dark',
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
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
    show['Nom'] = show['strat'].map(lambda x: STRATS.get(x, x))
    show['Dir'] = show['dir'].str.upper()
    show['In'] = show['entry'].apply(lambda x: f"{x:.2f}")
    show['Out'] = show['exit'].apply(lambda x: f"{x:.2f}")
    show['PnL'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
    show['oz'] = show['pnl_oz'].apply(lambda x: f"{x:+.3f}")
    show['Lots'] = show.get('lots', pd.Series([0]*len(show))).apply(lambda x: f"{x:.3f}" if x else "—")

    tbl = show[['Ouverture','Fermeture','strat','Nom','Dir','In','Out','PnL','oz','Lots']].copy()
    tbl.columns = ['Ouverture','Fermeture','Strat','Nom','Dir','In','Out','PnL','PnL oz','Lots']

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
            'Nom': STRATS.get(sn, 'Legacy' if sn == 'LEGACY' else sn),
            'Trades': n, 'Wins': w, 'Losses': n - w,
            'Win Rate': f"{w/n*100:.0f}%",
            'PF': f"{gps/gls:.2f}",
            'PnL total': f"${s['pnl_dollar'].sum():+,.2f}",
            'Avg trade': f"${s['pnl_dollar'].mean():+,.2f}",
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
        fig2.update_layout(title="PnL par strategie", height=350,
                           template='plotly_dark', margin=dict(l=0,r=0,t=30,b=0),
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        daily = df.groupby('date')['pnl_dollar'].sum()
        colors_d = ['#26a69a' if v >= 0 else '#ef5350' for v in daily.values]
        fig3 = go.Figure(go.Bar(x=daily.index, y=daily.values, marker_color=colors_d))
        fig3.update_layout(title="PnL journalier", height=350,
                           template='plotly_dark', margin=dict(l=0,r=0,t=30,b=0),
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig3, use_container_width=True)

else:
    st.info(f"En attente du premier trade. {len(PORTFOLIO)} strategies surveillent XAUUSD 5 minutes.")

# ── SIDEBAR: STRATEGIES ──
with st.sidebar:
    st.subheader(f"Strategies {BROKER}")

    sessions = {}
    for sn in PORTFOLIO:
        s = STRAT_SESSION.get(sn, 'All')
        sessions.setdefault(s, []).append(sn)

    for session, strat_list in sorted(sessions.items()):
        st.caption(f"**{session}**")
        for sn in strat_list:
            exit_cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
            if n_trades > 0 and sn in df['strat'].values:
                s = df[df['strat']==sn]
                w = (s['pnl_dollar']>0).sum(); ns = len(s)
                pnl_s = s['pnl_dollar'].sum()
                gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
                gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
                icon = "🟢" if pnl_s >= 0 else "🔴"
                label = f"{icon} **{sn}** {ns}t WR{w/ns*100:.0f}% ${pnl_s:+,.0f}"
                tip = (f"{STRATS.get(sn,'')}&#10;"
                       f"{exit_cfg[0]} SL={exit_cfg[1]:.1f} "
                       f"{'TP='+str(exit_cfg[2]) if exit_cfg[0]=='TPSL' else 'ACT='+str(exit_cfg[2])+' TR='+str(exit_cfg[3])}&#10;"
                       f"PF={gps/gls:.2f} | {w}W {ns-w}L")
                st.markdown(f'<span title="{tip}">{label}</span>', unsafe_allow_html=True)
            else:
                tip = (f"{STRATS.get(sn,'')}&#10;"
                       f"{exit_cfg[0]} SL={exit_cfg[1]:.1f} "
                       f"{'TP='+str(exit_cfg[2]) if exit_cfg[0]=='TPSL' else 'ACT='+str(exit_cfg[2])+' TR='+str(exit_cfg[3])}")
                st.markdown(f'<span title="{tip}">⚪ **{sn}**</span>', unsafe_allow_html=True)

# Auto-refresh
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10000, key="refresh")
