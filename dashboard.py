"""
Dashboard VP Swing — streamlit run dashboard.py
Multi-compte, multi-instrument, Live MT5 uniquement.
"""
import streamlit as st
import pandas as pd
import numpy as np
import hashlib, importlib
from datetime import datetime, timezone, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from strats import STRAT_NAMES, STRAT_SESSION
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

st.set_page_config(page_title="VP Swing", layout="wide")

# ── SIDEBAR: ACCOUNT ──
ACCOUNTS = {
    'icm': {'module': 'config_icm', 'label': 'ICMarkets'},
    'ftmo': {'module': 'config_ftmo', 'label': 'FTMO'},
    '5ers': {'module': 'config_5ers', 'label': '5ers'},
}
with st.sidebar:
    account = st.selectbox("Compte", list(ACCOUNTS.keys()),
                           format_func=lambda x: ACCOUNTS[x]['label'],
                           key='account_selector')

cfg = importlib.import_module(ACCOUNTS[account]['module'])
BROKER = cfg.BROKER
INSTRUMENTS = cfg.INSTRUMENTS

# ── MAGIC NUMBERS (same as live_mt5.py) ──
MAGIC_BASES = {'icm': 240000, 'ftmo': 250000, '5ers': 260000}
MAGIC_BASE = MAGIC_BASES.get(account, 240000)

def _magic(symbol, strat):
    sym_offset = int(hashlib.md5(symbol.encode()).hexdigest()[:2], 16) * 100
    strat_hash = int(hashlib.md5(strat.encode()).hexdigest()[:4], 16) % 99
    return MAGIC_BASE + sym_offset + strat_hash

# Build reverse magic map for all instruments
MAGIC_REVERSE = {}  # magic -> (symbol, strat)
for sym, icfg in INSTRUMENTS.items():
    for sn in icfg['portfolio']:
        m = _magic(sym, sn)
        MAGIC_REVERSE[m] = (sym, sn)
ALL_OUR_MAGICS = set(MAGIC_REVERSE.keys())

# ── MT5 DATA LOADING ──

def load_mt5():
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        info = mt5.account_info()
        if not info:
            mt5.shutdown(); return None

        balance = info.balance
        equity = info.equity

        # Positions ouvertes (tous instruments)
        positions = []
        for sym in INSTRUMENTS:
            mt5_pos = mt5.positions_get(symbol=sym) or []
            for p in mt5_pos:
                sym_sn = MAGIC_REVERSE.get(p.magic)
                sn = sym_sn[1] if sym_sn else 'LEGACY'
                d = 'long' if p.type == 0 else 'short'
                positions.append({
                    'symbol': sym, 'strat': sn, 'dir': d,
                    'entry': p.price_open, 'stop': p.sl,
                    'tp': p.tp if p.tp > 0 else None,
                    'lots': p.volume, 'pnl': p.profit,
                    'ticket': p.ticket,
                    'time': datetime.fromtimestamp(p.time, tz=timezone.utc),
                })

        # Historique deals (tous instruments)
        from_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        to_date = datetime.now(timezone.utc) + timedelta(days=1)
        deals = mt5.history_deals_get(from_date, to_date) or []

        symbols_set = set(INSTRUMENTS.keys())
        pos_deals = {}
        for d in deals:
            if d.symbol not in symbols_set: continue
            if d.entry == 0 and d.type <= 1:  # DEAL_ENTRY_IN
                pos_deals.setdefault(d.position_id, {'in': None, 'out': None, 'pnl': 0, 'comm': 0, 'swap': 0})
                pos_deals[d.position_id]['in'] = d
            elif d.entry == 1 and d.type <= 1:  # DEAL_ENTRY_OUT
                pos_deals.setdefault(d.position_id, {'in': None, 'out': None, 'pnl': 0, 'comm': 0, 'swap': 0})
                pos_deals[d.position_id]['out'] = d
                pos_deals[d.position_id]['pnl'] += d.profit
                pos_deals[d.position_id]['comm'] += d.commission
                pos_deals[d.position_id]['swap'] += d.swap

        trades = []
        for pid, td in pos_deals.items():
            if not td['in'] or not td['out']: continue
            din = td['in']; dout = td['out']
            sym_sn = MAGIC_REVERSE.get(din.magic)
            sym = sym_sn[0] if sym_sn else din.symbol
            sn = sym_sn[1] if sym_sn else 'LEGACY'
            direction = 'long' if din.type == 0 else 'short'
            pnl_total = td['pnl'] + td['comm'] + td['swap']
            trades.append({
                'symbol': sym, 'strat': sn, 'dir': direction,
                'entry': din.price, 'exit': dout.price,
                'pnl': pnl_total, 'lots': din.volume,
                'entry_time': datetime.fromtimestamp(din.time, tz=timezone.utc),
                'exit_time': datetime.fromtimestamp(dout.time, tz=timezone.utc),
            })

        trades.sort(key=lambda t: t['entry_time'])
        # Reconstruct running capital
        cap_init = balance - sum(t['pnl'] for t in trades)
        running = cap_init
        for t in trades:
            running += t['pnl']
            t['capital_after'] = running

        mt5.shutdown()
        return {
            'balance': balance, 'equity': equity, 'cap_init': cap_init,
            'positions': positions, 'trades': trades,
        }
    except Exception as e:
        st.error(f"MT5 error: {e}")
        return None

