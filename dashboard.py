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

# Custom CSS
st.markdown("""<style>
.block-container {padding-top: 1rem;}
.card {
    background: #1e1e2e;
    border-radius: 10px;
    padding: 15px 20px;
    margin: 5px 0;
    border: 1px solid #333;
}
.card-green { border-left: 4px solid #26a69a; }
.card-red { border-left: 4px solid #ef5350; }
.card-blue { border-left: 4px solid #42a5f5; }
.card-label { color: #888; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }
.card-value { color: #fff; font-size: 1.5rem; font-weight: 700; }
.card-value-sm { color: #fff; font-size: 1.1rem; font-weight: 600; }
.card-delta { font-size: 0.85rem; margin-top: 2px; }
.delta-green { color: #26a69a; }
.delta-red { color: #ef5350; }
.delta-gray { color: #888; }
.pos-card {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
    border: 1px solid #333;
}
.session-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
}
.session-tokyo { background: #1a237e; color: #90caf9; }
.session-london { background: #1b5e20; color: #a5d6a7; }
.session-ny { background: #b71c1c; color: #ef9a9a; }
.session-off { background: #333; color: #888; }
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

def card(label, value, delta="", card_class="", value_class="card-value"):
    delta_html = f'<div class="card-delta {delta[0] if delta else ""}">{delta[1] if delta else ""}</div>' if delta else ""
    return f'<div class="card {card_class}"><div class="card-label">{label}</div><div class="{value_class}">{value}</div>{delta_html}</div>'

state = load_state()
capital = state['capital']
trades = state['trades']
positions = state['open_positions']
bid, ask = get_price()
now_utc = datetime.now(timezone.utc)
h = now_utc.hour
if 0<=h<6: sess, sess_cls = "Tokyo", "session-tokyo"
elif 8<=h<14: sess, sess_cls = "London", "session-london"
elif 14<=h<21: sess, sess_cls = "New York", "session-ny"
else: sess, sess_cls = "Ferme", "session-off"

pnl = capital - CAPITAL_INITIAL
pnl_pct = pnl / CAPITAL_INITIAL * 100
pnl_cls = "delta-green" if pnl >= 0 else "delta-red"
cap_border = "card-green" if pnl >= 0 else "card-red"

# ══════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════
header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:20px;">
        <div>
            <div style="color:#888; font-size:0.8rem;">XAUUSD 5M PAPER TRADING</div>
            <div style="font-size:2.2rem; font-weight:800; color:white;">${capital:,.2f}</div>
            <div class="{pnl_cls}" style="font-size:1rem;">{'+' if pnl>=0 else ''}{pnl:,.2f} ({pnl_pct:+.1f}%)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with header_right:
    price_html = f"<div style='font-size:1.3rem; font-weight:700;'>${bid:,.2f}</div>" if bid else ""
    spread_html = f"<div class='delta-gray'>spread {ask-bid:.3f}</div>" if bid and ask else ""
    cache = {}
    for k, v in state.get('daily_cache', {}).items(): cache = v; break
    atr_html = f"<div class='delta-gray'>ATR {cache['atr']:.2f}</div>" if cache.get('atr') else ""
    st.markdown(f"""
    <div style="text-align:right;">
        <span class="session-badge {sess_cls}">{sess}</span>
        <span class="delta-gray"> {now_utc.strftime('%H:%M')} UTC</span>
        {price_html}{spread_html}{atr_html}
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════
n_trades = len(trades)
df = None
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

    today_df = df[df['date'] == now_utc.date()]
    today_pnl = today_df['pnl_dollar'].sum() if len(today_df) else 0
    today_n = len(today_df)
    today_cls = "delta-green" if today_pnl >= 0 else "delta-red"

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.markdown(card("Trades", str(n_trades), ("delta-gray", f"{today_n} aujourd'hui"), "card-blue"), unsafe_allow_html=True)
    with k2: st.markdown(card("Win Rate", f"{wr:.0f}%", ("delta-gray", f"{len(wins)}W / {len(losses)}L"), "card-blue"), unsafe_allow_html=True)
    with k3: st.markdown(card("Profit Factor", f"{pf:.2f}", "", "card-blue"), unsafe_allow_html=True)
    with k4: st.markdown(card("Max Drawdown", f"{max_dd:.1f}%", "", "card-red" if max_dd < -5 else "card-blue"), unsafe_allow_html=True)
    with k5: st.markdown(card("Aujourd'hui", f"${today_pnl:+,.2f}", (today_cls, f"{today_n} trades"), "card-green" if today_pnl>=0 else "card-red"), unsafe_allow_html=True)
else:
    st.markdown(card("Trades", "0", ("delta-gray", "En attente de signaux"), "card-blue"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# POSITIONS OUVERTES
# ══════════════════════════════════════════════════
if positions:
    st.markdown(f"### Positions ouvertes")
    total_unr = 0
    for p in positions:
        entry=p.get('entry',0); stop=p.get('stop',0); best=p.get('best',entry)
        d=p.get('strat_dir',''); strat=p.get('strat',''); oz=p.get('pos_oz',0)
        bars=p.get('bars_held',0); atr=p.get('trade_atr',1)
        trail=p.get('trail_active',False); lots=p.get('lots',0)
        entry_time=str(p.get('entry_time',''))[:16]

        px_str="—"; pnl_str="—"; pnl_d=0
        if bid:
            px = bid if d=='long' else ask
            pnl_oz = (px-entry) if d=='long' else (entry-px)
            pnl_d = pnl_oz*oz; total_unr += pnl_d
            px_str=f"${px:.2f}"; pnl_str=f"${pnl_d:+,.2f}"

        pnl_color = "#26a69a" if pnl_d>=0 else "#ef5350"
        trail_str = "🔒 Trail ON" if trail else "Trail off"
        bar_pct = int(bars/12*100)

        st.markdown(f"""
        <div class="pos-card" style="border-left: 4px solid {pnl_color};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:1.1rem; font-weight:700;">{strat}</span>
                    <span style="color:#888;"> {STRATS.get(strat,'')} · </span>
                    <span style="font-weight:600; color:{'#26a69a' if d=='long' else '#ef5350'};">{d.upper()}</span>
                    <span style="color:#666;"> · {entry_time}</span>
                </div>
                <div style="font-size:1.3rem; font-weight:700; color:{pnl_color};">{pnl_str}</div>
            </div>
            <div style="display:flex; gap:30px; margin-top:8px; color:#aaa; font-size:0.85rem;">
                <span>Entree <b>${entry:.2f}</b></span>
                <span>Prix <b>{px_str}</b></span>
                <span>Stop <b>${stop:.2f}</b></span>
                <span>Best <b>${best:.2f}</b></span>
                <span>{trail_str}</span>
                <span>{lots:.3f} lots</span>
                <span>Bar {bars}/12</span>
            </div>
            <div style="margin-top:6px; background:#333; border-radius:4px; height:4px;">
                <div style="background:{pnl_color}; width:{bar_pct}%; height:100%; border-radius:4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if bid:
        unr_color = "#26a69a" if total_unr>=0 else "#ef5350"
        st.markdown(f'<div style="text-align:right; font-size:1.1rem; color:{unr_color}; font-weight:600; margin:8px 0;">PnL latent: ${total_unr:+,.2f}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# EQUITY + DRAWDOWN
# ══════════════════════════════════════════════════
if df is not None and len(df) > 0:
    col_eq, col_dd = st.columns(2)
    with col_eq:
        st.markdown("### Equity")
        eq = pd.DataFrame({'$': [CAPITAL_INITIAL] + df['cum'].tolist()},
            index=[df['entry_time'].iloc[0] - pd.Timedelta(minutes=30)] + df['entry_time'].tolist())
        st.line_chart(eq, height=250, use_container_width=True)
    with col_dd:
        st.markdown("### Drawdown")
        peak = pd.concat([pd.Series([CAPITAL_INITIAL]), df['cum']]).cummax().iloc[1:].reset_index(drop=True)
        dd_s = (df['cum'].reset_index(drop=True) - peak) / peak * 100
        st.area_chart(pd.DataFrame({'%': dd_s.values}, index=df['entry_time'].values),
                      height=250, use_container_width=True, color='#ff4b4b')

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # TRADES
    # ══════════════════════════════════════════════════
    st.markdown(f"### Historique des trades ({n_trades})")

    show = df.iloc[::-1].copy()
    show['Ouverture'] = show['entry_time'].dt.strftime('%d/%m %H:%M')
    show['Fermeture'] = show['exit_time'].dt.strftime('%d/%m %H:%M')
    show['Nom'] = show['strat'].map(STRATS)
    show['Dir'] = show['dir'].str.upper()
    show['In'] = show['entry'].apply(lambda x: f"{x:.2f}")
    show['Out'] = show['exit'].apply(lambda x: f"{x:.2f}")
    show['PnL'] = show['pnl_dollar'].apply(lambda x: f"${x:+,.2f}")
    show['PnL oz'] = show['pnl_oz'].apply(lambda x: f"{x:+.3f}")
    show['Sortie'] = show['exit_reason']
    show['Bars'] = show['bars_held']
    show['Duree'] = show['duration'].apply(lambda x: f"{x:.0f}m")
    show['Capital'] = show['capital_after'].apply(lambda x: f"${float(x):,.2f}")

    cols = ['Ouverture','Fermeture','strat','Nom','Dir','In','Out','PnL','PnL oz','Sortie','Bars','Duree','Capital']
    tbl = show[cols].copy()
    tbl.columns = ['Ouverture','Fermeture','Strat','Nom','Dir','In','Out','PnL','PnL oz','Sortie','Bars','Duree','Capital']

    def color_pnl(row):
        try:
            v = float(row['PnL'].replace('$','').replace(',','').replace('+',''))
            c = 'color:#26a69a' if v>0 else 'color:#ef5350'
        except: c = ''
        return [c]*len(row)

    st.dataframe(tbl.style.apply(color_pnl, axis=1), use_container_width=True, hide_index=True,
                 height=min(n_trades*38+40, 500))

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════
    # PERFORMANCE
    # ══════════════════════════════════════════════════
    st.markdown("### Performance par strategie")

    srows = []
    for sn in sorted(df['strat'].unique()):
        s = df[df['strat']==sn]; n=len(s); w=(s['pnl_dollar']>0).sum()
        gps=s[s['pnl_dollar']>0]['pnl_dollar'].sum()
        gls=abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        srows.append({
            'Strat':sn, 'Nom':STRATS.get(sn,''), 'Trades':n,
            'Wins':w, 'Losses':n-w,
            'Win Rate':f"{w/n*100:.0f}%", 'PF':f"{gps/gls:.2f}",
            'PnL':f"${s['pnl_dollar'].sum():+,.2f}",
            'Avg':f"${s['pnl_dollar'].mean():+,.2f}",
            'Best':f"${s['pnl_dollar'].max():+,.2f}",
            'Worst':f"${s['pnl_dollar'].min():+,.2f}",
        })
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### PnL par strategie")
        st.bar_chart(df.groupby('strat')['pnl_dollar'].sum().sort_values(),
                     horizontal=True, height=250, use_container_width=True)
    with col2:
        st.markdown("##### PnL journalier")
        st.bar_chart(df.groupby('date')['pnl_dollar'].sum(), height=250, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("##### Direction")
        for d_n in ['long','short']:
            s=df[df['dir']==d_n]
            if len(s)==0: continue
            w=(s['pnl_dollar']>0).sum()
            gd=s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            ld=abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            color = "#26a69a" if s['pnl_dollar'].sum()>=0 else "#ef5350"
            st.markdown(f"<div style='margin:8px 0;'><b>{d_n.upper()}</b> · {len(s)} trades · WR {w/len(s)*100:.0f}% · PF {gd/ld:.2f}<br><span style='color:{color};font-weight:600;'>${s['pnl_dollar'].sum():+,.2f}</span></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("##### Sorties")
        for reason in sorted(df['exit_reason'].unique()):
            s=df[df['exit_reason']==reason]; w=(s['pnl_dollar']>0).sum()
            st.markdown(f"**{reason}** · {len(s)} trades · {w}W {len(s)-w}L")

    with col3:
        st.markdown("##### Statistiques")
        ls = max((sum(1 for _ in g) for k,g in itertools.groupby(df['pnl_dollar']<0) if k), default=0)
        ws = max((sum(1 for _ in g) for k,g in itertools.groupby(df['pnl_dollar']>0) if k), default=0)
        stats = {
            'Max wins consec': ws, 'Max losses consec': ls,
            'Avg win': f"${wins['pnl_dollar'].mean():+,.2f}" if len(wins) else "—",
            'Avg loss': f"${losses['pnl_dollar'].mean():+,.2f}" if len(losses) else "—",
            'Duree moyenne': f"{df['duration'].mean():.0f} min",
            'Bars moyen': f"{df['bars_held'].mean():.1f}",
        }
        for k, v in stats.items():
            st.markdown(f"**{k}**: {v}")

else:
    st.markdown("""
    <div class="card card-blue" style="text-align:center; padding:40px;">
        <div class="card-label">SYSTEME ACTIF</div>
        <div style="font-size:1.2rem; color:#ccc; margin:15px 0;">En attente du premier trade</div>
        <div style="color:#888;">10 strategies surveillent XAUUSD sur bougies 5 minutes</div>
        <div style="color:#666; margin-top:10px; font-size:0.85rem;">
            Tokyo: AC, F, O, V · London: D, E, H · New York: G, I, P
        </div>
    </div>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Config")
    st.caption("Trailing pessimiste")
    st.caption("SL 1.5 ATR · ACT 0.3 · TRAIL 0.3")
    st.caption("Max 12 barres")
    st.divider()
    st.caption("Strats actives:")
    for s, n in sorted(STRATS.items()):
        st.caption(f"**{s}** · {n}")

# Refresh
time.sleep(10)
st.rerun()
