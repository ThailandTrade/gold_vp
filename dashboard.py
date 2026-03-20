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
    'AC':'Absorption Tok','D':'GAP Tok→Lon','E':'KZ Lon fade',
    'F':'2BAR Tok rev','G':'NY 1st','H':'TOKEND 3b',
    'I':'FADE NY 1h','O':'BigCandle Tok','P':'ORB NY 30m','V':'Ratio Tok'
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

def session():
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

# ════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════
h1, h2, h3, h4 = st.columns([2,1,1,1])
h1.markdown(f"## ${capital:,.2f}")
pnl = capital - CAPITAL_INITIAL
h1.caption(f"{'+ ' if pnl >= 0 else ''}{pnl:,.2f} ({pnl/CAPITAL_INITIAL*100:+.1f}%)")

h2.markdown(f"**{session()}** {datetime.now(timezone.utc).strftime('%H:%M')} UTC")
if bid: h2.caption(f"Gold ${bid:,.2f}")

if trades:
    df = pd.DataFrame(trades)
    df['pnl_dollar'] = df['pnl_dollar'].astype(float)
    df['cum'] = df['capital_after'].astype(float)
    caps = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).reset_index(drop=True)
    dd = ((caps - caps.cummax()) / caps.cummax() * 100).min()
    dd_now = (capital - caps.cummax().iloc[-1]) / caps.cummax().iloc[-1] * 100

    w = (df['pnl_dollar'] > 0).sum()
    gp = df[df['pnl_dollar']>0]['pnl_dollar'].sum()
    gl = abs(df[df['pnl_dollar']<0]['pnl_dollar'].sum()) + 0.01

    h3.metric("PF", f"{gp/gl:.2f}", delta=f"WR {w/len(df)*100:.0f}%")
    h4.metric("DD", f"{dd_now:.1f}%", delta=f"max {dd:.1f}%", delta_color="off")

st.divider()

# ════════════════════════════════════════════
# POSITIONS OUVERTES
# ════════════════════════════════════════════
if positions:
    st.markdown("#### Positions ouvertes")
    rows = []
    total_pnl = 0
    for p in positions:
        e = p.get('entry',0); s = p.get('stop',0); d = p.get('strat_dir','')
        oz = p.get('pos_oz',0); b = p.get('bars_held',0)
        pnl_str = "—"; prix = "—"
        if bid:
            px = bid if d == 'long' else ask
            pnl_oz = (px - e) if d == 'long' else (e - px)
            pnl_d = pnl_oz * oz; total_pnl += pnl_d
            pnl_str = f"${pnl_d:+,.2f}"; prix = f"{px:.2f}"
        rows.append({
            '': p.get('strat',''),
            'Direction': d.upper(),
            'Entree': f"{e:.2f}",
            'Prix': prix,
            'Stop': f"{s:.2f}",
            'PnL': pnl_str,
            'Trail': '✓' if p.get('trail_active') else '—',
            'Bars': f"{b}/12",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if bid:
        color = "green" if total_pnl >= 0 else "red"
        st.markdown(f"PnL latent: :{color}[**${total_pnl:+,.2f}**]")
    st.divider()

# ════════════════════════════════════════════
# PAS DE TRADES
# ════════════════════════════════════════════
if not trades:
    st.caption("Aucun trade. En attente de signaux.")
    with st.sidebar:
        if st.button("Reset"):
            with open(LOG_FILE, 'w') as f:
                json.dump({'capital':CAPITAL_INITIAL,'trades':[],'open_positions':[],
                           'ib_levels':{},'daily_cache':{},'_triggered':{},'last_candle_ts':0}, f, indent=2)
            st.rerun()
    time.sleep(10); st.rerun()
    st.stop()

# ════════════════════════════════════════════
# EQUITY
# ════════════════════════════════════════════
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])

eq = pd.DataFrame({'$': [CAPITAL_INITIAL] + df['cum'].tolist()},
    index=[df['entry_time'].iloc[0] - pd.Timedelta(minutes=30)] + df['entry_time'].tolist())
st.line_chart(eq, height=220, use_container_width=True)

# ════════════════════════════════════════════
# TRADES
# ════════════════════════════════════════════
st.markdown("#### Trades")
for _, t in df.iloc[::-1].iterrows():
    p = t['pnl_dollar']
    c = "🟢" if p > 0 else "🔴"
    d = t['entry_time'].strftime('%d/%m %H:%M')
    dur = (t['exit_time'] - t['entry_time']).total_seconds() / 60
    st.caption(
        f"{c} **{t['strat']}** {t['dir']} · {d} · "
        f"{t['entry']:.2f}→{t['exit']:.2f} · "
        f"**${p:+,.2f}** · {t['exit_reason']} · {t['bars_held']}b/{dur:.0f}m"
    )

# ════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════
if len(df) >= 3:
    st.divider()
    st.markdown("#### Stats")

    c1, c2 = st.columns(2)
    with c1:
        srows = []
        for sn in sorted(df['strat'].unique()):
            s = df[df['strat']==sn]; n = len(s)
            w = (s['pnl_dollar']>0).sum()
            gps = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gls = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            srows.append({
                '': sn, 'Nom': STRATS.get(sn,''), 'n': n,
                'WR': f"{w/n*100:.0f}%", 'PF': f"{gps/gls:.2f}",
                'PnL': f"${s['pnl_dollar'].sum():+,.2f}",
            })
        st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    with c2:
        for d_name in ['long','short']:
            s = df[df['dir']==d_name]
            if len(s) == 0: continue
            w = (s['pnl_dollar']>0).sum()
            gp_d = s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            gl_d = abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            st.caption(f"**{d_name.upper()}** {len(s)} trades · WR {w/len(s)*100:.0f}% · PF {gp_d/gl_d:.2f} · ${s['pnl_dollar'].sum():+,.2f}")

        # Streaks
        loss_s = max((sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar']<0) if k), default=0)
        win_s = max((sum(1 for _ in g) for k, g in itertools.groupby(df['pnl_dollar']>0) if k), default=0)
        st.caption(f"Max win streak: {win_s} · Max loss streak: {loss_s}")

# ════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════
with st.sidebar:
    if st.button("Reset"):
        with open(LOG_FILE, 'w') as f:
            json.dump({'capital':CAPITAL_INITIAL,'trades':[],'open_positions':[],
                       'ib_levels':{},'daily_cache':{},'_triggered':{},'last_candle_ts':0}, f, indent=2)
        st.rerun()

time.sleep(10)
st.rerun()