# ── LOAD ──
data = load_mt5()

if not data:
    st.error("Impossible de se connecter a MT5")
    st.stop()

balance = data['balance']
cap_init = data['cap_init']
trades = data['trades']
positions = data['positions']
pnl_total = balance - cap_init
now = datetime.now(timezone.utc)
h = now.hour
sess = "Tokyo" if 0<=h<6 else "London" if 8<=h<14 else "New York" if 14<=h<21 else "Off"
n_instruments = sum(1 for icfg in INSTRUMENTS.values() if icfg['portfolio'])
n_strats = sum(len(icfg['portfolio']) for icfg in INSTRUMENTS.values())

# ── TITRE ──
st.title(f"VP Swing {BROKER} — Live")
st.caption(f"{sess} · {now.strftime('%H:%M')} UTC · {n_instruments} instruments · {n_strats} strats · 0.05% risk")

# ── METRIQUES GLOBALES ──
n_trades = len(trades)
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Balance", f"${balance:,.0f}", f"${pnl_total:+,.0f}")

if n_trades > 0:
    df = pd.DataFrame(trades)
    df['pnl'] = df['pnl'].astype(float)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['date'] = df['entry_time'].dt.date

    wins = df[df['pnl'] > 0]; losses = df[df['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) else 0
    gl = abs(losses['pnl'].sum()) + 0.01
    caps = pd.concat([pd.Series([cap_init]), df['capital_after']]).reset_index(drop=True)
    max_dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
    today_df = df[df['date'] == now.date()]
    today_pnl = today_df['pnl'].sum() if len(today_df) else 0

    c2.metric("Trades", n_trades, f"{len(today_df)} aujourd'hui")
    c3.metric("Win Rate", f"{len(wins)/n_trades*100:.0f}%", f"{len(wins)}W {len(losses)}L")
    c4.metric("Profit Factor", f"{gp/gl:.2f}")
    c5.metric("Max DD", f"{max_dd:.1f}%")
    c6.metric("PnL du jour", f"${today_pnl:+,.0f}")
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
    total_unr = sum(p['pnl'] for p in positions)
    for p in positions:
        sym_exits = STRAT_EXITS.get((account, p['symbol']), {})
        exit_cfg = sym_exits.get(p['strat'], DEFAULT_EXIT)
        pos_rows.append({
            'Symbol': p['symbol'], 'Strat': p['strat'],
            'Type': exit_cfg[0], 'Dir': p['dir'].upper(),
            'Entry': f"{p['entry']:.2f}", 'Stop': f"{p['stop']:.2f}" if p['stop'] else "—",
            'TP': f"{p['tp']:.2f}" if p['tp'] else "—",
            'Lots': f"{p['lots']:.3f}",
            'PnL': f"${p['pnl']:+,.2f}",
            '_pnl_val': p['pnl'],
            'Ouvert': p['time'].strftime('%d/%m %H:%M'),
        })
    pos_df = pd.DataFrame(pos_rows)
    pnl_vals = pos_df['_pnl_val'].values
    display_df = pos_df.drop(columns=['_pnl_val'])

    def color_pnl(row):
        idx = row.name
        v = pnl_vals[idx] if idx < len(pnl_vals) else 0
        c = 'color:#26a69a' if v > 0 else 'color:#ef5350' if v < 0 else ''
        return [c if col == 'PnL' else '' for col in row.index]

    st.dataframe(display_df.style.apply(color_pnl, axis=1),
                 use_container_width=True, hide_index=True)
    c = '#26a69a' if total_unr >= 0 else '#ef5350'
    st.markdown(f'**PnL latent** <span style="color:{c};font-size:1.4em">${total_unr:+,.2f}</span>', unsafe_allow_html=True)
else:
    st.info("Aucune position ouverte")

st.divider()

# ── EQUITY + DRAWDOWN ──
if n_trades > 1:
    st.subheader("Equity & Drawdown")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])
    eq_x = [df['entry_time'].iloc[0] - pd.Timedelta(minutes=30)] + df['entry_time'].tolist()
    eq_y = [cap_init] + df['capital_after'].tolist()
    fig.add_trace(go.Scatter(x=eq_x, y=eq_y, fill='tozeroy',
                             fillcolor='rgba(38,166,154,0.15)',
                             line=dict(color='#26a69a', width=2), name='Capital'), row=1, col=1)
    peak = pd.Series(eq_y).cummax()
    dd = ((pd.Series(eq_y) - peak) / peak * 100)
    fig.add_trace(go.Scatter(x=eq_x, y=dd, fill='tozeroy',
                             fillcolor='rgba(239,83,80,0.15)',
                             line=dict(color='#ef5350', width=1.5), name='Drawdown'), row=2, col=1)
    fig.update_layout(height=400, showlegend=False, template='plotly_dark',
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_yaxes(title_text="$", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

# ── PERFORMANCE PAR INSTRUMENT ──
if n_trades > 0:
    st.subheader("Performance par instrument")
    sym_rows = []
    for sym in sorted(df['symbol'].unique()):
        s = df[df['symbol'] == sym]; n = len(s)
        w = (s['pnl'] > 0).sum()
        gps = s[s['pnl'] > 0]['pnl'].sum()
        gls = abs(s[s['pnl'] < 0]['pnl'].sum()) + 0.01
        sym_rows.append({
            'Instrument': sym, 'Trades': n, 'WR': f"{w/n*100:.0f}%",
            'PF': f"{gps/gls:.2f}", 'PnL': f"${s['pnl'].sum():+,.0f}",
        })
    st.dataframe(pd.DataFrame(sym_rows), use_container_width=True, hide_index=True)
    st.divider()

    # ── PERFORMANCE PAR STRATEGIE ──
    st.subheader("Performance par strategie")
    srows = []
    for _, grp in df.groupby(['symbol', 'strat']):
        sym = grp['symbol'].iloc[0]; sn = grp['strat'].iloc[0]
        n = len(grp); w = (grp['pnl'] > 0).sum()
        gps = grp[grp['pnl'] > 0]['pnl'].sum()
        gls = abs(grp[grp['pnl'] < 0]['pnl'].sum()) + 0.01
        srows.append({
            'Instrument': sym, 'Strat': sn,
            'Nom': STRAT_NAMES.get(sn, sn),
            'Trades': n, 'WR': f"{w/n*100:.0f}%",
            'PF': f"{gps/gls:.2f}", 'PnL': f"${grp['pnl'].sum():+,.0f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        pnl_sym = df.groupby('symbol')['pnl'].sum().sort_values()
        colors = ['#26a69a' if v >= 0 else '#ef5350' for v in pnl_sym.values]
        fig2 = go.Figure(go.Bar(y=pnl_sym.index, x=pnl_sym.values, orientation='h',
                                marker_color=colors,
                                text=[f"${v:+,.0f}" for v in pnl_sym.values],
                                textposition='outside'))
        fig2.update_layout(title="PnL par instrument", height=350,
                           template='plotly_dark', margin=dict(l=0,r=0,t=30,b=0),
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        daily = df.groupby('date')['pnl'].sum()
        colors_d = ['#26a69a' if v >= 0 else '#ef5350' for v in daily.values]
        fig3 = go.Figure(go.Bar(x=daily.index, y=daily.values, marker_color=colors_d))
        fig3.update_layout(title="PnL journalier", height=350,
                           template='plotly_dark', margin=dict(l=0,r=0,t=30,b=0),
                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── TRADES FERMES ──
    st.subheader(f"Trades fermes ({n_trades})")
    show = df.iloc[::-1].copy()
    show['Ouverture'] = show['entry_time'].dt.strftime('%d/%m %H:%M')
    show['Fermeture'] = show['exit_time'].dt.strftime('%d/%m %H:%M')
    show['Dir'] = show['dir'].str.upper()
    show['In'] = show['entry'].apply(lambda x: f"{x:.2f}")
    show['Out'] = show['exit'].apply(lambda x: f"{x:.2f}")
    show['PnL $'] = show['pnl'].apply(lambda x: f"${x:+,.2f}")
    show['Lots'] = show['lots'].apply(lambda x: f"{x:.3f}")
    tbl = show[['Ouverture','Fermeture','symbol','strat','Dir','In','Out','PnL $','Lots']].copy()
    tbl.columns = ['Ouverture','Fermeture','Symbol','Strat','Dir','In','Out','PnL','Lots']

    def color_trade(row):
        try:
            v = float(row['PnL'].replace('$','').replace(',','').replace('+',''))
            c = 'color:#26a69a' if v > 0 else 'color:#ef5350'
        except: c = ''
        return [c] * len(row)
    st.dataframe(tbl.style.apply(color_trade, axis=1),
                 use_container_width=True, hide_index=True, height=min(n_trades * 38 + 40, 500))

else:
    st.info(f"En attente du premier trade. {n_strats} strategies sur {n_instruments} instruments.")

# ── SIDEBAR: INSTRUMENTS SUMMARY ──
with st.sidebar:
    st.subheader(f"Portfolio {BROKER}")
    for sym, icfg in INSTRUMENTS.items():
        portfolio = icfg['portfolio']
        if not portfolio: continue
        n_s = len(portfolio)
        if n_trades > 0:
            s = df[df['symbol'] == sym]
            if len(s) > 0:
                w = (s['pnl'] > 0).sum(); ns = len(s)
                pnl_s = s['pnl'].sum()
                icon = "🟢" if pnl_s >= 0 else "🔴"
                st.markdown(f"{icon} **{sym}** · {n_s} strats · {ns}t · WR{w/ns*100:.0f}% · ${pnl_s:+,.0f}")
                continue
        st.markdown(f"⚪ **{sym}** · {n_s} strats")

# Auto-refresh
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10000, key="refresh")
